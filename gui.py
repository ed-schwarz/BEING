import time

from PySide6.QtGui import QColorConstants, QPixmap, QPainter, QTextDocument, QWheelEvent, QMouseEvent, QTransform
from PySide6.QtWidgets import (QWidget, QTabWidget, QListWidget,
                               QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
                               QPushButton, QTextEdit, QLineEdit, QLabel, QListWidgetItem, QAbstractItemView, QSpinBox,
                               QFrame, QSizePolicy, QScrollArea, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                               QComboBox, QDoubleSpinBox, QCheckBox, QSlider)
from PySide6.QtCore import Qt, QPoint
import pyqtgraph

from SpektraBsi import BsiInstrument, TMUMeasurementQuantity


def get_traffic_light_pixmap(color=QColorConstants.Gray, radius=8):
    width, height = 2 * radius, 2 * radius
    px = QPixmap(width, height)
    px.fill(QColorConstants.White)
    p = QPainter(px)
    p.setBrush(color)
    p.drawEllipse(0, 0, width - 1, height - 1)
    p.end()
    return px


class EvalBoardWidget(QWidget):
    def __init__(self, utb: BsiInstrument, eeprom, osci, bma280, ntc, zener):
        super().__init__()

        self.utb = utb

        self.setWindowTitle("UTB EvalBoard")

        # connect area
        self.connectWidget = QWidget()
        self.IPLineEdit = QLineEdit(self.utb.last_address)
        self.IPLineEdit.setFont('Consolas')
        self.IPLineEdit.setFixedSize(112, 24)
        self.IPLineEdit.setInputMask('999.999.999.999;_')
        self.connectBtn = QPushButton("Connect")
        self.connectLayout = QHBoxLayout()
        self.connectLayout.addWidget(self.IPLineEdit)
        self.connectLayout.addWidget(self.connectBtn)
        self.connectWidget.setLayout(self.connectLayout)

        # tabview
        self.tabWidget = QTabWidget()
        # tabs
        self.eepromWidget = EepromWidget(eeprom)
        self.oscillatorWidget = OscillatorWidget(osci)
        self.bmaWidget = BMA280Widget(bma280)
        self.ntcWidget = NTCWidget(ntc)
        self.zenerWidget = ZenerWidget(zener)

        self.tabWidget.addTab(self.eepromWidget, "EEPROM")
        self.tabWidget.addTab(self.oscillatorWidget, "Oscillator")
        self.tabWidget.addTab(self.bmaWidget, "BMA280")
        self.tabWidget.addTab(self.ntcWidget, "NTC")
        self.tabWidget.addTab(self.zenerWidget, "Zener")

        # console
        self.consoleListWidget = QListWidget()
        self.consoleListWidget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.clearConsoleBtn = QPushButton("clear")

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.connectWidget)
        self.layout.addWidget(self.tabWidget)
        self.layout.addWidget(self.consoleListWidget)
        self.layout.addWidget(self.clearConsoleBtn)
        self.setLayout(self.layout)

        # connect signals
        self.connectBtn.clicked.connect(self.utb_connect)
        for idx in range(self.tabWidget.count()):
            self.tabWidget.widget(idx).device.output.connect(self.output_ListWidgetItem)
        self.clearConsoleBtn.clicked.connect(self.consoleListWidget.clear)

        self.tabWidget.setCurrentIndex(2)

    def utb_connect(self):
        if not self.utb.connected:
            self.consoleListWidget.addItem("Connecting to UTB @ " + self.IPLineEdit.text())
            self.consoleListWidget.update(self.consoleListWidget.indexAt(QPoint(0, 0)))
            self.repaint()
            # cut off leading zeros from IP
            ip = self.IPLineEdit.text()
            ps = ip.split(sep='.')
            pi = list()
            for e in ps:
                pi.append(int(e))
            ip = '.'.join(str(e) for e in pi)
            # connect
            res = self.utb.open_bsi(ip)
            if res:
                self.connectBtn.setText("Disconnect")
                self.eepromWidget.setEnabled(True)
                self.oscillatorWidget.setEnabled(True)
                self.bmaWidget.setEnabled(True)
                self.ntcWidget.setEnabled(True)
                self.zenerWidget.setEnabled(True)
                self.consoleListWidget.item(self.consoleListWidget.count() - 1).setIcon(
                    get_traffic_light_pixmap(QColorConstants.Green))
            else:
                self.consoleListWidget.item(self.consoleListWidget.count() - 1).setIcon(
                    get_traffic_light_pixmap(QColorConstants.Red))
        else:  # disconnect
            self.consoleListWidget.addItem("Disconnecting")
            self.consoleListWidget.update(self.consoleListWidget.indexAt(QPoint(0, 0)))
            self.repaint()

            res = self.utb.disconnect()
            if res:
                self.connectBtn.setText("Connect")
                self.eepromWidget.setEnabled(False)
                self.oscillatorWidget.setEnabled(False)
                self.bmaWidget.setEnabled(False)
                self.ntcWidget.setEnabled(False)
                self.zenerWidget.setEnabled(False)

                self.consoleListWidget.item(self.consoleListWidget.count() - 1).setIcon(
                    get_traffic_light_pixmap(QColorConstants.Green))
            else:
                self.consoleListWidget.item(self.consoleListWidget.count() - 1).setIcon(
                    get_traffic_light_pixmap(QColorConstants.Red))

    def output_ListWidgetItem(self, result, text):
        item = QListWidgetItem(text)
        item.setIcon(get_traffic_light_pixmap(QColorConstants.Green) if result else
                     get_traffic_light_pixmap(QColorConstants.Red))
        self.consoleListWidget.addItem(item)
        self.consoleListWidget.scrollToItem(item)


