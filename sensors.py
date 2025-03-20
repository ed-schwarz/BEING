import abc

from typing import Union, Optional

from PySide6.QtGui import QColorConstants, QIcon
from SpektraBsi import BsiInstrument, BsiI2c, TMUMeasurementQuantity
import time
from PySide6.QtCore import QThread, QMutex

from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QApplication, QTextEdit, QWidget, QListWidgetItem


import functools


def utb_connected(f):
    @functools.wraps(f)
    def func(*args, **kwargs):
        try:
            if not isinstance(args[0].utb, BsiInstrument):  # self.utb of class Device
                raise TypeError()
            assert args[0].utb.connected
            return f(*args, **kwargs)
        except AssertionError as e:
            args[0].checklog("UTB not connected", False)

    return func

#Parent Class for sensors. Do not instanciate it directly
class Sensor(QObject):
    device_type = None  # i.e. "EEPROM"
    part_number = None  # optional
    pwr_sources = list()  # the power source the device is connected to (1..4) as int or list of int
    

    output = Signal(bool, str)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if isinstance(cls.pwr_sources, int):
            cls.pwr_sources = [cls.pwr_sources]
        elif not isinstance(cls.pwr_sources, list):
            raise ValueError("pwr_sources must be an int or a list of int")
        for e in cls.pwr_sources:
            if e not in range(1, 5):
                raise ValueError(f"{cls.__name__} must have assigned a power source (1..4)")
        if cls.device_type is None:
            raise ValueError(f"{cls.__name__} must have assigned a device type.")
        if cls.part_number:
            pass  # not used at the moment

    def __init__(self, utb: BsiInstrument):
        super().__init__()
        self.utb = utb
        
    #turn power off
    @utb_connected
    def power_off(self):
        ans = True
        for e in self.pwr_sources:
            res = self.utb.pwr_set_onoff(e, 0, 0)
            self.checklog("Turning Power Off", res)
            ans &= res
            res = self.utb.pwr_set_openrelais(e, 0)
            self.checklog("Opening Power Relais", res)
            ans &= res
        return ans

    #turn power on
    @utb_connected
    def power_on(self):
        ans = True
        for e in self.pwr_sources:
            # close power relais
            res = self.utb.pwr_set_closerelais(e, 0)
            self.checklog("Closing Power Relais", res)
            ans &= res
            # power on
            res = self.utb.pwr_set_onoff(e, 0, 1)
            self.checklog("Turning Power On", res)
            ans &= res
        return ans

    @abc.abstractmethod
    @utb_connected
    def configure(self):
        pass

    def checklog(self, text: str, result: bool):
        # use stdout
        print(("check" if result else "fail") + "\t" + text)

        # emit signal with stuff to print for gui
        self.output.emit(result, text)



