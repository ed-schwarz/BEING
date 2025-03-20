from gui import GUI_WINDOW
from SpektraBsi import BsiInstrument, BsiI2c, TMUMeasurementQuantity
from PySide6.QtWidgets import QApplication, QTextEdit, QWidget, QListWidgetItem
import sys
import sensors
import time

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # UTB instance
    socket_addr = '192.168.001.77'
    evalutb = BsiInstrument()
    evalutb.last_address = socket_addr

    # components of eval board
    pwr_sources = [4]
    pins = {
        'I2C_SDA': 5, 'I2C_SCL': 7,
        'SPI_SDI': 5, 'SPI_SDO': 6, 'SPI_SCK': 7, 'SPI_CSB': 9,
        'PS': 8,  # protocol select (GND => SPI, VDDIO => I2C) at MIO8
        'INT1': 4, 'INT2': 3  # interrupt pins
    }
    
    device = sensors.LPS22(evalutb, pwr_sources, pins, 'I2C')
    #evalutb.set_sample_frequency(1500)
    connected = evalutb.open_bsi(socket_addr)
    print(connected)
    device.power_off()

    device.configure

    device.power_on()

    #device_id = device.read(b'\0x00')
    #print("device_id:")
    #print(device_id)

    for i in range(10):
        acc = device.getPressure()
        print(acc)
        time.sleep(2)

    device.power_off()
    connected = evalutb.disconnect()
    print(connected)