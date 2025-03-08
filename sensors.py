import time
import numpy as np

class Sensor:
  def __init__(self, interface, frequency, PWR_VDD, PWR_VDDIO, sock):
    self.interface = interface
    self.frequency = frequency
    self.PWR_VDD = PWR_VDD
    self.PWR_VDDIO = PWR_VDDIO
    self.sock = sock
    self.init_config_s_test()
    self.set_frequency()
    match self.interface:
      case "SPI":
        self.SPI_config()
      case "I2C":
        self.I2C_config()


  def enable_spi(self):
    # DIG_SPI1_Enable,022,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    self.send_to_s_test(b"DIG_SPI1_Enable,022,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")

  def disable_spi(self):
    # DIG_SPI1_Disable,022,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    print("placeholder")

  def init_config_s_test(self):
    self.send_to_s_test(b"DIG_CFG_LOADMIOSETUP1,000,2,0,0,0,0,0,0,0,0,0,0,90,14,93,4000,91,0,0,0,0,0,0,0")
    self.send_to_s_test(b"DIG_CFG_SETHIGHLEVELOUTBANK1,002,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4")
    self.send_to_s_test(b"DIG_CFG_SETHIGHLEVELINBANK1,005,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0")
    self.send_to_s_test(b"DIG_CFG_SETLOWLEVELINBANK1,004,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7")
    self.send_to_s_test(b"DIG_CFG_SETLOWLEVELOUTBANK1,003,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0")
    self.send_to_s_test(b"DIG_CFG_SETHIGHLEVELOUTBANK2,006,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4,2.4")
    self.send_to_s_test(b"DIG_CFG_SETHIGHLEVELINBANK2,005,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0")
    self.send_to_s_test(b"DIG_CFG_SETLOWLEVELINBANK2,004,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7,0.7")
    self.send_to_s_test(b"DIG_CFG_SETLOWLEVELOUTBANK2,007,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0")

  def SPI_config(self):
    self.send_to_s_test(b"DIG_SPI1_CFG_SetCPOLHigh,014,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    self.send_to_s_test(b"DIG_SPI1_CFG_SetCPHAHigh,014,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    self.send_to_s_test(b"DIG_SPI1_CFG_SetFrameLength,123,18,18,0,0,0,0,0,0,0,0,0,0,0,0,0,0")

  def I2C_config(self):
    self.send_to_s_test(b"DIG_SPI1_CFG_SetCPOLHigh,014,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    self.send_to_s_test(b"DIG_SPI1_CFG_SetCPHAHigh,014,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    self.send_to_s_test(b"DIG_SPI1_CFG_SetFrameLength,123,18,18,0,0,0,0,0,0,0,0,0,0,0,0,0,0")

  def _parse_answer(self, answer, remove_first_elements=0, convert_to_type=None,
                    card_select=0, separate_hex_nibbles=2):
    """
    splits answer from BSI to int list, separator is ',', removes '/n',
    removes first elements, converts answer to list of (float, int, hex, bool
    (BSI 'O'=TRUE, 'E'=FALSE), 'andbool' (AND calculation over all Bool
    of existing BSI cards)
    if conversion type is None no conversion is done and list of strings will be returned
    :param answer: string to convert
    :param remove_first_elements: number of leading list elements to remove
    :param convert_to_type: conversion type
    :param card_select: 1,2,..16 (single card) or 0 (all cards)
    :param separate_hex_nibbles: nr of hex nibble to convert to int (f.e.'ff'=2 or 'ffff'=4)
    :return:  converted value (single or list depends on card_select and conversion type)
    (type depends on conversion type)
    """
    if answer is None:
      return None
    return_list = answer.strip('\n')
    return_list = return_list.split(',')
    if return_list[-1] == '\n':
      return_list = return_list[:-1]  # strip newline at end of answer
    if remove_first_elements > 0:
      return_list = return_list[remove_first_elements:]
    if card_select > 0:
      res = self._convert_string(return_list[card_select - 1], convert_to_type,
                                 '', separate_hex_nibbles)
      return res
    for ind in range(len(return_list)):
      return_list[ind] = self._convert_string(return_list[ind], convert_to_type,
                                              '', separate_hex_nibbles)
    # card_select is 0 (allcards and bool has to be build over all EXISTING cards)
    if convert_to_type == 'andbool':
      for ind in range(self.bsi_nr_cards):
        if not return_list[ind]:
          return False
      return True
    return return_list


  def set_frequency_SPI(self):
    # DIG_SPI1_CFG_SETFREQUENCY,000,1e6
    self.send_to_s_test(b"DIG_SPI1_CFG_SETFREQUENCY,000,1e6")

  def set_frequency_I2C(self):
    # DIG_SPI1_CFG_SETFREQUENCY,000,1e6
    self.send_to_s_test()

  def set_frequency(self):
    # DIG_SPI1_CFG_SETFREQUENCY,000,1e6
    match self.interface:
      case "SPI":
        self.set_frequency_SPI()
      #case "I2C":
        #self.set_frequency_I2C()

  def read_SPI(self, address):
    #read data using DIG_I2C1_Read or DIG_SPI_Read
    return self.read_from_s_test()

  def read_I2C(self, i2c_address):
    cmd = 'DIG_I2C' + str(i2c_address) + '_Read'
    return self.read_from_s_test(cmd.encode('ascii'))


  def read_register(self, address):
    #read data using DIG_I2C1_Read or DIG_SPI_Read
    match self.interface:
      case "SPI":
        res = self.read_SPI(address)
      case "I2C":
        res = self.read_I2C(address)

    return self._parse_answer(res, 2, 'andbool', 1)

  def write_SPI(self, data, address):
    #read data using DIG_I2C1_Read or DIG_SPI_Read
    self.send_to_s_test("placeholder")

  def write_I2C(self, data, address):
    #read data using DIG_I2C1_Read or DIG_SPI_Read
    self.send_to_s_test("placeholder")


  def write_register(self, data, address):
    #write data using DIG_I2C1_Write or DIG_SPI_Write
    match self.interface:
      case "SPI":
        self.write_SPI(data, address)
      case "I2C":
        self.write_I2C(data, address)

  def send_to_s_test(self, cmd):
    self.sock.sendall(cmd)


  def read_from_s_test(self, cmd):
    self.sock.sendall(cmd)
    return self.sock.recv(1024)

#accelerator sensor
class BMA280(Sensor):
  def __init__(self, interface, frequency, PWR_VDD, PWR_VDDIO, sock):
    super().__init__(interface, frequency, PWR_VDD, PWR_VDDIO, sock)
    self.PWR_VDDIO = PWR_VDDIO
    self.set_power_vdd()
    self.set_power_vddio()
    self.set_power_on()
    self.start_meas()
    self.enable_spi()


  def get_chip_id(self):
    addr = 0x0
    return self.read_register(addr)

  def set_power_vdd(self):
    '''
    instead of 3 PWR_VDD
    PWR_CFG_VOLTAGEMODE3,014,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    PWR_CFG_IMAX3,016,1.9,1.9,1.9,,,,,,,,,,,,,
    PWR_CFG_IMIN3,018,-1,-1,,,,,,,,,,,,,,
    PWR_CFG_RelClose3,022,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    PWR_CFG_SETV3,026,2.4,2.4,,,,,,,,,,,,,,
    '''
    self.send_to_s_test(b"PWR_CFG_VOLTAGEMODE3,014,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    self.send_to_s_test(b"PWR_CFG_IMAX3,016,1.9,1.9,1.9,,,,,,,,,,,,,")
    self.send_to_s_test(b"PWR_CFG_IMIN3,018,-1,-1,,,,,,,,,,,,,,")
    self.send_to_s_test(b"PWR_CFG_RelClose3,022,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    self.send_to_s_test(b"PWR_CFG_SETV3,026,2.4,2.4,,,,,,,,,,,,,,")

  def set_power_vddio(self):
    '''
    instead of 3 PWR_VDDIO
    PWR_CFG_VOLTAGEMODE3,014,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    PWR_CFG_IMAX3,016,1.9,1.9,1.9,,,,,,,,,,,,,
    PWR_CFG_IMIN3,018,-1,-1,,,,,,,,,,,,,,
    PWR_CFG_RelClose3,022,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    PWR_CFG_SETV3,026,2.4,2.4,,,,,,,,,,,,,,
    '''
    self.send_to_s_test(b"PWR_CFG_VOLTAGEMODE4,015,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    self.send_to_s_test(b"PWR_CFG_IMAX4,017,1.9,1.9,1.9,,,,,,,,,,,,,")
    self.send_to_s_test(b"PWR_CFG_IMIN4,019,-1,-1,,,,,,,,,,,,,,")
    self.send_to_s_test(b"PWR_CFG_RelClose4,023,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    self.send_to_s_test(b"PWR_CFG_SETV4,027,2.4,2.4,,,,,,,,,,,,,,")

  def set_power_on_vdd(self):
    '''
    instead of 3 PWR_VDD
    PWR_ON3,024,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    '''
    self.send_to_s_test(b"PWR_ON3,024,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")

  def set_power_on_vddio(self):
    '''
    instead of 3 PWR_VDDIO
    PWR_ON3,024,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    '''
    self.send_to_s_test(b"PWR_ON4,025,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")

  def set_power_off_vdd(self):
    '''
    instead of 3 PWR_VDD
    PWR_OFF3,024,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    '''
    self.send_to_s_test(b"PWR_CFG_SETV3,003,0,0,,,,,,,,,,,,,,")
    self.send_to_s_test(b"PWR_OFF3,024,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")

  def set_power_off_vddio(self):
    '''
    instead of 3 PWR_VDDIO
    PWR_OFF3,024,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    '''
    self.send_to_s_test(b"PWR_CFG_SETV4,003,0,0,,,,,,,,,,,,,,")
    self.send_to_s_test(b"PWR_OFF4,025,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")

  def activate_mio(self):
    self.send_to_s_test(b"DIG_CFG_ACTIVATEMIOSETUP1,001,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0")

  def set_power_on(self):
    self.set_power_vdd()
    self.set_power_vddio()
    time.sleep(0.1)

  def set_power_off(self):
    self.set_power_off_vdd()
    self.set_power_off_vddio()
    time.sleep(0.1)

  def reset_sensor(self):
    self.set_power_off()
    time.sleep(0.5)
    self.set_power_on()

  def start_meas_vdd(self):
    self.send_to_s_test(b"MEAS_V_High3S_Low3S,001")
    self.send_to_s_test(b"MEAS_I_3,028")

  def start_meas_vddi(self):
    self.send_to_s_test(b"MEAS_V_High4S_Low4S,001")
    self.send_to_s_test(b"MEAS_I_4,028")

  def start_meas(self):
    self.start_meas_vdd()
    self.start_meas_vddi()

  def set_SPI_pins(self, SDI, SDO, SCK):
    self.PIN1 = SDI
    self.PIN2 = SDO
    self.PIN12 = SCK

  def set_I2C_pins(self, SDI, SDO, SCL):
    self.PIN1 = SDI
    self.PIN2 = SDO
    self.PIN12 = SCL

  def get_acceleration_lsb_x(self):
    addr = 0x2
    return self.read_register(addr)

  def get_acceleration_msb_x(self):
    addr = 0x3
    return self.read_register(addr)

  def get_acceleration_lsb_y(self):
    addr = 0x4
    return self.read_register(addr)

  def get_acceleration_msb_y(self):
    addr = 0x5
    return self.read_register(addr)

  def get_acceleration_lsb_z(self):
    addr = 0x6
    return self.read_register(addr)
    #sock.sendall(b"Hello, world")
    #return self.sock.recv(1024)

  def get_acceleration_msb_z(self):
    addr = 0x7
    return self.read_register(addr)

  def get_temperature(self):
    addr = 0x8
    return self.read_register(addr)

  def get_acceleration_x(self):
    lsb = self.get_acceleration_lsb_x()
    msb = self.get_acceleration_msb_x()
    return lsb + (msb << 6)

  def get_acceleration_y(self):
    lsb = self.get_acceleration_lsb_y()
    msb = self.get_acceleration_msb_y()
    return lsb + (msb << 6)

  def get_acceleration_z(self):
    lsb = self.get_acceleration_lsb_z()
    msb = self.get_acceleration_msb_z()
    return lsb + (msb << 6)

  def get_dummy_sin(self, i):
    return np.sin(2 * np.pi * (0.001 * i))