class EEPROM24XX02(Sensor):
    device_type = "EEPROM"
    part_number = "24XX02"
    pwr_sources = 1
    
    pages = 64
    pagesize = 8

    def __init__(self, utb: BsiInstrument):
        super().__init__(utb)
        self.utb_i2c = BsiI2c(self.utb, 1, 1)  

    @utb_connected
    def configure(self):
        self.power_off()
        # configure pin output and input levels
        res = self.utb.mio_set_high_level_out(1, 5, 0)
        res = res and self.utb.mio_set_low_level_out(1, 0, 0)
        res = res and self.utb.mio_set_high_level_in(1, 3.5, 0)
        res = res and self.utb.mio_set_low_level_in(1, .4, 0)
        self.checklog("Setting Pin I/O Voltage Levels", res)
        # configure i2c MIOs
        res = self.utb.mio_load_config(1, [0x00802005, 0x00802004, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        res = res and self.utb.mio_activate_config(1, 0)
        self.checklog("Configuring I2C MIO Pins", res)
        # set eeprom addr
        res = self.utb.i2c_set_master_address(0x57, 0, 1)
        self.checklog("Setting I2C Address", res)
        # config power
        res = self.utb.pwr_config_voltage_source(self.pwr_sources[0], 0, 5.0, -0.1, 50, False)
        self.checklog("Configuring Voltage Source", res)

    @utb_connected
    def write(self, addr: Union[int, bytearray], data: bytearray):
        # write data
        # note: writing more than pagesize of bytes results in overwriting the first written bytes

        # add addr word at start
        data.insert(0, addr)

        ans = self.utb_i2c.write(0x57, data)

        self.checklog("Writing " +
                      str(len(data) - 1) + " bytes at address 0x" + format(data[0], '02X') + ": " +
                      ' '.join(format(x, '02X') for x in data[1:]), ans)

    @utb_connected
    def read(self, addr: Union[int, bytearray], num_bytes: int):
        # read data
        res = self.utb_i2c.write(0x57, addr)
        time.sleep(1)
        ans = self.utb_i2c.read(0x57, num_bytes)
        res = res and bool(ans)
        if res:
            self.checklog("Reading " + str(num_bytes) + " bytes at address 0x" +
                          ' '.join(format(x, '02X') for x in addr) + ": " +
                          ' '.join(format(x, '02X') for x in ans), res)
        else:
            self.checklog("Reading " + str(num_bytes) + " bytes at address 0x" +
                          ' '.join(format(x, '02X') for x in addr), res)

    #read entire EEPROM
    @utb_connected
    def read_all(self):
        self.utb_i2c.write(0x57, bytearray(1))  # start address
        time.sleep(.1)
        data = self.utb_i2c.read(0x57, 248)  # api supports max 255 byte reads, Eval EEPROM size is 256 byte
        print("00: ", end='')
        for i, byte in enumerate(data):
            print(f'{byte:02X}', end=' ')
            if (i + 1) % 8 == 0:
                print('\n' + f'{i + 1:02X}', end=': ')
        # read last 8 bytes
        self.utb_i2c.write(0x57, bytearray(b'\xF8'))  # start address
        time.sleep(.1)
        data = self.utb_i2c.read(0x57, 8)  # api supports max 255 byte reads, Eval EEPROM size is 256 byte
        print(' '.join(f'{byte:02X}' for byte in data))


class Oscillator(Sensor):
    device_type = "Osci"
    pwr_sources = 2
    

    def __init__(self, utb: BsiInstrument):

        super().__init__(utb)

    #configure the Sensor
    @utb_connected
    def configure(self):
        self.utb.pwr_set_supply_current_limit_max(self.pwr_sources[0], 20, 0)
        self.utb.pwr_set_supply_current_limit_min(self.pwr_sources[0], -20, 0)
        self.utb.pwr_set_supply_voltagemode(self.pwr_sources[0], 0)
        self.utb.pwr_set_supply_voltage(self.pwr_sources[0], 5, 0)

        self.utb.set_meas_range(0)

        res = self.utb.send_cmd_val_parse_answer('TMU_CFG_GateTime', str((hex(100)))[2:], 0)
        self.checklog("set gate time", res)
        res = self.utb.send_cmd_parse_answer('TMU_CFG_Event0_Source_LowComp', 0)
        self.checklog("set source for Event0 to LowComp", res)
        res = self.utb.send_cmd_parse_answer('TMU_CFG_Event0_FallingEdge_Off', 0)
        self.checklog("deactivate Event0 trigger on falling edge", res)
        res = self.utb.send_cmd_parse_answer('TMU_CFG_LowComp_Source_MIO11', 0)
        self.checklog("set MIO11 (=Oscillator output) as comparator source", res)
        res = self.utb.send_cmd_val_parse_answer('TMU_CFG_LowComp_Level', 2.5, 0)
        self.checklog("set trigger level", res)
        res = self.utb.send_cmd_parse_answer('TMU_CFG_Event1_Source_LowComp', 0)
        self.checklog("set source for Event1 to LowComp", res)  # used for duty cycle measurement
        res = self.utb.send_cmd_parse_answer('TMU_CFG_Event1_FallingEdge_On', 0)
        self.checklog("set event1 to falling edge", res)  # used for duty cycle measurement

    #measure Oscillator
    @utb_connected
    def measure(self, quantity: TMUMeasurementQuantity):
        quantity = str(TMUMeasurementQuantity(quantity))[33:]
        ans = self.utb.send_cmd_parse_answer('TMU_MEAS_' + quantity, 0, hex if quantity == 'Count' else float)
        self.checklog("Measuring " + quantity + ": " + str(ans), ans)


class BMA280(Sensor):
    device_type = "BMA280"
    pwr_sources = [3, 4]

    i2c_addr = 0x18
    pins = {
        'I2C_SDA': 5, 'I2C_SCL': 7,
        'SPI_SDI': 5, 'SPI_SDO': 6, 'SPI_SCK': 7, 'SPI_CSB': 9,
        'PS': 8,  # protocol select (GND => SPI, VDDIO => I2C) at MIO8
        'INT1': 4, 'INT2': 3  # interrupt pins
    }
    register = {
        'acc_x': 0x02,
        'acc_y': 0x04,
        'acc_z': 0x06,
        'temp': 0x08
    }

    def __init__(self, utb: BsiInstrument, pwr_sources, pins, interface):
        super().__init__(utb)
        self.pwr_sources = pwr_sources
        self.pins = pins
        self.interface = interface
        self.utb_i2c = BsiI2c(self.utb, 1, 1)  
        self.measure_thread = BMA280AccelerationMeasurementThread(self, 'xyz', 1)

    #configure the Sensor
    @utb_connected
    def configure(self):
        res = True
        for src in self.pwr_sources:
            res = res and self.utb.pwr_set_supply_voltagemode(src, 0)
            res = res and self.utb.pwr_config_voltage_source(src, 0, 2.4, -0.1, 2, True)
        self.checklog("config VDD and VDDIO to 2.4V", res)

        # i2c
        res = self.utb.send_cmd_parse_answer('PWR_CFG_S4_MIO{:02d}_On'.format(self.pins['PS']), 0)
        self.checklog("use I2C as protocol", res)
        mio_config = [0x00] * 16
        mio_config[self.pins['I2C_SCL'] - 1] = 0x00802005
        mio_config[self.pins['I2C_SDA'] - 1] = 0x00802004
        mio_config[self.pins['SPI_SDO'] - 1] = 0x00000040  # SDO to GND to set slave addr to 0x18
        mio_config[self.pins['INT1'] - 1] = 0x00004000  # as input with pull down
        mio_config[self.pins['INT2'] - 1] = 0x00004000  # as input with pull down
        res = self.utb.mio_load_config(1, mio_config)
        res = res and self.utb.mio_activate_config(1, 0)
        self.checklog("configure I2C and interrupt pins", res)

        # bank voltages
        res = self.utb.mio_set_low_level_out(1, 0, 0)
        res = res and self.utb.mio_set_low_level_in(1, 0.2 * 2.4, 0)
        res = res and self.utb.mio_set_high_level_in(1, 0.8 * 2.4, 0)
        res = res and self.utb.mio_set_high_level_out(1, 2.4, 0)
        res = res and self.utb.mio_set_low_level_out(2, 0, 0)
        res = res and self.utb.mio_set_low_level_in(2, 0.2 * 2.4, 0)
        res = res and self.utb.mio_set_high_level_in(2, 0.8 * 2.4, 0)
        res = res and self.utb.mio_set_high_level_out(2, 2.4, 0)

        self.checklog("Setting Pin I/O Voltage Levels", res)

    @utb_connected
    def read(self, addr: bytearray, num_bytes: int = 1) -> Union[bytearray, bool]:
        """
        read register at address addr [0x00 to 0x3F]
        :param addr: start address to read from
        :param num_bytes: number of bytes to read
        :return: read bytes if succeed, else False
        """
        # read data
        res = self.utb_i2c.write(self.i2c_addr, addr)
        time.sleep(.010)
        ans = self.utb_i2c.read(self.i2c_addr, num_bytes)
        res = res and bool(ans)
        if res:
            self.checklog("Reading " + str(num_bytes) + " bytes at address 0x" +
                          ' '.join(format(x, '02X') for x in addr) + ": " +
                          ' '.join(format(x, '02X') for x in ans), res)
            return ans
        else:
            self.checklog("Reading " + str(num_bytes) + " bytes at address 0x" +
                          ' '.join(format(x, '02X') for x in addr), res)
            return False

    @utb_connected
    def write(self, addr: Union[int, bytearray], data: bytearray) -> bool:
        """
        write data to register at addr
        """
        # add addr word at start
        data.insert(0, addr)

        res = self.utb_i2c.write(self.i2c_addr, data)

        self.checklog("Writing " +
                      str(len(data) - 1) + " bytes at address 0x" + format(data[0], '02X') + ": " +
                      ' '.join(format(x, '02X') for x in data[1:]), res)
        return res

    @utb_connected
    def getTemperature(self) -> Optional[float]:
        """
        read the temperature register
        :return: the tempereature of the chip in °C, resolution is 0.5K
        """
        # ans = self.utb_i2c.write_read(self.i2c_addr, bytearray([self.register['temp']]), 1)
        res = self.utb_i2c.write(self.i2c_addr, bytearray(b'\x08'))
        ans = self.utb_i2c.read(self.i2c_addr, 1)
        if bool(ans):
            temp = 23 + int.from_bytes(ans, 'big', signed=True) / 2
            self.checklog("Temperature: {:.1f}°C".format(temp), bool(ans))
            return temp
        return None

    @utb_connected
    def getAcceleration(self, axis='xyz') -> Optional[dict]:
        # in python it's a bit complicated to achieve to combine the actual sensor value because we need to
        # convert between int to make use of bitoperators and bytes-object to cover the input value type of msb and lsb
        # and to interpret a 14-bit value as twos complement
        axis = set('xyz').intersection(set(axis))
        assert len(axis) in range(1, 4)
        # map register address of lsb to axis
        axis_addr = {ax: self.register['acc_' + ax].to_bytes(1, 'big') for ax in axis}
        ans = dict()
        for ax, lsb_addr in axis_addr.items():
            res = self.utb_i2c.write(self.i2c_addr, bytearray(lsb_addr))  # address of the lsb, needs to be read first
            print(res)
            lsb = self.utb_i2c.read(self.i2c_addr, 1)  # read lsb first
            print(lsb)
            lsb = int.from_bytes(lsb, "big")  # convert it to int to use bitoperators
            print(lsb)
            res = res and self.utb_i2c.write(self.i2c_addr,
                                             bytearray((int.from_bytes(lsb_addr, 'big') + 1).to_bytes(1, 'big')))
            msb = self.utb_i2c.read(self.i2c_addr, 1)
            msb = int.from_bytes(msb, "big")

            acc = ((msb << 8) + lsb) >> 2  # combine msb and first 6 bit of lsb for full 14bit sensor value
            if acc & 1 << 14 - 1:  # if first of the 14bits is 1, it's a signed value
                acc |= int('0b1100000000000000', 2)  # fill 14bit value with 1s to 16bit value
                acc = acc.to_bytes(2, 'big')  # now we can convert it back to a 2byte bytes-object
                acc = int.from_bytes(acc, 'big',
                                     signed=True)  # so now it's possible to use the python builtin function to convert it as a two's complement value back to int
            acc /= 4096  # convert from LSB to g
            self.checklog("Acceleration {}-axis: {:.3f}g".format(ax, acc), bool(res))
            ans[ax] = acc
        return ans

    @utb_connected
    def configureDTap(self):
        """
        write registers to enable interrupt for recognising double tap event on INT1-pin
        :return: True if success else False
        """
        res = self._ChangeBitInRegister(0x19, 4, 1)   # map interrupt to INT1-pin
        self.checklog("map interrupt to INT1-pin", res)
        res &= self.write(0x21, bytearray([0x0F]))  # set interrupt mode to latched
        self.checklog("set interrupt mode to latched", res)
        res &= self._ChangeBitInRegister(0x16, 4, 1)  # DTap interrupt enable
        self.checklog("DTap interrupt enable", res)
        return res

    @utb_connected
    def resetInterrupt(self):
        """
        reset the Interrupt in register 0x21 bit7
        :return: True if success else False
        """
        res = self._ChangeBitInRegister(0x21, 7, 1)
        self.checklog("reset Interrupt", res)
        return res

    @utb_connected
    def _ChangeBitInRegister(self, register: int, bit: int, mode: int) -> bool:
        """
        set or reset a bit in a 8bit-register but leave the other bytes as is
        :param register: register address, e.g. 0x21
        :param bit: 0 to 7
        :param mode: 1 to set bit, 0 to reset bit
        :return: True if success, else False
        """
        assert bit in range(8)
        assert mode in range(2)
        reg = self.read(bytearray([register]))
        if type(reg) is bool and not reg:
            return False
        reg = int.from_bytes(reg, 'big')
        if mode == 1:
            reg |= 1 << bit
        if mode == 0:
            reg &= ~(1 << bit)
        time.sleep(.01)
        res = self.write(register, bytearray([reg]))
        return res
    
class ADXL343(Sensor):
    device_type = "ADXL343"
    pwr_sources = [4]

    i2c_addr = 0x53
    pins = {
        'I2C_SDA': 5, 'I2C_SCL': 7,
        'SPI_SDI': 5, 'SPI_SDO': 6, 'SPI_SCK': 7, 'SPI_CSB': 9,
        'PS': 8,  # protocol select (GND => SPI, VDDIO => I2C) at MIO8
        'INT1': 4, 'INT2': 3,  # interrupt pins
        'GND' : 10
    }
    register = {
        'acc_x': 0x32,
        'acc_y': 0x34,
        'acc_z': 0x36,
    }

    def __init__(self, utb: BsiInstrument, pwr_sources, pins, interface):
        super().__init__(utb)
        self.pwr_sources = pwr_sources
        self.pins = pins
        self.interface = interface
        self.utb_i2c = BsiI2c(self.utb, 1, 1)  
        self.measure_thread = ADXL343AccelerationMeasurementThread(self, 'xyz', 1)

    #configure the Sensor
    @utb_connected
    def configure(self):
        res = True
        for src in self.pwr_sources:
            res = res and self.utb.pwr_set_supply_voltagemode(src, 0)
            res = res and self.utb.pwr_config_voltage_source(src, 0, 3.3, -0.1, 2, True)
        self.checklog("config VDD and VDDIO to 3.3V", res)

        # i2c
        res = self.utb.send_cmd_parse_answer('PWR_CFG_S4_MIO{:02d}_On'.format(self.pins['PS']), 0)
        res = self.utb.i2c_set_master_address(i2c_addr, 0, 1)
        self.checklog("Setting I2C Address", res)
        self.checklog("use I2C as protocol", res)
        mio_config = [0x00] * 16
        mio_config[self.pins['I2C_SCL'] - 1] = 0x00802005
        mio_config[self.pins['I2C_SDA'] - 1] = 0x00802004
        mio_config[self.pins['SPI_SDO'] - 1] = 0x00000040  # SDO to GND to set slave addr to 0x53
        mio_config[self.pins['SPI_CSB'] - 1] = 0x00000040  # CSB to GND to set slave addr to 0x53
        mio_config[self.pins['GND'] - 1] = 0x00000040  # CSB to GND to set slave addr to 0x53
        mio_config[self.pins['INT1'] - 1] = 0x00004000  # as input with pull down
        mio_config[self.pins['INT2'] - 1] = 0x00004000  # as input with pull down
        res = self.utb.mio_load_config(1, mio_config)
        res = res and self.utb.mio_activate_config(1, 0)
        self.checklog("configure I2C and interrupt pins", res)

        # bank voltages
        res = self.utb.mio_set_low_level_out(1, 0, 0)
        res = res and self.utb.mio_set_low_level_in(1, 0.2 * 3.3, 0)
        res = res and self.utb.mio_set_high_level_in(1, 0.8 * 3.3, 0)
        res = res and self.utb.mio_set_high_level_out(1, 3.3, 0)
        res = res and self.utb.mio_set_low_level_out(2, 0, 0)
        res = res and self.utb.mio_set_low_level_in(2, 0.2 * 3.3, 0)
        res = res and self.utb.mio_set_high_level_in(2, 0.8 * 3.3, 0)
        res = res and self.utb.mio_set_high_level_out(2, 3.3, 0)

        self.checklog("Setting Pin I/O Voltage Levels", res)

    @utb_connected
    def read(self, addr: bytearray, num_bytes: int = 1) -> Union[bytearray, bool]:
        """
        read register at address addr [0x00 to 0x3F]
        :param addr: start address to read from
        :param num_bytes: number of bytes to read
        :return: read bytes if succeed, else False
        """
        # read data
        res = self.utb_i2c.write(self.i2c_addr, addr)
        time.sleep(.10)
        ans = self.utb_i2c.read(self.i2c_addr, num_bytes)
        res = res and bool(ans)
        if res:
            self.checklog("Reading " + str(num_bytes) + " bytes at address 0x" +
                          ' '.join(format(x, '02X') for x in addr) + ": " +
                          ' '.join(format(x, '02X') for x in ans), res)
            return ans
        else:
            self.checklog("Reading " + str(num_bytes) + " bytes at address 0x" +
                          ' '.join(format(x, '02X') for x in addr), res)
            return False

    @utb_connected
    def write(self, addr: Union[int, bytearray], data: bytearray) -> bool:
        """
        write data to register at addr
        """
        # add addr word at start
        data.insert(0, addr)

        res = self.utb_i2c.write(self.i2c_addr, data)

        self.checklog("Writing " +
                      str(len(data) - 1) + " bytes at address 0x" + format(data[0], '02X') + ": " +
                      ' '.join(format(x, '02X') for x in data[1:]), res)
        return res


    @utb_connected
    def getAcceleration(self, axis='xyz') -> Optional[dict]:
        # in python it's a bit complicated to achieve to combine the actual sensor value because we need to
        # convert between int to make use of bitoperators and bytes-object to cover the input value type of msb and lsb
        # and to interpret a 16-bit value as twos complement
        axis = set('xyz').intersection(set(axis))
        assert len(axis) in range(1, 4)
        # map register address of lsb to axis
        axis_addr = {ax: self.register['acc_' + ax].to_bytes(1, 'big') for ax in axis}
        ans = dict()
        for ax, lsb_addr in axis_addr.items():
            res = self.utb_i2c.write(self.i2c_addr, bytearray(lsb_addr))  # address of the lsb, needs to be read first
            print(res)
            lsb = self.utb_i2c.read(self.i2c_addr, 1)  # read lsb first
            print(lsb)
            lsb = int.from_bytes(lsb, "big")  # convert it to int to use bitoperators
            print(lsb)
            res = res and self.utb_i2c.write(self.i2c_addr,
                                             bytearray((int.from_bytes(lsb_addr, 'big') + 1).to_bytes(1, 'big')))
            msb = self.utb_i2c.read(self.i2c_addr, 1)
            msb = int.from_bytes(msb, "big")

            acc = ((msb << 8) + lsb)  # combine msb and first 6 bit of lsb for full 14bit sensor value
            if acc & 1 << 16 - 1:  # if first of the 14bits is 1, it's a signed value
                acc |= int('0b1000000000000000', 2)  # fill 14bit value with 1s to 16bit value
                acc = acc.to_bytes(2, 'big')  # now we can convert it back to a 2byte bytes-object
                acc = int.from_bytes(acc, 'big',
                                     signed=True)  # so now it's possible to use the python builtin function to convert it as a two's complement value back to int
            #acc /= 4096  # convert from LSB to g
            self.checklog("Acceleration {}-axis: {:.3f}g".format(ax, acc), bool(res))
            ans[ax] = acc
        return ans

    @utb_connected
    def configureDTap(self):
        """
        write registers to enable interrupt for recognising double tap event on INT1-pin
        :return: True if success else False
        """
        res = self._ChangeBitInRegister(0x19, 4, 1)   # map interrupt to INT1-pin
        self.checklog("map interrupt to INT1-pin", res)
        res &= self.write(0x21, bytearray([0x0F]))  # set interrupt mode to latched
        self.checklog("set interrupt mode to latched", res)
        res &= self._ChangeBitInRegister(0x16, 4, 1)  # DTap interrupt enable
        self.checklog("DTap interrupt enable", res)
        return res

    @utb_connected
    def resetInterrupt(self):
        """
        reset the Interrupt in register 0x21 bit7
        :return: True if success else False
        """
        res = self._ChangeBitInRegister(0x21, 7, 1)
        self.checklog("reset Interrupt", res)
        return res

    @utb_connected
    def _ChangeBitInRegister(self, register: int, bit: int, mode: int) -> bool:
        """
        set or reset a bit in a 8bit-register but leave the other bytes as is
        :param register: register address, e.g. 0x21
        :param bit: 0 to 7
        :param mode: 1 to set bit, 0 to reset bit
        :return: True if success, else False
        """
        assert bit in range(8)
        assert mode in range(2)
        reg = self.read(bytearray([register]))
        if type(reg) is bool and not reg:
            return False
        reg = int.from_bytes(reg, 'big')
        if mode == 1:
            reg |= 1 << bit
        if mode == 0:
            reg &= ~(1 << bit)
        time.sleep(.01)
        res = self.write(register, bytearray([reg]))
        return res
    

class LPS22(Sensor):
    device_type = "LPS22"
    pwr_sources = [3, 4]

    i2c_addr = 0x5D
    pins = {
        'I2C_SDA': 5, 'I2C_SCL': 7,
        'SPI_SDI': 5, 'SPI_SDO': 6, 'SPI_SCK': 7, 'SPI_CSB': 9,
        'PS': 8,  # protocol select (GND => SPI, VDDIO => I2C) at MIO8
        'INT1': 4, 'INT2': 3  # interrupt pins
    }
    register = {
        'acc_x': 0x32,
        'acc_y': 0x34,
        'acc_z': 0x36,
    }

    def __init__(self, utb: BsiInstrument, pwr_sources, pins, interface):
        super().__init__(utb)
        self.pwr_sources = pwr_sources
        self.pins = pins
        self.interface = interface
        self.utb_i2c = BsiI2c(self.utb, 1, 1)  


    #configure the Sensor
    @utb_connected
    def configure(self):
        res = True
        for src in self.pwr_sources:
            res = res and self.utb.pwr_set_supply_voltagemode(src, 0)
            res = res and self.utb.pwr_config_voltage_source(src, 0, 3.3, -0.1, 2, True)
        self.checklog("config VDD and VDDIO to 3.3V", res)

        # i2c
        res = self.utb.send_cmd_parse_answer('PWR_CFG_S4_MIO{:02d}_On'.format(self.pins['PS']), 0)
        self.checklog("use I2C as protocol", res)
        mio_config = [0x00] * 16
        mio_config[self.pins['I2C_SCL'] - 1] = 0x00802005
        mio_config[self.pins['I2C_SDA'] - 1] = 0x00802004
        mio_config[self.pins['SPI_SDO'] - 1] = 0x00000040  # SDO to GND to set slave addr to 0x53
        mio_config[self.pins['INT1'] - 1] = 0x00004000  # as input with pull down
        mio_config[self.pins['INT2'] - 1] = 0x00004000  # as input with pull down
        res = self.utb.mio_load_config(1, mio_config)
        res = res and self.utb.mio_activate_config(1, 0)
        self.checklog("configure I2C and interrupt pins", res)

        # bank voltages
        res = self.utb.mio_set_low_level_out(1, 0, 0)
        res = res and self.utb.mio_set_low_level_in(1, 0.2 * 3.3, 0)
        res = res and self.utb.mio_set_high_level_in(1, 0.8 * 3.3, 0)
        res = res and self.utb.mio_set_high_level_out(1, 3.3, 0)
        res = res and self.utb.mio_set_low_level_out(2, 0, 0)
        res = res and self.utb.mio_set_low_level_in(2, 0.2 * 3.3, 0)
        res = res and self.utb.mio_set_high_level_in(2, 0.8 * 3.3, 0)
        res = res and self.utb.mio_set_high_level_out(2, 3.3, 0)

        self.checklog("Setting Pin I/O Voltage Levels", res)

    @utb_connected
    def read(self, addr: bytearray, num_bytes: int = 1) -> Union[bytearray, bool]:
        """
        read register at address addr [0x00 to 0x3F]
        :param addr: start address to read from
        :param num_bytes: number of bytes to read
        :return: read bytes if succeed, else False
        """
        # read data
        res = self.utb_i2c.write(self.i2c_addr, addr)
        time.sleep(.010)
        ans = self.utb_i2c.read(self.i2c_addr, num_bytes)
        res = res and bool(ans)
        if res:
            self.checklog("Reading " + str(num_bytes) + " bytes at address 0x" +
                          ' '.join(format(x, '02X') for x in addr) + ": " +
                          ' '.join(format(x, '02X') for x in ans), res)
            return ans
        else:
            self.checklog("Reading " + str(num_bytes) + " bytes at address 0x" +
                          ' '.join(format(x, '02X') for x in addr), res)
            return False

    @utb_connected
    def write(self, addr: Union[int, bytearray], data: bytearray) -> bool:
        """
        write data to register at addr
        """
        # add addr word at start
        data.insert(0, addr)

        res = self.utb_i2c.write(self.i2c_addr, data)

        self.checklog("Writing " +
                      str(len(data) - 1) + " bytes at address 0x" + format(data[0], '02X') + ": " +
                      ' '.join(format(x, '02X') for x in data[1:]), res)
        return res


    @utb_connected
    def getPressure(self):
        res = self.utb_i2c.write(self.i2c_addr, b'\0x28')  # address of the lsb, needs to be read first
        print(res)
        lsb = self.utb_i2c.read(self.i2c_addr, 1)  # read lsb first
        print(lsb)
        lsb = int.from_bytes(lsb, "big")  # convert it to int to use bitoperators
        print(lsb)
        res = res and self.utb_i2c.write(self.i2c_addr, b'\0x29')
        mid = self.utb_i2c.read(self.i2c_addr, 1)
        mid = int.from_bytes(mid, "big")
        print(mid)
        res = res and self.utb_i2c.write(self.i2c_addr, b'\0x2A')
        msb = self.utb_i2c.read(self.i2c_addr, 1)
        msb = int.from_bytes(msb, "big")
        print(mid)

        acc = ((msb << 16) + (mid << 8) + lsb)  # combine msb and first 6 bit of lsb for full 14bit sensor value

        self.checklog("Pressure {:.3f}g".format(acc), bool(res))
        return acc


    @utb_connected
    def _ChangeBitInRegister(self, register: int, bit: int, mode: int) -> bool:
        """
        set or reset a bit in a 8bit-register but leave the other bytes as is
        :param register: register address, e.g. 0x21
        :param bit: 0 to 7
        :param mode: 1 to set bit, 0 to reset bit
        :return: True if success, else False
        """
        assert bit in range(8)
        assert mode in range(2)
        reg = self.read(bytearray([register]))
        if type(reg) is bool and not reg:
            return False
        reg = int.from_bytes(reg, 'big')
        if mode == 1:
            reg |= 1 << bit
        if mode == 0:
            reg &= ~(1 << bit)
        time.sleep(.01)
        res = self.write(register, bytearray([reg]))
        return res

#used to measure in GUI
class BMA280AccelerationMeasurementThread(QThread):
    newValue = Signal(dict)

    def __init__(self, parent: BMA280, axis: Union[str, set] = 'xyz', dt: Union[int, float] = 1):
        """
        :param parent:
        :param axis: axis to be measured as set of x, y, z or string, e.g. 'xz'
        :param dt: refresh rate in seconds
        """
        super().__init__(parent)
        assert isinstance(parent, BMA280)
        axis = set('xyz').intersection(set(axis))
        assert len(axis) in range(1, 4)
        self.axis = axis
        self.dt = dt
        self.count = 0

    def run(self):
        try:
            assert self.parent().utb.connected
            while True:
                acc = self.parent().getAcceleration(self.axis)
                self.count += 1
                acc['count'] = self.count
                self.newValue.emit(acc)
                print(str(self.count), end=' ', flush=True)
                time.sleep(self.dt)
        except AssertionError as e:
            self.parent().checklog("UTB not connected", False)

    def terminate(self):
        print("measure thread terminated")
        super().terminate()

class ADXL343AccelerationMeasurementThread(QThread):
    newValue = Signal(dict)

    def __init__(self, parent: ADXL343, axis: Union[str, set] = 'xyz', dt: Union[int, float] = 1):
        """
        :param parent:
        :param axis: axis to be measured as set of x, y, z or string, e.g. 'xz'
        :param dt: refresh rate in seconds
        """
        super().__init__(parent)
        assert isinstance(parent, ADXL343)
        axis = set('xyz').intersection(set(axis))
        assert len(axis) in range(1, 4)
        self.axis = axis
        self.dt = dt
        self.count = 0

    def run(self):
        try:
            assert self.parent().utb.connected
            while True:
                acc = self.parent().getAcceleration(self.axis)
                self.count += 1
                acc['count'] = self.count
                self.newValue.emit(acc)
                print(str(self.count), end=' ', flush=True)
                time.sleep(self.dt)
        except AssertionError as e:
            self.parent().checklog("UTB not connected", False)

    def terminate(self):
        print("measure thread terminated")
        super().terminate()


class NTC(Sensor):
    device_type = "NTC"
    pwr_sources = 4

    def __init__(self, utb: BsiInstrument):
        
        super().__init__(utb)

    @utb_connected
    def configure(self):
        res = self.utb.mio_load_config(1,
                                       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x40, 0, 0, 0])
        res = res and self.utb.mio_activate_config(1, 0)
        self.checklog("set MIO13 as output", res)
        # config power source 4 in current mode for mio12
        # to prepare voltage measurement at NTC for calculating resistance
        res = self.utb.pwr_config_current_source(self.pwr_sources[0], 0, 0.1, -2, 8, True)
        self.checklog("set power source 4 as current source with 0.1A", res)
        res = self.utb.send_cmd_parse_answer('PWR_CFG_S4_MIO12_On', 0)
        self.checklog("switch power source 4 to MIO12", res)
        # config ADC
        res = self.utb.set_meas_range(0)
        self.checklog("set measurement range 0: 0 to 8V", res)
        res = self.utb.set_wait_time(100)
        self.checklog("set wait time after multiplexer set to 100ms", res)
        res = self.utb.set_sample_count(1000)
        self.checklog("set sample count to 1000", res)
        res = self.utb.set_sample_frequency(1000)
        self.checklog("set sample frequency to 1kHz", res)
        # config power source 3 as heater for 100 Ohm resistor
        res = self.utb.pwr_config_voltage_source(3, 0, 5, -2, 50, True)
        self.checklog(
            "set power source 3 as voltage source with 5V and Imax=50mA to serve together with 100Ohm as 0.25W heater",
            res)

    @utb_connected
    def heater_on(self):
        res = self.utb.pwr_set_closerelais(3, 0)
        res = res and self.utb.pwr_set_onoff(3, 0, 1)
        self.checklog("turn heater on", res)

    @utb_connected
    def heater_off(self):
        res = self.utb.pwr_set_onoff(3, 0, 0)
        res = res and self.utb.pwr_set_openrelais(3, 0)
        self.checklog("turn heater off", res)

    @utb_connected
    def measure_voltage(self):
        ans = self.utb.get_voltage('MIO12', 'MIO13')
        self.checklog("voltage at NTC in V = " + str(ans), bool(ans))


class ZenerDiode(Sensor):
    device_type = "Zener"
    
    init_voltage = 3
    pwr_sources = 3

    def __init__(self, utb: BsiInstrument):
        super().__init__(utb)

    @utb_connected
    def configure(self):
        res = self.utb.pwr_set_supply_voltagemode(self.pwr_sources[0], 0)
        self.checklog("set PMU in voltage mode", res)
        res = self.utb.pwr_config_voltage_source(self.pwr_sources[0], 0, self.init_voltage, -0.1, 5, True)
        self.checklog("configure PMU", res)

    @utb_connected
    def measure_current(self):
        ans = self.utb.pwr_get_current(self.pwr_sources[0], 1)  
        self.checklog("Current through PMU {}: I={}mA".format(self.pwr_sources[0], ans), bool(ans))

    @utb_connected
    def set_voltage(self, voltage):
        res = self.utb.pwr_set_supply_voltage(self.pwr_sources[0], voltage, 0)
        self.checklog("set V=" + str(voltage) + "V", res)



