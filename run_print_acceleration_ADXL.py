
from SpektraBsi import BsiInstrument, BsiI2c, TMUMeasurementQuantity
import sensors
import time

if __name__ == '__main__':
    # UTB instance
    socket_addr = '192.168.1.77'
    evalutb = BsiInstrument()
    evalutb.last_address = socket_addr

    # components of eval board
    pwr_sources = [1, 2]
    pins = {
        'I2C_SDA': 1, 'I2C_SCL': 2,
        'PS': 8,  # protocol select (GND => SPI, VDDIO => I2C) at MIO8
        'INT1': 4, 'INT2': 3,  # interrupt pins
        'GND' : 10
    }
    
    device = sensors.ADXL343(evalutb, pwr_sources, pins, 'I2C')

    connected = evalutb.open_bsi(socket_addr)
    
    #device.configure()
    device.power_off()

    device.configure()

    device.power_on()

    device_id = device.read(bytearray(b'\0x00'))
    print("device_id:")
    print(device_id)

    addr = int("0x0d", 16)
    #device.write(addr, bytearray(b'\0x08'))

    acc_x = device.read(bytearray(b'\0x32'), 2)
    print("acc in x:")
    print(acc_x)

    format = device.read(bytearray(b'\0x2d'))
    print("format:")
    print(format)

    for i in range(3):
        acc = device.getAcceleration('x')
        print(acc)
        time.sleep(2)

    device.power_off()
    connected = evalutb.disconnect()
    