# BEING API

Python API to be used in the BEING project with the SPEKTRA S-Test

## Installation

Clone the directory using git clone <URL>
Install the required Packages: PySide6, numpy, scipy, pyqtgraph

## Usage

An example of the usage can be found in run_gui.py

### Sensors usage

```python
from SpektraBsi import BsiInstrument, BsiI2c, TMUMeasurementQuantity
from PySide6.QtWidgets import QApplication, QTextEdit, QWidget, QListWidgetItem
import sys
import sensors

app = QApplication(sys.argv)

# UTB instance
socket_addr = '192.168.001.79' #here the ip address written in your S-Test
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
    
bma280 = sensors.BMA280(evalutb, pwr_sources, pins, 'I2C')
```


### GUI usage

```python
from gui import GUI_WINDOW

window = GUI_WINDOW(evalutb, bma280)

app.aboutToQuit.connect(bma280.measure_thread.terminate)

window.show()
app.exec()
```



