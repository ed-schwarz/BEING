from gui import GUI_WINDOW
from SpektraBsi import BsiInstrument, BsiI2c, TMUMeasurementQuantity
from PySide6.QtWidgets import QApplication, QTextEdit, QWidget, QListWidgetItem
import sys
from sensors import BMA280

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # UTB instance
    socket_addr = '192.168.001.79'
    evalutb = BsiInstrument()
    evalutb.last_address = socket_addr

    # components of eval board
    pwr_sources = [3, 4]
    pins = {
        'I2C_SDA': 5, 'I2C_SCL': 7,
        'SPI_SDI': 5, 'SPI_SDO': 6, 'SPI_SCK': 7, 'SPI_CSB': 9,
        'PS': 8,  # protocol select (GND => SPI, VDDIO => I2C) at MIO8
        'INT1': 4, 'INT2': 3  # interrupt pins
    }
    
    bma280 = BMA280(evalutb, pwr_sources, pins)


    #window = EvalBoardWidget(evalutb, eeprom, osci, bma280, ntc, zener)
    window = GUI_WINDOW(evalutb, bma280)

    app.aboutToQuit.connect(bma280.measure_thread.terminate)

    window.show()
    app.exec()