class DeviceWidget(QWidget):
    def __init__(self, device):
        """
        this Widget is thought to be derived
        Every device has the core functionality to power on/off and
        to configure its pin interface - this widget offers the dedicated
        buttons in a gridlayout
        :param device: instance of Device
        """
        super().__init__()

        # instance of device logic
        self.device = device

        # image for schematic
        self.schematicView = ImageWidget('./doc/schematics/' + self.device.device_type + '_schematic.png')
        self.schematicView.zoom(0.5)

        # cfg interface and pwr buttons
        self.buttonConfig = QPushButton("Cfg IFace")  # config power (pins, mode, levels etc.) and MIO pin interface
        self.pwrLabel = QLabel("Power")
        self.pwrLabel.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.buttonPowerOn = QPushButton("On")
        self.buttonPowerOn.setFixedSize(50, 24)
        self.buttonPowerOff = QPushButton("Off")
        self.buttonPowerOff.setFixedSize(50, 24)
        self.labelPowerStatus = QLabel()
        self.labelPowerStatus.setPixmap(get_traffic_light_pixmap(QColorConstants.Red))

        # layout
        self.layout = QGridLayout()
        self.layout.addWidget(self.schematicView, 0, 0, 1, -1)
        self.layout.addWidget(self.buttonConfig, 1, 0)
        self.layout.addWidget(self.pwrLabel, 1, 1)
        self.layout.addWidget(self.buttonPowerOn, 1, 2)
        self.layout.addWidget(self.buttonPowerOff, 1, 3)
        self.layout.addWidget(self.labelPowerStatus, 1, 4)
        self.setLayout(self.layout)

        # disabled as default as long as no connection to BSI
        self.setEnabled(False)

        # connect signals
        self.buttonPowerOn.clicked.connect(self.powerOn)
        self.buttonPowerOff.clicked.connect(self.powerOff)
        self.buttonConfig.clicked.connect(self.device.configure)

    def powerOn(self):
        res = self.device.power_on()
        self.labelPowerStatus.setPixmap(get_traffic_light_pixmap(QColorConstants.Green) if res else
                                        get_traffic_light_pixmap(QColorConstants.Red))
        self.buttonConfig.setEnabled(False)

    def powerOff(self):
        res = self.device.power_off()
        self.labelPowerStatus.setPixmap(get_traffic_light_pixmap(QColorConstants.Red) if res else
                                        get_traffic_light_pixmap(QColorConstants.Green))
        self.buttonConfig.setEnabled(True)


