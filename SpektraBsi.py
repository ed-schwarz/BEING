"""
@package python_test_library.SpektraBsi
This module cotains basic BSI IO.

Module for BSI handling

defgroup BSI_MODULE SPEKTRA BSI Functionality

This module supports SPEKTRA BSI (S-TEST)
 supported functionality:
 * Voltage measurement
 * I2C SYS Interface
 * I/O configuration
 * Logical Input/Output
 * SPI
 * Power modules
"""

import socket
import threading
import time
import configparser
from typing import Union
from I2cInterface import I2cInterface
from enum import Enum


class TMUMeasurementQuantity(Enum):
    TMUMeasureFrequency = 0
    TMUMeasureTime = 1
    TMUMeasureCount = 2
    TMUMeasureDutyCycle = 3


class BsiProcessingError(Exception):
    """
    MODULE Exeption handler
    """
    pass


class BsiInstrument:
    """
    Class for BSI handling\n
    * analog measure
    * digital IO
    * power supply
    * SPI communication
    * I2C communication
    """
    # class members
    connected = False
    last_address = "127.0.0.0"
    last_port = 21
    bsi_socket = None
    bsi_timeout = 5.0
    bsi_id = None
    bsi_card_serials = list()
    bsi_nr_cards = 0
    bsi_cmd_counter = 0
    bsi_i2c_adresses = list()
    bsi_i2c_write_framelen = list()
    bsi_i2c_read_framelen = list()

    def __init__(self):
        """
        constructor
        """
        self.lock = threading.Lock()
        self.connected = False
        self.last_address = "127.0.0.0"
        self.last_port = 21
        self.bsi_socket = None
        self.bsi_timeout = 5.0
        self.bsi_id = None
        self.bsi_card_serials = list()
        self.bsi_nr_cards = 0
        self.bsi_cmd_counter = 0
        self.bsi_i2c_adresses = list()
        self.bsi_i2c_write_framelen = list()
        self.bsi_i2c_read_framelen = list()

    def __del__(self):
        """
        destructor
        :return: None
        """
        # self.bsi_socket.shutdown(socket.SHUT_RDWR)
        # print('Closing BSI...')
        if self.connected:
            self.bsi_socket.close()
            self.bsi_socket = None
            self.connected = False

    def _opensocket(self):
        """
        create open socket for ethernet communication, if not exist
        :return:
        """
        # Marco gave the good hint, that socket with noDelay Flag
        # noch schneller reagieren. -> TCP_NODELAY through setsockopt
        if self.bsi_socket is None:
            self.bsi_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            # make it an non blocing socket, by setting a timeout (for blocking use None)
            # qucik time out prevents open functions to complete
            self.bsi_socket.settimeout(self.bsi_timeout)  # 10.0)
            self.bsi_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def open_bsi(self, address, port=21):
        """
        opens bsi_instrument communication, reads id and card serialnumbers
        :param address: IP address as string f.e. '192.168.1.3'
        :param port: port number optioanla as int
        :return: True if connected and ready, else false
        """
        self._opensocket()
        print('Connecting to BSI ' + str(address) + ' ...', end='')
        self.last_port = port
        self.last_address = address
        self.connected = False
        try:
            self.bsi_socket.connect((address, port))
            self.connected = True
        except Exception as ex:
            print('NOT CONNECTED, ' + str(ex))
        if self.connected:
            # self.flush_receive()
            print('OK')
            self.bsi_id = self.get_id()
            print(self.bsi_id[0], end='')
            self.read_card_serials()
            print(', ' + str(self.bsi_nr_cards) + ' cards'
                  + ' (SN ' + str(self.bsi_card_serials) + ')')
        return self.connected

    def flush_receive(self):
        """
        flushes socket receive buffer
        :return: None
        """
        while 1:
            try:
                self.bsi_socket.settimeout(0.1)
                self.bsi_socket.recv(1024)
            except Exception as ex:
                print(str(ex))
                break
        self.bsi_socket.settimeout(self.bsi_timeout)

    def disconnect(self):
        try:
            assert self.connected
            print("Close connection")
            self.bsi_socket.shutdown(socket.SHUT_RDWR)
            self.bsi_socket.close()
            self.bsi_socket = None
            self.connected = False
            return True
        except Exception as ex:
            print(str(ex))
            return False

    def reconnect(self):
        """
        reconnect, close socket, open socket, open bsi (use only if communication problems exist)
        :return: True if bsi is ready after reconnect
        """
        print("Reconnect BSI")
        if self.connected:
            try:
                self.bsi_socket.shutdown(socket.SHUT_RDWR)
                self.bsi_socket.close()
                self.bsi_socket = None
            except Exception as ex:
                print(str(ex))
                pass
        self.connected = False
        return self.open_bsi(self.last_address, self.last_port)

    def set_timeout(self, timeout):
        """
        sets socket timeout in sec
        :param timeout: timeout as float 1sec = 1.0
        :return: None
        """
        self.bsi_socket.settimeout(timeout)

    def get_timeout(self):
        """
        reads socket timeout in sec
        :return: timeout in sec as float 1sec = 1.0
        """
        return self.bsi_socket.gettimeout()

    def get_connected(self):
        """
        returns connected status
        :return: True if connected
        """
        return self.connected

    def get_nrofcards(self):
        """
        returns number of cards in bsi_instrument system
        :return: number of cards as int
        """
        return self.bsi_nr_cards

    def get_idlist(self):
        """
        returns list of of card_ids
        :return: list of id as string list (list lenght depend on cards in BSI)
        """
        return self.bsi_id

    def get_card_serials(self):
        """
        returns list of card serialnumbers
        :return: list of serialnumbers as stringlist (list lenght depend on cards in BSI)
        """
        return self.bsi_card_serials

    def _send(self, command, params=''):
        """
        builds and sends command, increments command counter
        :param command: command as string f. e. 'SYS_IDN'
        :param params:  (optional) as  string ( seperated by ',' if necessary)
        :return: number of bytes sent as int
        """
        self.bsi_cmd_counter += 1
        if self.bsi_cmd_counter >= 1000:
            self.bsi_cmd_counter = 1
        cmd = command + ',' + "{:03d}".format(self.bsi_cmd_counter)
        if params != '':
            cmd += ',' + params
        cmd += '\n'
        try:
            bytes_sent = self.bsi_socket.send(bytes(cmd, 'utf-8'))
        except Exception as ex:
            bytes_sent = 0
            print(str(ex))
        return bytes_sent

    def _receive(self, buffersize=1024):
        """
        reads from bsi_instrument with timeout
        and encodes with utf-8 (if more than 1024 characters received loops)
        until \n as last character received
        :return: complete answer as string, '' on timeout
        """
        try:
            data = str(self.bsi_socket.recv(buffersize), encoding="utf-8")
            # recv(.., flags = socket.MSG_DONTWAIT)
            # has no meaning in windows / doesn't excists there
            # starting with small buffers (e.g. 32) for short ACKs won't
            # makes it faster -> just a tiny bit, but then program spends more time in sleep.
            #  check for end of message character -> otherwise there might be further data
            for ind in range(100):
                if data[-1:] == "\n":
                    break
                time.sleep(0.01)
                data += str(self.bsi_socket.recv(buffersize), encoding="utf-8")
        except Exception as ex:
            data = ''
            print(str(ex))
        return data

    def _query(self, command, params=''):
        """
        sends command and reads answer
        :param command: command as string f. e. 'SYS_IDN'
        :param params: (optional) as  string ( seperated by ',' if necessary)
        :return: complete answer as string,
        """
        # print (command)
        with self.lock:  # TODO: make this method thread safe AND efficient
            bytes_sent = self._send(command, params)
            data = None
            if bytes_sent != 0:
                data = self._receive()
                if data.startswith("E"):
                    raise BsiProcessingError(data)
        return data

    # def llv_read_reg(self, address):
    #     par=f"1,RD,{address}"
    #     data = self._query('LLV_BSI',par)
    #     # <A000,001,RD,404,0
    #     data = self._parse_answer(data)
    #     if (data[2] == "RD") and (data[3] == str(address)):
    #         return int(data[4])  # just get the data
    #     else:
    #         raise BSI_processing_error(f"No Read from reg {address}: {str(data)}")
    #     pass

    @staticmethod
    def _convert_string(data_string, convert_to_type, default='', separate_hex_nibbles=2):
        """
        helper function for parse_answer, converts answer parts to int,float, hex....
        :param data_string: string to convert
        :param convert_to_type: type(f.e. int, float, hex, bool,'andbool');
        'anbool'=convert list to bool and then ands all bool
        :param default: default answer string
        :param separate_hex_nibbles: nr of hex nibble to convert to int (f.e.'ff'=2 or 'ffff'=4)
        :return: list (type of list elements depends on conversion type)
        """
        if convert_to_type is None:
            return data_string
        if data_string != '':
            if convert_to_type == int:
                return int(data_string)  # convert to int
            if convert_to_type == float:
                return float(data_string)  # convert to float
            if convert_to_type == hex:
                if separate_hex_nibbles > 0:
                    if len(data_string) == separate_hex_nibbles:
                        return int(data_string, 16)  # convert to hex
                    else:
                        b_list = list()
                        # l = len(data_string)
                        nr_bytes = int(len(data_string) / separate_hex_nibbles)
                        for elem in range(nr_bytes):
                            hex_str = '0x' + str(data_string[separate_hex_nibbles
                                                             * elem: (separate_hex_nibbles * elem)
                                                                     + separate_hex_nibbles])
                            b_list.append(int(hex_str, 16))
                        return b_list
                else:
                    return int(data_string, 16)  # convert to hex
            if (convert_to_type == bool) or (convert_to_type == 'andbool'):
                if data_string == 'O':
                    return True
                return False
        else:
            return default

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

    # def _check_oklist(self,li,card_select):
    #     if(card_select==0):
    #         for class_found in li:
    #             if(class_found==False):
    #                 return False
    #     else:
    #         if(li[card_select-1]==False):
    #             return False
    #     return True

    @staticmethod
    def _create_param_list_string(value, default, card_select, create_hex=False):
        """
        creates pameter list for BSI (AL,HL,...) dependent on card_select

        :param value: option_name for list elements to create
        :param default:  is option_name for not selected/not existing cards
        :param card_select: 1,2,..16 (single card) or 0 (all cards)
        :param create_hex: True=convert to hex (for example 15->0F 1023->03FF...)
        :return: string (for use as parameter list in bsi command)
        """
        str_var: str = ''
        if card_select == 0:
            for crd_nr in range(16):
                if not create_hex:
                    str_var += str(value) + ','
                else:
                    str_hex = hex(value)
                    str_hex = str_hex[2:]  # cut 0x
                    # be sure to have equal number of nibbles
                    if (len(str_hex) % 2) == 1:
                        str_hex = '0' + str_hex
                    str_var += str_hex + ','
        else:
            for crd_nr in range(16):
                if crd_nr == card_select - 1:
                    if not create_hex:
                        str_var += str(value) + ','
                    else:
                        str_hex = hex(value)
                        str_hex = str_hex[2:]  # cut 0x
                        # be sure to have equal number of nibbles
                        if (len(str_hex) % 2) == 1:
                            str_hex = '0' + str_hex
                        str_var += str_hex + ','  # format(value, '#04x')[2:]
                else:
                    str_var += str(default)
                    str_var += ','
        str_var = str_var[:-1]
        return str_var

    def send_cmd_parse_answer(self, cmd, card_select, parsetype='andbool', parseparam=1):
        """
        sends command, waits for answer, parses answer

        :param cmd: command as string
        :param card_select: 1,2,..16 (single card) or 0 (all cards)
        :param parsetype: float, int, hex, bool
        (BSI 'O'=TRUE, 'E'=FALSE), 'andbool' (AND calculation over all Bool
        of existing BSI cards)
        :return: converted value (single or list depends on card_select and conversion type)
        (type depends on conversion type)
        """
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, parsetype, card_select, parseparam)
        return res

    def send_cmd_val_parse_answer(self, cmd: str, value: str, card_select: int, parsetype='andbool', parseparam=1):
        """
        sends command, waits for answer, parses answer

        :param cmd: command as string
        :param value: value as string
        :param card_select: 1,2,..16 (single card) or 0 (all cards)
        :param parsetype: float, int, hex, bool
        (BSI 'O'=TRUE, 'E'=FALSE), 'andbool' (AND calculation over all Bool
        of existing BSI cards)
        :return: converted value (single or list depends on card_select and conversion type)
        (type depends on conversion type)
        """
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string(value, '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, parsetype, card_select, parseparam)
        return res

    def get_id(self):
        """
        reads id string of bsi_instrument
        :return: bsi id as string
        """
        res = self._query("SYS_IDN")
        res = self._parse_answer(res, 2)
        return res

    def read_card_serials(self):
        """
        reads card serial numbers from bsi
        :return: list of serialnumbers (string) (list lenght depend on cards in BSI)
        """
        res = self._query("SYS_GetBSISnr")
        res = self._parse_answer(res, 2)
        res = [x for x in res if x]  # remove empty list entries
        self.bsi_card_serials = []
        self.bsi_nr_cards = len(res)
        # convert BSI card serial(hex) numbers to int
        if self.bsi_nr_cards > 0:
            for i in range(self.bsi_nr_cards):
                self.bsi_card_serials.append(str(int(res[i], 16)))
        return self.bsi_card_serials

    # ************************************************************************
    # VOLTAGE MEASUREMENT
    # ************************************************************************

    def get_meas_range(self):
        """
        reads measuring range (1=-2....25V, 0=-2...8V)
        !!! all cards !!!
        :return: measuring range as int
        """
        res = self._query('MEAS_CFG_GetRange')
        res = self._parse_answer(res, 2, int, 1)
        return res

    def set_meas_range(self, meas_range):
        """
        sets measuring range (1=-2....25V, 0=-2...8V) !!! all cards !!!
        :param meas_range: 1=-2....25V, 0=-2...8V as int
        :return: True=success
        """
        res = self._query('MEAS_CFG_SetRange', str(meas_range))
        res = self._parse_answer(res, 2, 'andbool', 1)
        return res

    def set_sample_count(self, samples_per_average=1000):
        """
        sets sample count for analog measurement (per average)
        !!! all cards !!!
        :param samples_per_average: measuring count (int)
        :return: True=success
        """
        res = self._query('MEAS_CFG_SetSampleCnt', str(samples_per_average))
        res = self._parse_answer(res, 2, 'andbool', 1)
        return res

    def set_sample_frequency(self, sample_freq=1000):
        """
        sets sample frequency (=sample rate) for analog measurement
        !!! all cards !!!
        :param sample_freq: sample frequency in Hz (int)
        :return: True=success
        """
        res = self._query('MEAS_CFG_SetSampleFreq', str(sample_freq))
        res = self._parse_answer(res, 2, 'andbool', 1)
        return res

    def set_wait_time(self, wait_time=10):
        """
        sets wait time in ms after multiplexer set for analog measurement
        !!! all cards !!!
        :param wait_time: wait time in ms (int)
        :return: True=success
        """
        res = self._query('MEAS_CFG_SetWaitTime', str(wait_time))
        res = self._parse_answer(res, 2, 'andbool', 1)
        return res

    def get_voltage(self, high_pin, low_pin, card_select=0):
        """
        reads/measures voltage between 2 pins of BSI
        :param high_pin: pinname like 'MIO01'
        (see BSI Command documention: Pin names vary by function!!!)
        :param low_pin: pinname like 'MIO01'
        (see BSI Command documention: Pin names vary by function!!!)
        :param card_select: 1,2,..16 (single card) or 0 (all cards=default)
        :return: voltage as list of float (depends on card_select)
        """
        res = self._query('MEAS_V_' + high_pin + '_' + low_pin)
        res = self._parse_answer(res, 2, float, card_select)
        return res

    def get_voltage_autorange(self, high_pin, low_pin, card_select=0):
        """
        sets measrange to 1 (high range)
        measure voltage between 2 pins
        measures again in measrange 0 if result is <= 8V
        :param high_pin: pinname like 'MIO01'
        (see BSI Command documention: Pin names vary by function!!!)
        :param low_pin: pinname like 'MIO01'
        (see BSI Command documention: Pin names vary by function!!!)
        :param card_select: 1,2,..16 (single card) or 0 (all cards=default)
        :return: voltage as list of float (depends on card_select)
        """
        res = self.set_meas_range(1)
        if res is not None:
            res = self._query('MEAS_V_' + high_pin + '_' + low_pin)
            res = self._parse_answer(res, 2, float, card_select)
            if res is not None:
                if res <= 8.0:
                    self.set_meas_range(0)
                    res = self._query('MEAS_V_' + high_pin + '_' + low_pin)
                    res = self._parse_answer(res, 2, float, card_select)
        return res

    def get_voltage_autorange_by_cmd(self, cmd, params, card_select=0):
        """
        see get_voltage_autorange, but no pins are defined.
        use this if pins are not supported by default.
        implement low_level command string to measure between nearly any pins
        (see BSI Command documention for low level measuring commands)
        :param cmd: low level command as string
        :param params: parameter string (see documentation)
        :param card_select:  1,2,..16 (single card) or 0 (all cards=default)
        :return: voltage as list of float (depends on card_select)
        """
        res = self.set_meas_range(1)
        if res is not None:
            res = self._query(cmd, params)
            res = self._parse_answer(res, 2, float, card_select)
            if res is not None:
                if res <= 8.0:
                    self.set_meas_range(0)
                    res = self._query(cmd, params)
                    res = self._parse_answer(res, 2, float, card_select)
        return res

    # ************************************************************************
    # CONFIGURATION
    # ************************************************************************

    def mio_get_config(self, card_select=0):
        """
        reads active mio configuration
        (see BSI documentation for details)
        :param card_select: 1,2,..16 (single card) or 0 (all cards=default)
        :return: TODO
        """
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        cmd = 'DIG_CFG_GetActivateMIOSetup'
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, hex, card_select, 8)  # 8 nibble characters
        # delete first 8 list elements (Version + spare)
        if card_select > 0:
            res = res[7:]
        else:
            for ind in range(len(res)):
                res[ind] = res[ind][7:]
        return res

    def mio_load_config(self, config_number, config_list):
        """
        writes configuration-set to config-set number
        after this you must activate configuration if you want use it!!!
        :param config_number: configuration set number as int 1..20
        :param config_list: configuration set list
        (f.e.[0x50,0x51,0x14,0x53,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
        MIO1=SPI-MOSI, MIO2=SPI-CS, MIO3=SPI-MISO, MIO4=SPI-CLK,...
        for values see BSI documentation
        :return: True= success
        """
        cmd = 'DIG_CFG_LoadMIOSetup' + str(config_number)
        str_var = '1,0,0,0,0,0,0,'
        for ind in range(16):
            str_hex = hex(config_list[ind])
            str_hex = str_hex[2:]  # cut 0x
            # be sure to have equal number of nibbles
            if (len(str_hex) % 2) == 1:
                str_hex = '0' + str_hex
            str_var += str_hex + ','  # format(value, '#04x')[2:]
        str_var = str_var[:-1]
        res = self._query(cmd, str_var)
        res = self._parse_answer(res, 2, bool, 1)
        return res

    def mio_activate_config(self, config_number, card_select=0):
        """
        activates configuration-set with config-set number on desired card
        must be loaded before
        :param config_number: config set number to activate 1...20 (int)
        :param card_select: 1,2,..16 (single card) or 0 (all cards=default)
        :return: True= success
        """
        cmd = 'DIG_CFG_ActivateMIOSetup' + str(config_number)
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def mio_set_high_level_out(self, bank, voltage, card_select=0):
        """
        sets output level(voltage) for pin HIGH
        :param bank: IO bank 1...4 as int
        :param voltage: level voltage as float or string
        :param card_select:  1,2,..16 (single card) or 0 (all cards=default)
        :return: True= success
        """
        cmd = 'DIG_CFG_SetHighLevelOutBank' + str(bank)
        f_list = self._create_param_list_string(str(voltage), '', card_select, False)
        res = self._query(cmd, f_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def mio_set_low_level_out(self, bank, voltage, card_select=0):
        """
        sets output level(voltage) for pin LOW
        :param bank: IO bank 1...4 as int
        :param voltage: level voltage as float or string
        :param card_select:  1,2,..16 (single card) or 0 (all cards=default)
        :return: True= success
        """
        cmd = 'DIG_CFG_SetLowLevelOutBank' + str(bank)
        f_list = self._create_param_list_string(str(voltage), '', card_select, False)
        res = self._query(cmd, f_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def mio_set_high_level_in(self, bank, voltage, card_select=0):
        """
        sets input threshold voltage for input HIGH
        :param bank: IO bank 1...4 as int
        :param voltage: threshold voltage as float or string
        :param card_select:  1,2,..16 (single card) or 0 (all cards=default)
        :return: True= success
        """
        cmd = 'DIG_CFG_SetHighLevelInBank' + str(bank)
        f_list = self._create_param_list_string(str(voltage), '', card_select, False)
        res = self._query(cmd, f_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def mio_set_low_level_in(self, bank, voltage, card_select=0):
        """
        sets input threshold voltage for input LOW
        :param bank: IO bank 1...4 as int
        :param voltage: threshold voltage as float or string
        :param card_select:  1,2,..16 (single card) or 0 (all cards=default)
        :return: True= success
        """
        cmd = 'DIG_CFG_SetLowLevelInBank' + str(bank)
        f_list = self._create_param_list_string(str(voltage), '', card_select, False)
        res = self._query(cmd, f_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def mio_get_high_level_out(self, bank, card_select=0):
        """
        reads output level(voltage) for pin HIGH
        :param bank: IO bank 1...4 as int
        :param card_select: 1,2,..16 (single card) or 0 (all cards=default)
        :return: list of float (depends on card select)
        """
        cmd = 'DIG_CFG_GetHighLevelOutBank' + str(bank)
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, float, card_select)
        return res

    def mio_get_low_level_out(self, bank, card_select=0):
        """
        reads output level(voltage) for pin LOW
        :param bank: IO bank 1...4 as int
        :param card_select: 1,2,..16 (single card) or 0 (all cards=default)
        :return: list of float (depends on card select)
        """
        cmd = 'DIG_CFG_GetLowLevelOutBank' + str(bank)
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, float, card_select)
        return res

    def mio_get_high_level_in(self, bank, card_select=0):
        """
        reads input threshold voltage for pin HIGH
        :param bank: IO bank 1...4 as int
        :param card_select: 1,2,..16 (single card) or 0 (all cards=default)
        :return: list of float (depends on card select)
        """
        cmd = 'DIG_CFG_GetHighLevelInBank' + str(bank)
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, float, card_select)
        return res

    def mio_get_low_level_in(self, bank, card_select=0):
        """
        reads input threshold voltage for pin LOW
        :param bank:  IO bank 1...4 as int
        :param card_select: 1,2,..16 (single card) or 0 (all cards=default)
        :return: list of float (depends on card select)
        """
        cmd = 'DIG_CFG_GetLowLevelInBank' + str(bank)
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, float, card_select)
        return res

    def mio_set_gnd(self, bank, gnd_bank_nr, card_select=0):
        """
        sets ground for digital IO bank
        :param bank:  IO bank 1...4
        :param gnd_bank_nr: 0=AGND, 1=GND1, 2=GND2... as int
        :param card_select: 1,2,..16 (single card) or 0 (all cards=default)
        :return: True= success
        """
        if gnd_bank_nr == 0:
            cmd = 'DIG_CFG_Bank' + str(bank) + '_Agnd'
        else:
            cmd = 'DIG_CFG_Bank' + str(bank) + '_Gnds' + str(gnd_bank_nr)
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def mio_get_gnd(self, bank, card_select=0):
        """
        reads DGND for IO bank
        :param bank: IO bank 1...4
        :param card_select: 1,2,..16 (single card) or 0 (all cards=default)
        :return: list of int (1...4) (depends on card select)
        """
        cmd = 'DIG_CFG_GetBank' + str(bank) + '_Gnds'
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, int, card_select)
        return res

    def mio_get_agnd(self, bank, card_select=0):
        """
        reads AGND for IO bank
        :param bank: IO bank 1...4
        :param card_select: 1,2,..16 (single card) or 0 (all cards=default)
        :return: list of int (depends on card select)
        """
        cmd = 'DIG_CFG_GetBank' + str(bank) + '_Agnd'
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, int, card_select)
        return res

    # ************************************************************************
    # Digital I/O
    # ************************************************************************
    def mio_get_state_all(self, card_select=0):
        """
        reads MIO pin input state of all MIO pins
        :param card_select:  1,2,..16 (single card)
        :return: input state as int16
        """
        cmd = 'DIG_GetMIOState'
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, hex, card_select, 4)
        return res

    def mio_set_output_high(self, mio_number, card_select):
        """
        set MIO pin HIGH (must pe configured as output)
        :param mio_number: MIO number 1...16 as int
        :param card_select: 1,2,..16 (single card)
        :return: True if success
        """
        conf = self.mio_get_config(card_select)
        if (conf[mio_number - 1] & 0x40) == 0x40:
            conf[mio_number - 1] |= 0x01
            self.mio_load_config(card_select, conf)
            self.mio_activate_config(card_select, card_select)
        else:
            print('Err: MIO' + str(mio_number) + ' is not Output')
            return False
        return True

    def mio_set_output_low(self, mio_number, card_select):
        """
        set MIO pin LOW (must pe configured as output)
        :param mio_number: MIO number 1...16 as int
        :param card_select: 1,2,..16 (single card)
        :return: True if success
        """
        conf = self.mio_get_config(card_select)
        if (conf[mio_number - 1] & 0x40) == 0x40:
            conf[mio_number - 1] &= 0xFFFE
            self.mio_load_config(card_select, conf)
            self.mio_activate_config(card_select, card_select)
        else:
            print('Err: MIO' + str(mio_number) + ' is not Output')
            return False
        return True

    def mio_get_input(self, mio_number, card_select):
        """
        reads MIO pin input state
        :param mio_number:  MIO number 1...16 as int
        :param card_select: 1,2,..16 (single card)
        :return: 1=High. 0=Low
        """
        res = self.mio_get_state_all(card_select)
        mask = 2 ** (mio_number - 1)
        if card_select > 0:
            res = res & mask
            if res > 0:
                res = 1
        else:
            for ind in range(len(res)):
                if res[ind] != '':
                    res[ind] = res[ind] & mask
                    if res[ind] > 0:
                        res[ind] = 1
        return res

    def mio_set_high_z(self, on=True, card_select=0):
        """
        set all MIOs to High-Z state or return to usual operation, if on = False
        
        :param on: True -> High-Z, False -> Normal Operation
        :param card_select:  1,2,..16 (single card) or 0 (all cards=default)
        :return: True= success
        """
        cmd = 'DIG_CFG_MIO_Highz'
        if on:
            cmd += "_ON"
        else:
            cmd += "_OFF"
        f_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, f_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

        # ************************************************************************

    # POWER
    # ************************************************************************

    def pwr_set_closerelais(self, source_number, card_select):
        """
        close power relais

        :param source_number: power source 1...4
        :param card_select: 1,2,..16 (single card) or 0 (all cards)
        :return: True if successfull
        """
        # create AL as int ',,128,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        cmd = 'PWR_CFG_RelClose' + str(source_number)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, 'andbool', 1)
        return res

    def pwr_set_openrelais(self, source_number, card_select):
        """
        open power relais

        :param source_number: power source 1...4
        :param card_select: 1,2,..16 (single card) or 0 (all cards)
        :return: True if successfull
        """
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        cmd = 'PWR_CFG_RelOpen' + str(source_number)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, 'andbool', 1)
        return res

        # ************************************************************************
        # POWER Voltage Mode
        # ************************************************************************

    def pwr_get_source_current(self, source_number, card_select=0):
        """
        reads source current

        :param source_number: 1...4 as int
        :param card_select: 0 (default): return is list of voltages float (listlen depends on number of cards in BSI)
                          1 voltage float of card1
                          2 voltage float of card2 ...
        :return: see param card_select
        """
        res = self._query('MEAS_I_' + str(source_number))
        res = self._parse_answer(res, 2, float, card_select)
        return res

    def pwr_set_supply_voltage(self, source_number, voltage, card_select):
        """
        sets supply voltage

        :param source_number: 1...4 as int
        :param voltage: voltage as float
        :param card_select: 0 all cards
                            1 voltage float of card 1
                            2 voltage float of card 2 ...
        :return: True if successful
        """
        FL = self._create_param_list_string(voltage, '', card_select, False)
        cmd = 'PWR_CFG_SetV' + str(source_number)
        res = self._query(cmd, FL)
        res = self._parse_answer(res, 2, 'andbool', 1)
        return res

    def pwr_get_supply_voltage_force(self, source_number, card_select):
        """
        reads supply voltage force high pin against sense low pin

        :param source_number: 1...4 as int
        :param card_select: 0 all cards
                            1 voltage float of card 1
                            2 voltage float of card 2 ...
        :return: voltage as float
        """
        # MEAS_V_HighXF_LowXS
        cmd = 'MEAS_V_High' + str(source_number) + 'F_Low' + str(source_number) + 'S'
        res = self._query(cmd)
        res = self._parse_answer(res, 2, float, card_select)
        return res

    def pwr_get_supply_voltage_sense(self, source_number, card_select):
        """
        reads supply voltage sense high pin against sense low pin

        :param source_number: 1...4 as int
        :param card_select: 0 all cards
                            1 voltage float of card 1
                            2 voltage float of card 2 ...
        :return: voltage as float
        """
        # MEAS_V_HighXS_LowXS
        cmd = 'MEAS_V_High' + str(source_number) + 'S_Low' + str(source_number) + 'S'
        res = self._query(cmd)
        res = self._parse_answer(res, 2, float, card_select)
        return res

    def pwr_set_supply_voltagemode(self, source_number, card_select):
        """
        sets supply voltage mode

        :param source_number: 1...4 as int
        :param card_select: 0 all cards
                            1 voltage float of card 1
                            2 voltage float of card 2 ...
        :return: True if successful
        """
        AL = self._create_param_list_string('1', '0', card_select, False)
        cmd = 'PWR_CFG_VoltageMode' + str(source_number)
        res = self._query(cmd, AL)
        res = self._parse_answer(res, 2, 'andbool', 1)
        return res

    def pwr_set_supply_onoff(self, source_number, onoff, card_select):
        """
        switches supply on or off

        :param source_number: 1...4 as int
        :param onoff: 1 = on 0= off as int
        :param card_select: 0 all cards,
                            1 voltage float of card1,
                            2 voltage float of card2 ...
        :return: True if successful
        """
        AL = self._create_param_list_string('1', '0', card_select, False)
        if onoff == 1:
            cmd = 'PWR_On'
        else:
            cmd = 'PWR_Off'
        cmd += str(source_number)
        res = self._query(cmd, AL)
        res = self._parse_answer(res, 2, 'andbool', 1)
        return res

    def pwr_set_supply_current_limit_max(self, source_number, current_mA, card_select):
        """
        sets supply current limit maximum

        :param source_number: 1...4 as int
        :param current_mA: current in mA (max 50.0) as float
        :param card_select: 0 all cards
                            1 voltage float of card 1
                            2 voltage float of card 2 ...
        :return: True if successful
        """
        # PWR_CFG_IMax1..4
        FL = self._create_param_list_string(current_mA, '', card_select, False)
        cmd = 'PWR_CFG_IMax' + str(source_number)
        res = self._query(cmd, FL)
        res = self._parse_answer(res, 2, 'andbool', 1)
        return res

    def pwr_set_supply_current_limit_min(self, source_number, current_mA, card_select):
        """
        sets supply current limit (sink) minimum

        :param source_number: 1...4 as int
        :param current_mA: negative current in mA (max -50.0) as float
        :param card_select: 0 all cards,
                          1 voltage float of card1,
                          2 voltage float of card2 ...
        :return: True if successful
        """
        # PWR_CFG_IMax1..4
        FL = self._create_param_list_string(current_mA, '', card_select, False)
        cmd = 'PWR_CFG_IMin' + str(source_number)
        res = self._query(cmd, FL)
        res = self._parse_answer(res, 2, 'andbool', 1)
        return res

    def pwr_config_voltage_source(self, source_number, card_select, voltage, i_min, i_max, use_sense):
        """
        configures a power source / sink

        :param source_number: 1...4 as int
        :param card_select: 0 all cards,
                          1 voltage float of card1,
                          2 voltage float of card2 ...
        :return: True if successful
        :param voltage: voltage as float
        :param i_min: minimum current in mA (max -50.0) as float
        :param i_max: maximum current in mA (max 50.0) as float
        :param use_sense: Sense Force On/Off as bool
        :return: True if successful
        """
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        # set Sense Force On/Off
        cmd = 'PWR_CFG_Sense_Force_'
        if use_sense:
            cmd += 'On'
        else:
            cmd += 'Off'
        cmd += str(source_number)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        if not res:
            return False
        # set voltage mode
        cmd = 'PWR_CFG_VoltageMode' + str(source_number)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, 'andbool', 1)
        if not res:
            return False
        # set I min in mA
        cmd = 'PWR_CFG_IMin' + str(source_number)
        f_list = self._create_param_list_string(str(i_min), '', card_select, False)
        res = self._query(cmd, f_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        if not res:
            return False
        # set I max in mA
        cmd = 'PWR_CFG_IMax' + str(source_number)
        f_list = self._create_param_list_string(str(i_max), '', card_select, False)
        res = self._query(cmd, f_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        if not res:
            return False
        # set voltage
        cmd = 'PWR_CFG_SetV' + str(source_number)
        f_list = self._create_param_list_string(str(voltage), '', card_select, False)
        res = self._query(cmd, f_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        if not res:
            return False
        return res

    def pwr_config_current_source(self, source_number, card_select, current, v_min, v_max, use_sense):
        """
        configures a power source / sink

        :param source_number: 1...4 as int
        :param card_select: 0 all cards,
                          1 voltage float of card1,
                          2 voltage float of card2 ...
        :return: True if successful
        :param current: current in mA as float
        :param v_min: minimum voltage in V (max -20.0) as float
        :param i_max: maximum voltage in VA (max 20.0V) as float
        :param use_sense: Sense Force On/Off as bool
        :return: True if successful
        """
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        # set Sense Force On/Off
        cmd = 'PWR_CFG_Sense_Force_'
        if use_sense:
            cmd += 'On'
        else:
            cmd += 'Off'
        cmd += str(source_number)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        if not res:
            return False
        # set voltage mode
        cmd = 'PWR_CFG_CurrentMode' + str(source_number)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, 'andbool', 1)
        if not res:
            return False
        # set V min in Volt
        cmd = 'PWR_CFG_VMin' + str(source_number)
        f_list = self._create_param_list_string(str(v_min), '', card_select, False)
        res = self._query(cmd, f_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        if not res:
            return False
        # set V max in Volt
        cmd = 'PWR_CFG_VMax' + str(source_number)
        f_list = self._create_param_list_string(str(v_max), '', card_select, False)
        res = self._query(cmd, f_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        if not res:
            return False
        # set current
        cmd = 'PWR_CFG_SetI' + str(source_number)
        f_list = self._create_param_list_string(str(current), '', card_select, False)
        res = self._query(cmd, f_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        if not res:
            return False
        return res

    def pwr_get_state(self, source_number, card_select):
        """
        reads state

        :param source_number: 1...4 as int
        :param card_select: 0 all cards,
                          1 voltage float of card1,
                          2 voltage float of card2 ...
        :return: state as int
        """
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        # read state
        cmd = 'PWR_GetState' + str(source_number)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, hex, card_select, 8)
        return res

    def pwr_get_current(self, source_number, card_select):
        """
        reads source current

        :param source_number: 1...4 as int
        :param card_select: 0 all cards,
                          1 voltage float of card1,
                          2 voltage float of card2 ...
        :return: current in mA as float
        """
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        # read state
        cmd = 'MEAS_I_' + str(source_number)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, float, card_select)
        return res

    def pwr_set_onoff(self, source_number, card_select, onoff):
        """
        switches supply on or off

        :param source_number: 1...4 as int
        :param onoff: 1 = on 0= off as int
        :param card_select: 0 all cards,
                            1 voltage float of card1,
                            2 voltage float of card2 ...
        :return: True if successful
        """
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        # set on or off
        cmd = 'PWR_'
        if onoff:
            cmd += 'On'
        else:
            cmd += 'Off'
        cmd += str(source_number)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        if onoff:
            self.pwr_set_closerelais(source_number, card_select)
        else:
            self.pwr_set_openrelais(source_number, card_select)
        return res

    # ************************************************************************
    # SPI Interface 1...4
    # ************************************************************************

    def spi_set_frequency(self, spi_channel, frequency):
        """
        set spi frequency of all cards

        :param spi_channel:  interface number 1...4
        :param frequency:  frequency in HZ (max 1E7)
        :return: True if successfull
        """
        cmd = 'DIG_SPI' + str(spi_channel) + '_CFG_SetFrequency'
        frq = int(frequency)
        res = self._query(cmd, str(frq))
        res = self._parse_answer(res, 2, 'andbool', 1)
        return res

    def spi_set_polarity(self, spi_channel, pol_high, card_select):
        """
        set spi polarity of SPI interface

        :param spi_channel: interface number 1...4
        :param pol_high: pol_high 1= high polarity, 0= low polarity
        :param card_select: 1,2,..16 (single card) or 0 (all cards)
        :return: @return True if successfull else False (List of True/False if card_select = 0)
        """
        cmd = 'DIG_SPI' + str(spi_channel)
        if pol_high:
            cmd += '_CFG_SetCPOLHigh'
        else:
            cmd += '_CFG_SetCPOLLow'
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def spi_set_enable(self, spi_channel, enable, card_select):
        """
        enable/disable of SPI interface

        :param spi_channel: interface number 1...4
        :param enable: 1=enable 0=disable
        :param card_select: 1,2,..16 (single card) or 0 (all cards)
        :return: True if successfull else False (List of True/False if card_select = 0)
        """
        cmd = 'DIG_SPI' + str(spi_channel)
        if enable:
            cmd += '_Enable'
        else:
            cmd += '_Disable'
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def spi_set_framelen(self, spi_channel, framelen_in_bytes, card_select):
        """
        set spi framelen in byte of SPI interface

        :param spi_channel: interface number 1...4
        :param framelen_in_bytes: framelen in byte as int
        :param card_select: 1,2,..16 (single card) or 0 (all cards)
        :return: True if successfull else False (List of True/False if card_select = 0)
        """
        frame_bits = framelen_in_bytes * 8
        cmd = 'DIG_SPI' + str(spi_channel) + '_CFG_SetFrameLength'
        # create HL as int ',,1c,,,,...'
        hex_list = self._create_param_list_string(frame_bits, '', card_select, True)
        res = self._query(cmd, hex_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def spi_get_framelen(self, spi_channel, card_select):
        """
        reads spi frame len in byte of SPI interface

        :param spi_channel: interface number 1...4
        :param card_select: card_select:1,2,..16 (single card) or 0 (all cards)
        :return: framelen in bit as int (List of int if card_select = 0)
        """
        cmd = 'DIG_SPI' + str(spi_channel) + '_CFG_GetFrameLength'
        # create AL as int ',,1,,,,...'
        ad_list = self._create_param_list_string('1', '0', card_select, False)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, int, card_select)
        return res

    def spi_write_frame(self, spi_channel, data_list, card_select=0):
        """
        writes n bytes to SPI interface MOSI, reads back MISO
        :param spi_channel: interface number 1...4
        :param data_list: list of bytes to write
        :param card_select: card_select:1,2,..16 (single card) or 0 (all cards)
        :return: list of bytes (readback) (List of list if card_select = 0)
        """
        success = True
        res = []
        cmd = 'DIG_SPI' + str(spi_channel) + '_WriteFrame1'
        success &= self.spi_set_framelen(spi_channel, len(data_list), card_select)
        if success:
            str_var = self._list_to_hex_string(data_list)
            # create hex list
            hex_list = self._create_param_list_string(str_var, '', card_select, False)
            res = self._query(cmd, hex_list)
            res = self._parse_answer(res, 2, hex, card_select, 2)
        return res

    # ************************************************************************
    # SYS I2C Interface
    # ************************************************************************

    def i2c_set_master_address(self, i2c_address, card_select=0, channel_select=0):
        """
        sets i2c address af all cards

        :param i2c_address: (use 0x54 for hex or 84 for int) 1...127
        (f.e. if first i2c byte is address+R/W: A6A5A4A3A2A1A0RW, param is  0A6A5A4A3A2A1A0
        :param card_select: card_select:1,2,..16 (single card) or 0 (all cards)
        :param channel_select: 0=I2C_SYS, 1..4=I2C on MIO
        :return: True = success, False= Error
        """
        if (i2c_address == 0) or (i2c_address > 127):
            print('I2C address out of range 0x01 .. 0x7F')
            return False
        # create HL as hex ',,0c,,,,...'
        hex_list = self._create_param_list_string(i2c_address, '', card_select, True)
        if channel_select == 0:
            cmd = 'SYS_I2CExt_CFG_SetMasterAdr'
        else:
            cmd = 'DIG_I2C' + str(channel_select) + '_CFG_SetMasterAdr'
        res = self._query(cmd, hex_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def i2c_get_master_address(self, card_select=0, channel_select=0):
        """
        reads i2c address of all cards (card_select=0)
        or single card (card_select=1..n)

        :param card_select:1,2,..16 (single card) or 0 (all cards)
        :param channel_select: 0=I2C_SYS, 1..4=I2C on MIO
        :return: list of i2c addresses as int (hex-> int)
        """
        ad_list = self._create_param_list_string(1, 0, 0, False)  # read all cards
        if channel_select == 0:
            cmd = 'SYS_I2CExt_CFG_GetMasterAdr'
        else:
            cmd = 'DIG_I2C' + str(channel_select) + '_CFG_GetMasterAdr'
        res = self._query(cmd, ad_list)
        # return 4 byte list, address could only be 1 to 127 ignore first bytes
        res = self._parse_answer(res, 2, hex, card_select, 0)
        return res

    def i2c_set_write_framelen(self, framelen_in_bytes, card_select=0, channel_select=0):
        """
        sets i2c write frame length in Byte for all cards (card_select=0)
        or single card (card_select=1..n)

        :param framelen_in_bytes: write length in byte
        :param card_select: 1,2,..16 (single card) or 0 (all cards)
        :param channel_select: 0=I2C_SYS, 1..4=I2C on MIO
        :return: True if success, False = at least one error
        """
        hex_list = self._create_param_list_string(framelen_in_bytes, '', card_select, True)
        if channel_select == 0:
            cmd = 'SYS_I2CExt_CFG_SetWriteFrameLength'
        else:
            cmd = 'DIG_I2C' + str(channel_select) + '_CFG_SetWriteFrameLength'
        res = self._query(cmd, hex_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def i2c_get_write_framelen(self, card_select=0, channel_select=0):
        """
        reads i2c write frame length in Byte for all cards (card_select=0)
        or single card (card_select=1..n)

        :param card_select:  1,2,..16 (single card) or 0 (all cards)
        :param channel_select: 0=I2C_SYS, 1..4=I2C on MIO
        :return: int list of write length in byte (list len depends on card select and nr of cards)
        """
        ad_list = self._create_param_list_string(1, 0, 0, False)  # read all cards
        if channel_select == 0:
            cmd = 'SYS_I2CExt_CFG_GetWriteFrameLength'
        else:
            cmd = 'DIG_I2C' + str(channel_select) + '_CFG_GetWriteFrameLength'
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, hex, card_select, 0)
        return res

    def i2c_set_read_framelen(self, framelen_in_bytes, card_select=0, channel_select=0):
        """
        sets i2c read frame length in Byte for all cards (card_select=0)
        or single card (card_select=1..n)

        :param framelen_in_bytes: read len in bytes
        :param card_select:  1,2,..16 (single card) or 0 (all cards)
         :param channel_select: 0=I2C_SYS, 1..4=I2C on MIO
        :return: True if success, False = at least one error
        """
        # create HL as int ',,1c,,,,...'
        hex_list = self._create_param_list_string(framelen_in_bytes, '', card_select, True)
        if channel_select == 0:
            cmd = 'SYS_I2CExt_CFG_SetReadFrameLength'
        else:
            cmd = 'DIG_I2C' + str(channel_select) + '_CFG_SetReadFrameLength'
        res = self._query(cmd, hex_list)
        res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def i2c_get_read_framelen(self, card_select=0, channel_select=0):
        """
        reads i2c read frame length in Byte for all cards (card_select=0)
        or single card (card_select=1..n)

        :param card_select: card_select: 1,2,..16 (single card) or 0 (all cards)
         :param channel_select: 0=I2C_SYS, 1..4=I2C on MIO
        :return: int list of read length in byte (list len depends on card select and nr of cards)
        """
        ad_list = self._create_param_list_string(1, 0, 0, False)  # read all cards
        if channel_select == 0:
            cmd = 'SYS_I2CExt_CFG_GetReadFrameLength'
        else:
            cmd = 'DIG_I2C' + str(channel_select) + '_CFG_GetReadFrameLength'
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, hex, card_select, 0)
        return res

    @staticmethod
    def _list_to_hex_string(data_byte_list):
        """
        helper function create 4 digit hex string from list of bytes

        :param data_byte_list: list of byte data
        :return: hex string
        """
        str_var = ''
        for elem in data_byte_list:
            if type(elem) == str:
                elem = ord(elem)
            str_var += format(elem, '#04x')[2:]
        return str_var

    def i2c_write_frame(self, i2c_address, data_list, card_select=0, channel_select=0):
        """
        writes a raw frame to SYS_I2C to all cards (card_select=0) or single card (card_select=1..n)

        :param i2c_address: i2c_address 1...127 as int
        :param data_list: list of bytes to write
        :param card_select: 1,2,..16 (single card) or 0 (all cards)
         :param channel_select: 0=I2C_SYS, 1..4=I2C on MIO
        :return: True if success (Acknowleged by I2C device) list of bool if card_select=0
        """
        res = False
        success = True
        success &= self.i2c_set_master_address(i2c_address, card_select, channel_select)
        success &= self.i2c_set_write_framelen(len(data_list), card_select, channel_select)
        if success:
            str_var = self._list_to_hex_string(data_list)
            # create hexlist
            hex_list = self._create_param_list_string(str_var, '', card_select, False)
            if channel_select == 0:
                cmd = 'SYS_I2CExt_Write'
            else:
                cmd = 'DIG_I2C' + str(channel_select) + '_Write'
            res = self._query(cmd, hex_list)
            res = self._parse_answer(res, 2, 'andbool', card_select)
        return res

    def i2c_read_frame(self, i2c_address, read_framelen, card_select=0, channel_select=0):
        """
        reads raw frame SYS_I2C from all cards (card_select=0) or single card (card_select=1..n)

        :param i2c_address: i2c_address 1...127 as int
        :param read_framelen: nr of bytes to read as int
        :param card_select: 1,2,..16 (single card) or 0 (all cards)
        :param channel_select: 0=I2C_SYS, 1..4=I2C on MIO
        :return: list of read bytes (list of list if card_select=0), '' if no ACK
        """
        success = True
        success &= self.i2c_set_master_address(i2c_address, card_select, channel_select)
        success &= self.i2c_set_read_framelen(read_framelen, card_select, channel_select)
        # create address list
        ad_list = self._create_param_list_string(1, 0, card_select, False)
        if channel_select == 0:
            cmd = 'SYS_I2CExt_Read'
        else:
            cmd = 'DIG_I2C' + str(channel_select) + '_Read'
        timeout = self.bsi_socket.gettimeout()
        if read_framelen > 4096:
            self.bsi_socket.settimeout(30)
        res = self._query(cmd, ad_list)
        res = self._parse_answer(res, 2, hex, card_select)
        if read_framelen > 4096:
            self.bsi_socket.settimeout(timeout)
        return res

    def i2c_write_read_frame(self, i2cadr, write_data_list, read_framelen, card_select=0, channel_select=0):
        """
        sends a raw frame and reads raw frame SYS_I2C (f.e memory: write address, read data)

        :param i2cadr: i2c_address 1...127 as int
        :param write_data_list: list of bytes to send
        :param read_framelen: nr of bytes to read as int
        :param card_select: 1,2,..16 (single card) or 0 (all cards)
        :param channel_select: 0=I2C_SYS, 1..4=I2C on MIO
        :return: list read bytes (list of list if card_select=0), '' if no ACK
        """
        success = True
        hex_str = self._list_to_hex_string(write_data_list)
        success &= self.i2c_set_master_address(i2cadr, card_select, channel_select)
        success &= self.i2c_set_read_framelen(read_framelen, card_select, channel_select)
        success &= self.i2c_set_write_framelen(len(write_data_list), card_select, channel_select)
        # create hex list
        hex_list = self._create_param_list_string(hex_str, '', card_select, False)
        if channel_select == 0:
            cmd = 'SYS_I2CExt_WriteRead'
        else:
            cmd = 'DIG_I2C' + str(channel_select) + '_WriteRead'
        timeout = self.bsi_socket.gettimeout()
        if read_framelen > 4096:
            self.bsi_socket.settimeout(30)
        res = self._query(cmd, hex_list)
        res = self._parse_answer(res, 2, hex, card_select)
        if read_framelen > 4096:
            self.bsi_socket.settimeout(timeout)
        return res

    def i2c_address_search(self, card_select, start_address=1, end_address=127, data=[0], channel_select=0):
        """
        reads raw frame SYS_I2C from all cards (card_select=0) or single card (card_select=1..n)
        if no answer writes a frame with data

        :param card_select: 1,2,..16 (single card) or 0 (all cards)
        :param start_address: i2c start address for search
        :param end_address: i2c end address for search
        :param data: (optional) data bytes to send (f.e. memory needs address byte(s))
        :param channel_select: 0=I2C_SYS, 1..4=I2C on MIO
        :return: list of acknowlegded i2c addresses (list of list if card_select=0)
        , empty list if no ACK
        """
        if card_select > 0:
            found = list()
        else:
            found = [[] for x in range(self.bsi_nr_cards)]
        if channel_select == 0:
            cmd = 'SYS_I2CExt_'
        else:
            cmd = 'DIG_I2C' + str(channel_select) + '_'
        ad_list = self._create_param_list_string(1, 0, card_select, False)  # read all cards
        self.i2c_set_read_framelen(1, 0, channel_select)
        self.i2c_set_write_framelen(len(data), 0, channel_select)
        for i2c_adr in range(start_address, end_address + 1):
            self.i2c_set_master_address(i2c_adr, 0, channel_select)
            if card_select > 0:  # single card

                res = self._query(cmd + 'Read', ad_list)
                res = self._parse_answer(res, 2, hex, card_select)
                if res != '':
                    found.append(i2c_adr)
                else:
                    # read did not answer, try write
                    str_var = self._list_to_hex_string(data)
                    # create hex list
                    hex_list = self._create_param_list_string(str_var, '', card_select, False)
                    res = self._query(cmd + 'Write', hex_list)
                    res = self._parse_answer(res, 2, 'andbool', card_select)
                    if res:
                        found.append(i2c_adr)
            else:  # for each card
                for ind in range(self.bsi_nr_cards):
                    # test all cards
                    res = self._query(cmd + 'Read', ad_list)
                    res = self._parse_answer(res, 2, hex, ind + 1)
                    if res != '':
                        found[ind].append(i2c_adr)
                    else:
                        # read did not answer, try write
                        str_var = self._list_to_hex_string(data)
                        # create hex list
                        hex_list = self._create_param_list_string(str_var, '', ind + 1, False)
                        res = self._query(cmd + 'Write', hex_list)
                        res = self._parse_answer(res, 2, 'andbool', ind + 1)
                        if res:
                            found[ind].append(i2c_adr)
        return found

    # ************************************************************************
    # CALIBRATION
    # ************************************************************************

    def bsi_start_self_calibration(self, timeout=20.0):
        """
        starts Calibration of all cards (Ref and Offset)
        :param timeout: (optional) timeout in sec before answer is expected (default 20sec)
        :return: list of list float li[0]=list Offset values
         li[1]= list Ref values for each card
        """
        old_timeout = self.get_timeout()
        self.set_timeout(timeout)
        return_list = []
        cmd = 'CAL_ADCOffset'
        res = self._query(cmd)
        res = self._parse_answer(res, 2, float)
        return_list.append(res)
        cmd = 'CAL_ADCRef'
        res = self._query(cmd)
        res = self._parse_answer(res, 2, float)
        return_list.append(res)
        self.set_timeout(old_timeout)
        return return_list  # li[0]=Offset values li[1]=Ref values

    def bsi_set_calibration_params(self, first_wait_ms, wait_ms, nr_samples):
        """
        sets parameters for calibration

        :param first_wait_ms: wait before first measure in ms
        :param wait_ms: wait between measures in ms
        :param nr_samples: nr of samples for averaging
        :return: True if successfull else False TODO
        """
        param_str = str(first_wait_ms) + ',' + str(wait_ms) + ',' + str(nr_samples)
        cmd = 'LLV_SET_CALI_Parameter'
        res = self._query(cmd, param_str)
        res = self._parse_answer(res, 2, bool, 1)
        return res

    def bsi_set_default_calibration_params(self):
        """
        set BSI calibration parameter to default

        :return: True if successfull else False TODO
        """
        cmd = 'LLV_RESET_CALI_Parameter'
        res = self._query(cmd)
        res = self._parse_answer(res, 2, bool, 1)
        return res


# end of class BSI_Instrument


class BsiI2c(I2cInterface):
    """
    Class for BSI I2c use as I2cInterface class
    * I2C communication (one Channel per card)
    channels: 0=SYS I2C, 1...4 MIO I2C
    """

    def __init__(self, bsi, card_select, channel_select):
        """
        constructor
        :param card_select: 1,2,..16 (single card) or 0 (all cards) as int
        :param channel_select: 0=SYS I2C, 1...4 MIO I2C as int
        """
        self._bsi = bsi
        self._card = card_select
        self._channel = channel_select

    def write(self, i2c_addr: int, data: bytearray) -> Union[bool, None]:
        return self._bsi.i2c_write_frame(i2c_addr, list(data), self._card, self._channel)

    def read(self, i2c_addr: int, read_len: int) -> Union[bytearray, None]:
        dat = self._bsi.i2c_read_frame(i2c_addr, read_len, self._card, self._channel)
        if dat != '':
            if type(dat) is list:
                return bytearray(dat)
            if type(dat) is int:
                return dat.to_bytes(read_len, 'big')
        else:
            return None

    def write_read(self, i2c_addr: int, data: bytearray, read_len: int) -> Union[bytearray, None]:
        dat = self._bsi.i2c_write_read_frame(i2c_addr, list(data), read_len, self._card, self._channel)
        if dat != '':
            if type(dat) is list:
                return bytearray(dat)
            if type(dat) is int:
                return dat.to_bytes(read_len, 'big')
        else:
            return None


# end of class BsiI2C


def bsi_open_by_ini(ini_filepath, ini_section):
    """
    opens BSI instrument with settings defined by ini_parser ini_section
    example:
    [BSI]
    ip=192.168.1.77
    port=21
    :param ini_filepath: file path of ini_parser file as string
    :param ini_section: ini_section name as string
    :return: instance of BSI, else None (if not connected)
    """
    parser = configparser.ConfigParser(allow_no_value=True, delimiters='=')
    parser.optionxform = str
    parser.read(ini_filepath)
    if parser.has_option(ini_section, 'ip'):
        ip_adr = parser.get(ini_section, 'ip')
    else:
        print('ERROR: Ini file has no section [ip], BSI IP not defined')
        return None
    port = 21
    if parser.has_option(ini_section, 'port'):
        port = int(parser.get(ini_section, 'port'))
    bsi = BsiInstrument()
    success = bsi.open_bsi(ip_adr, port)  # use default port 17501
    if success:
        return bsi
    return None


def bsi_meas_by_ini(bsi_instrument, ini_filepath, ini_section, stopmeas_on_first_error=False,
                    do_calc_deviation=False, ):
    """
    measurement of voltage with settings defined by ini_parser ini_section
    example
    [xyz]
    name ,BSI_U (voltage), HighPin, LowPin, card_select,
    voltage factor, expected value, min value, max val
    abc,BSI_U,MIO02,Low1_Sense,1,1.0,5.0,4.5,5.5   #BSI_U

    You can use commands inside measurement for example for open/close relais(keystring = 'BSI_CMD':
    CMD1,BSI_CMD,PWR_CFG_RelClose1,1
    5PD,BSI_UR,0,MEAS_V_MIO01_Low1_Sense,1,1.0,5,4.8,5.2
    ...
    CMD2,BSI_CMD,PWR_CFG_RelOpen1,1

    WARNING: first elements (== keys) must be different, so names of measurements inside a section
    must not be equal, if you use commands use CMD1,CMD2.... as first element

    :param bsi_instrument: BSI instrument array class instance
    :param ini_filepath: file path of ini_parser file as string
    :param ini_section: ini_section name as string
    :param stopmeas_on_first_error: (if true, measurement will stop measure at first error or out of range
                         but executes cmmands until end of list)
    :return: List of measurement list (first list element is True or False (all measures in range?)
    """
    return_list = []
    meas_list = []
    try:
        # if(bsi_instrument==None):
        #     print('ERROR: No BSI instrument')
        #     return [False]
        # read measures from ini_parser file
        parser = configparser.ConfigParser(allow_no_value=True, delimiters='=')
        parser.optionxform = str
        parser.read(ini_filepath)
        opt_list = parser.options(ini_section)
        measure_in_range = True  # defalut
        local_do_measure = True
        for measure in opt_list:
            # check comments
            found = measure.find('#')
            if found != -1:
                measure = measure[0:found]
            # string to list
            measure = measure.split(',')
            # calculate measure settings
            name = measure[0]
            meas_list = [name]  # list for measurement result (return is list of list)
            typ = measure[1]
            if 'BSI_CMD' in typ:
                cmd = measure[2]
                card = int(measure[3])
                bsi_instrument.send_cmd_parse_answer(cmd, card)
                time.sleep(0.05)
            elif local_do_measure:
                local_out_of_range = False
                nr_param = int(measure[2])
                cmd = measure[3]
                param_str = ''
                j = 4
                if nr_param > 0:
                    for found in range(nr_param):
                        param_str += str(measure[j]) + ','
                    param_str = param_str[:-1]
                j += nr_param
                card = int(measure[j])
                factor = float(measure[j + 1])
                expected = float(measure[j + 2])
                min_value = float(measure[j + 3])
                max_value = float(measure[j + 4])
                meas_list.append(min_value)
                meas_list.append(max_value)
                dimension_str = '?'
                val = None
                if (measure[1] == 'BSI_UR') or (measure[1] == 'BSI_URA'):  # measure voltage with range
                    # measure voltage
                    if measure[1] == 'BSI_URA':
                        dimension_str = 'A'  # dimension is Ampere
                    else:
                        dimension_str = 'V'  # dimension is Volt
                    if bsi_instrument is not None:
                        val = bsi_instrument.get_voltage_autorange_by_cmd(cmd, param_str, card)
                        val = round(val, 4)
                if val is None:
                    # no return from BSI
                    print(name + ': ' + '---' + str(dimension_str)
                          + ' (' + str(min_value) + str(dimension_str)
                          + '...' + str(max_value) + str(dimension_str) + ') NO MEASURE')
                    meas_list.insert(1, 'NO MEASURE')
                    measure_in_range = False
                else:
                    val = val * factor
                    val = round(val, 4)
                    meas_list.insert(1, val)  # insert result to measuring list
                    print(name + ':   ' + str(val) + str(dimension_str) + '  ('
                          + str(min_value) + str(dimension_str) + '...'
                          + str(max_value) + str(dimension_str) + ')   ', end='')
                    if do_calc_deviation:
                        if expected == 0.0:
                            dev_percent = 'not calculatable'
                            print('(Dev. ' + str(expected) + str(dimension_str) + ' ' + 'not calculatable)    ', end='')
                        else:
                            dev_percent = (abs(val - expected)) / expected
                            dev_percent = dev_percent * 100.0
                            dev_percent = round(dev_percent, 4)
                            if val < expected:
                                dev_percent = -dev_percent
                            print('(Dev. ' + str(expected) + str(dimension_str) + ': ' + str(dev_percent) + '%)    ',
                                  end='')
                    # check for range violation
                    if (val < min_value) or (val > max_value):
                        print('OUT OF RANGE')
                        local_out_of_range = True
                        measure_in_range = False
                    else:
                        local_out_of_range = False
                        print('OK')
                if local_out_of_range:  # =m   easure_in_range:
                    meas_list.append('OUT OF RANGE')
                else:
                    meas_list.append('OK')
                meas_list.append(dimension_str)
                meas_list.append(typ)
                if do_calc_deviation:
                    meas_list.append(expected)
                    meas_list.append(dev_percent)
                # append measure list to return list
                return_list.append(meas_list)
                if local_out_of_range:
                    # check for stop measurement after first error (out of range)
                    if stopmeas_on_first_error:
                        # do not return directly in case of commands, stop measure only
                        local_do_measure = False
        # all measures done
        # first element of return list is True or False (all measures in range?)
        return_list.insert(0, measure_in_range)
        return return_list
    except Exception as ex:
        meas_list.append(str(ex))
        return_list.append(meas_list)
        return_list.insert(0, False)
        print('Measure BSI by ini_parser:' + str(ex))
        return return_list


if __name__ == "__main__":
    import sys
    import inspect
    import pathlib

    # print module info
    print(pathlib.Path(__file__).name + ' is Library normally!')
    # print classes
    classes = inspect.getmembers(sys.modules[__name__], predicate=inspect.isclass)
    if len(classes) > 0:
        print('Classes:')
        for class_found in classes:
            print('   ' + str(class_found[0]))
            obj = class_found[1]
            members = inspect.getmembers(obj)
            # predicate=inspect.isfunction(obj)
            for member_found in members:
                S = str(member_found[0])
                S1 = str(member_found[1])
                if S1[0:5] == '<func':
                    if S[1] != '_':
                        print('       ' + str(member_found[0]))
        print()
    # print functions
    func = inspect.getmembers(sys.modules[__name__], predicate=inspect.isfunction)
    if len(func) > 0:
        print('Functions:')
        for class_found in func:
            print('   ' + str(class_found[0]))
        print()
    # example of use
    print('Example')
    bsi_instrument = BsiInstrument()
    ok = bsi_instrument.open_bsi("192.168.1.77")  # use default port 21
    if ok:
        ok = bsi_instrument.set_meas_range(1)
        vpos = bsi_instrument.get_voltage('MIO01', 'MIO02', 0)
        vneg = bsi_instrument.get_voltage('MIO02', 'MIO01', 0)
        print('All cards voltage: ' + str(vpos) + '' + str(vneg))
        dat = bsi_instrument.i2c_address_search(0)
        print('Found I2C devices: ' + str(dat))
    sys.exit()
