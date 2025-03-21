
from SpektraBsi import BsiInstrument, BsiI2c, TMUMeasurementQuantity
import sensors
import time

if __name__ == '__main__':
    # UTB instance
    socket_addr = '192.168.001.77'
    evalutb = BsiInstrument()
    evalutb.last_address = socket_addr

    # components of eval board
    pwr_sources = [1]
    #pwr_sources = [3, 4]
    pins = {
        'I2C_SDA': 1, 'I2C_SCL': 2,
        'PS': 8,  # protocol select (GND => SPI, VDDIO => I2C) at MIO8
        'INT1': 4, 'INT2': 3,  # interrupt pins
        'GND' : 10
    }
    
    device = sensors.ADXL343(evalutb, pwr_sources, pins, 'I2C')
    #device = sensors.BMA280(evalutb, pwr_sources, pins, 'I2C')
    connected = evalutb.open_bsi(socket_addr)
    
    #device.configure()
    device.power_off()

    device.configure()

    device.power_on()

    device_id = device.read(b'\0x00')
    print("device_id:")
    print(device_id)

    for i in range(5):
        acc = device.getAcceleration('x')
        print(acc)
        time.sleep(2)

    device.power_off()
    connected = evalutb.disconnect()
    