class EepromWidget(DeviceWidget):
    def __init__(self, eeprom):
        super().__init__(eeprom)

        self.buttonWrite = QPushButton("write")
        self.labelAddress = QLabel("address")
        self.labelAddress.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.labelAddress2 = QLabel("address")
        self.labelAddress2.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.WriteAddrLineEdit = QLineEdit("AA")
        self.WriteAddrLineEdit.setFont('Consolas')
        self.WriteAddrLineEdit.setFixedSize(21, 24)
        # self.WriteAddrLineEdit.setMaxLength(2)
        self.WriteAddrLineEdit.setInputMask('>HH;_')
        self.WriteDataLineEdit = QLineEdit("A0 AF")
        self.WriteDataLineEdit.setFont('Consolas')
        self.WriteDataLineEdit.setFixedSize(168, 24)
        # self.WriteDataLineEdit.setMaxLength(2*8+7)
        self.WriteDataLineEdit.setInputMask('>HH hh hh hh hh hh hh hh;_')
        self.buttonRead = QPushButton("read")
        self.ReadAddrLineEdit = QLineEdit("00")
        self.ReadAddrLineEdit.setFont('Consolas')
        self.ReadAddrLineEdit.setFixedSize(21, 24)
        self.ReadAddrLineEdit.setInputMask('>HH;_')
        self.ReadNumBytesSpinBox = QSpinBox()
        self.ReadNumBytesSpinBox.setMaximum(255)
        self.ReadNumBytesSpinBox.setMinimum(1)
        self.ReadNumBytesSpinBox.setValue(8)
        self.ReadNumBytesSpinBox.setButtonSymbols(QSpinBox.ButtonSymbols.PlusMinus)
        self.ReadNumBytesSpinBox.setFont('Consolas')
        self.ReadNumBytesSpinBox.setFixedSize(45, 24)

        self.layout.addWidget(self.buttonWrite, 2, 0)
        self.layout.addWidget(self.labelAddress, 2, 1)
        self.layout.addWidget(self.WriteAddrLineEdit, 2, 2)
        self.layout.addWidget(QLabel("data"), 2, 3)
        self.layout.addWidget(self.WriteDataLineEdit, 2, 4)
        self.layout.addWidget(self.buttonRead, 3, 0)
        self.layout.addWidget(self.labelAddress2, 3, 1)
        self.layout.addWidget(self.ReadAddrLineEdit, 3, 2)
        self.layout.addWidget(QLabel("amount"), 3, 3)
        self.layout.addWidget(self.ReadNumBytesSpinBox, 3, 4)

        self.setLayout(self.layout)

        # connect signals
        self.buttonWrite.clicked.connect(self.write)
        self.buttonRead.clicked.connect(self.read)

    def write(self):
        addr = int(self.WriteAddrLineEdit.text(), 16)
        data_str = self.WriteDataLineEdit.text().split(sep=" ")
        data = bytearray()
        for e in data_str:
            if len(e) == 2:
                data.append(int(e, 16))
        self.device.write(addr, data)

    def read(self):
        addr = bytearray()
        addr.insert(0, int(self.ReadAddrLineEdit.text(), 16))
        self.device.read(addr, self.ReadNumBytesSpinBox.value())


class OscillatorWidget(DeviceWidget):
    def __init__(self, osci):
        super().__init__(osci)

        self.buttonMeasure = QPushButton("Measure")
        self.ComboboxQuantitiy = QComboBox()
        self.ComboboxQuantitiy.insertItems(0, ['Frequency', 'Time', 'Count', 'DutyCycle'])

        # TODO: add widget showing the oscillator waveform

        self.layout.addWidget(self.buttonMeasure, 2, 0)
        self.layout.addWidget(self.ComboboxQuantitiy, 2, 1)

        self.buttonMeasure.clicked.connect(self.measure)

    def measure(self):
        quantity = TMUMeasurementQuantity(self.ComboboxQuantitiy.currentIndex())
        self.device.measure(quantity)


class BMA280Widget(DeviceWidget):
    def __init__(self, bma):
        super().__init__(bma)

        self.t = []
        self.x = []
        self.y = []
        self.z = []

        self.buttonTemp = QPushButton("read temperature")
        self.labelTemp = QLabel("°C")
        self.buttonAcc = QPushButton("read acceleration")
        self.labelAcc = QLabel("g")
        self.buttonPlot = QPushButton("Plot")

        self.plotWidget = pyqtgraph.PlotWidget()
        self.line_x = self.plotWidget.plot(self.t, self.x, pen=pyqtgraph.mkPen(color='r', width=2), name="x")
        self.line_y = self.plotWidget.plot(self.t, self.y, pen=pyqtgraph.mkPen(color='g', width=2), name="y")
        self.line_z = self.plotWidget.plot(self.t, self.z, pen=pyqtgraph.mkPen(color='b', width=2), name="z")

        self.LineCheckBoxsWidget = QWidget()
        self.checkBoxX = QCheckBox("x")
        self.checkBoxY = QCheckBox("y")
        self.checkBoxZ = QCheckBox("z")
        self.layoutLineCheckBoxs = QHBoxLayout()
        self.layoutLineCheckBoxs.addWidget(self.checkBoxX)
        self.layoutLineCheckBoxs.addWidget(self.checkBoxY)
        self.layoutLineCheckBoxs.addWidget(self.checkBoxZ)
        for idx in range(self.layoutLineCheckBoxs.count()):
            self.layoutLineCheckBoxs.itemAt(idx).widget().setChecked(True)
        self.LineCheckBoxsWidget.setLayout(self.layoutLineCheckBoxs)

        self.labelRefreshRate = QLabel("Plot Refresh Rate [ms]")
        self.sliderRefreshRate = QSlider()
        self.sliderRefreshRate.setOrientation(Qt.Orientation.Horizontal)
        self.sliderRefreshRate.setMinimum(10)
        self.sliderRefreshRate.setMaximum(1000)
        self.sliderRefreshRate.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sliderRefreshRate.setTickInterval(100)
        self.sliderRefreshRate.setSingleStep(10)
        self.sliderRefreshRate.setPageStep(100)

        self.buttonRead = QPushButton("read")
        self.ReadAddrLineEdit = QLineEdit("00")
        self.ReadAddrLineEdit.setFont('Consolas')
        self.ReadAddrLineEdit.setFixedSize(21, 24)
        self.ReadAddrLineEdit.setInputMask('>HH;_')
        self.ReadNumBytesSpinBox = QSpinBox()
        self.ReadNumBytesSpinBox.setMaximum(63)
        self.ReadNumBytesSpinBox.setMinimum(1)
        self.ReadNumBytesSpinBox.setValue(1)
        self.ReadNumBytesSpinBox.setButtonSymbols(QSpinBox.ButtonSymbols.PlusMinus)
        self.ReadNumBytesSpinBox.setFont('Consolas')
        self.ReadNumBytesSpinBox.setFixedSize(45, 24)

        self.buttonWrite = QPushButton("write")
        self.WriteAddrLineEdit = QLineEdit("19")
        self.WriteAddrLineEdit.setFont('Consolas')
        self.WriteAddrLineEdit.setFixedSize(21, 24)
        self.WriteAddrLineEdit.setInputMask('>HH;_')
        self.labelAddress = QLabel("address")
        self.labelData = QLabel("data")
        self.WriteDataLineEdit = QLineEdit("19")
        self.WriteDataLineEdit.setFont('Consolas')
        self.WriteDataLineEdit.setFixedSize(21, 24)
        self.WriteDataLineEdit.setInputMask('>HH;_')

        self.buttonCfgDTab = QPushButton("config Double Tap Interrupt")
        self.buttonResetInt = QPushButton("reset Interrupt")

        self.layout.addWidget(self.buttonTemp, 2, 0)
        self.layout.addWidget(self.labelTemp, 2, 1)
        self.layout.addWidget(self.buttonAcc, 3, 0)
        self.layout.addWidget(self.labelAcc, 3, 1)
        self.layout.addWidget(self.buttonPlot, 4, 0)
        self.layout.addWidget(self.LineCheckBoxsWidget, 4, 1, 1, -1)
        self.layout.addWidget(self.sliderRefreshRate, 5, 0, 1, 3)
        self.layout.addWidget(self.labelRefreshRate, 5, 3)
        self.layout.addWidget(self.buttonRead, 6, 0)
        self.layout.addWidget(self.ReadAddrLineEdit, 6, 1)
        self.layout.addWidget(self.ReadNumBytesSpinBox, 6, 2)
        self.layout.addWidget(self.buttonWrite, 7, 0)
        self.layout.addWidget(self.labelAddress, 7, 1)
        self.layout.addWidget(self.WriteAddrLineEdit, 7, 2)
        self.layout.addWidget(self.labelData, 7, 3)
        self.layout.addWidget(self.WriteDataLineEdit, 7, 4)
        self.layout.addWidget(self.buttonResetInt, 8, 0)
        self.layout.addWidget(self.buttonCfgDTab, 8, 1)

        self.buttonTemp.clicked.connect(self.getTemperature)
        self.buttonAcc.clicked.connect(self.getAcceleration)
        self.buttonPlot.clicked.connect(self.plot)
        self.sliderRefreshRate.valueChanged.connect(self.setPlotRefreshRate)
        self.sliderRefreshRate.setValue(self.device.measure_thread.dt * 1000)
        self.checkBoxX.toggled.connect(self.line_x.setVisible)
        self.checkBoxY.toggled.connect(self.line_y.setVisible)
        self.checkBoxZ.toggled.connect(self.line_z.setVisible)
        self.device.measure_thread.newValue.connect(self.addPointToPlot)
        self.buttonRead.clicked.connect(self.readRegister)
        self.buttonWrite.clicked.connect(self.writeRegister)
        self.buttonResetInt.clicked.connect(self.device.resetInterrupt)
        self.buttonCfgDTab.clicked.connect(self.device.configureDTap)

    def readRegister(self):
        addr = bytearray()
        addr.insert(0, int(self.ReadAddrLineEdit.text(), 16))
        self.device.read(addr, self.ReadNumBytesSpinBox.value())

    def writeRegister(self):
        addr = int(self.WriteAddrLineEdit.text(), 16)
        data_str = self.WriteDataLineEdit.text().split(sep=" ")
        data = bytearray()
        for e in data_str:
            if len(e) == 2:
                data.append(int(e, 16))
        self.device.write(addr, data)

    def getTemperature(self):
        temp = self.device.getTemperature()
        if temp is not None:
            self.labelTemp.setText("{:.1f}°C".format(temp))

    def getAcceleration(self):
        axis = ''.join([ax for ax, state in [('x', self.checkBoxX.isChecked()),
                                             ('y', self.checkBoxY.isChecked()),
                                             ('z', self.checkBoxZ.isChecked())] if state])

        acc = self.device.getAcceleration(axis)
        self.labelAcc.setText(str(acc))

    def setPlotRefreshRate(self, mdt):
        self.device.measure_thread.dt = mdt / 1000
        self.labelRefreshRate.setText("Plot Refresh Rate: {}ms".format(mdt))

    def plot(self):
        # exchange schematicview with plotwidget
        if self.layout.itemAtPosition(0, 0).widget() == self.schematicView:
            self.schematicView.hide()
            self.layout.removeWidget(self.schematicView)
            self.layout.addWidget(self.plotWidget, 0, 0, 1, -1)
            self.plotWidget.show()
            self.buttonPlot.setText("Schematic")
            # start live measuring
            self.device.measure_thread.start()
        else:
            # stop live measuring
            self.device.measure_thread.terminate()
            self.plotWidget.hide()
            self.layout.removeWidget(self.plotWidget)
            self.layout.addWidget(self.schematicView, 0, 0, 1, -1)
            self.schematicView.show()
            self.buttonPlot.setText("Plot")

    def addPointToPlot(self, pt: dict):
        self.t.append(pt['count'])
        axis = set('xyz').intersection(pt.keys())
        assert len(axis) in range(1, 4)
        if 'x' in axis:
            self.x.append(pt['x'])
            self.line_x.setData(self.t, self.x)
        if 'y' in axis:
            self.y.append(pt['y'])
            self.line_y.setData(self.t, self.y)
        if 'z' in axis:
            self.z.append(pt['z'])
            self.line_z.setData(self.t, self.z)


class NTCWidget(DeviceWidget):
    def __init__(self, ntc):
        super().__init__(ntc)

        self.buttonHeaterOn = QPushButton("Heater On")
        self.buttonHeaterOff = QPushButton("Heater Off")
        self.buttonMeasure = QPushButton("Measure")
        self.labelHeater = QLabel("Heater")
        self.labelHeater.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.layout.addWidget(self.buttonMeasure, 2, 0)
        self.layout.addWidget(self.labelHeater, 2, 1)
        self.layout.addWidget(self.buttonHeaterOn, 2, 2)
        self.layout.addWidget(self.buttonHeaterOff, 2, 3)

        self.buttonHeaterOn.clicked.connect(self.device.heater_on)
        self.buttonHeaterOff.clicked.connect(self.device.heater_off)
        self.buttonMeasure.clicked.connect(self.device.measure_voltage)


class ZenerWidget(DeviceWidget):
    def __init__(self, ntc):
        super().__init__(ntc)

        self.buttonMeasureCurrent = QPushButton("Meassure I")
        self.buttonSetVoltage = QPushButton("Set V")
        self.doubleSpinBoxVoltage = QDoubleSpinBox()
        self.doubleSpinBoxVoltage.setMaximum(8)
        self.doubleSpinBoxVoltage.setMinimum(1)
        self.doubleSpinBoxVoltage.setSingleStep(.1)
        self.doubleSpinBoxVoltage.setValue(self.device.init_voltage)  # TODO: supports only card 1
        self.doubleSpinBoxVoltage.setButtonSymbols(QSpinBox.ButtonSymbols.PlusMinus)
        self.doubleSpinBoxVoltage.setFont('Consolas')
        self.doubleSpinBoxVoltage.setFixedSize(45, 24)

        self.layout.addWidget(self.doubleSpinBoxVoltage, 2, 0)
        self.layout.addWidget(self.buttonSetVoltage, 2, 1)
        self.layout.addWidget(self.buttonMeasureCurrent, 2, 3)

        self.buttonMeasureCurrent.clicked.connect(self.device.measure_current)
        self.buttonSetVoltage.clicked.connect(self.set_voltage)

    def set_voltage(self):
        self.device.set_voltage(self.doubleSpinBoxVoltage.value())


class ImageWidget(QGraphicsView):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # TODO: better implement a QImage -> leads to better quality when downscaling, but problems with panning occur
        self._pixmap_item = QGraphicsPixmapItem(QPixmap(path))
        self._scene.addItem(self._pixmap_item)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        self._scale_factor = 1.0

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self._scale_factor *= 1.1
        else:
            self._scale_factor /= 1.1
        self.zoom(self._scale_factor)

    def zoom(self, zoom_factor, zoom_min=0.1, zoom_max=5.0):
        self._scale_factor = zoom_factor
        self._scale_factor = max(zoom_min, min(zoom_max, self._scale_factor))
        self.setTransform(QTransform().scale(self._scale_factor, self._scale_factor))
