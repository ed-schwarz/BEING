# -*- coding: utf-8 -*-
""" @package python_test_library.I2cInterface
 Generic I2C Interface Definition. It's used in BSI and VCU15 code.
"""

import abc
from typing import Union


class I2cBusException(Exception):
    """ Is raised when ever something unexpected happend on the I2C bus """
    #pass


class I2cInterface(abc.ABC):
    """
    An Interface definition for all I2C bus providers.

    It's main purpose is to define a common I2C Interface that may be used by any I2C-Device.
    That way it's possible to implement the I2C-Device behaviour independent from the actually I2C Bus
    implementation. (Over one of the many BSI channels, or a dedicated I2C-Master controller
    or a low level I2C Master driver, ...)

    Each actual implementation of this I2cInterface can describe any specific configuration
    needed for accessing the specific I2C bus,
    but provides always this common interface to higher level I2C Endpoint Device descriptions.    
     
    Example:
    @image html I2C_Concept-Example-1-BSI.png "I2C Application Example"

    Here BSI can generate I2C Interface objects based on a specific test setup description.
    These I2C_Interface objects can then be assigned to various I2C_Endpoint-Devices like EEPROMs.
    Once Done each EEPROM can be accessed from the test bench as independent device.
    The EEPROM-object knows then how it can be access it's actual device through the given
    I2C_Interface, even without knowing what actual Bus device realizes this I2C commands for it.
    """

    @abc.abstractmethod
    def write(self, addr: int, data: bytearray) -> bool:
        """
        Send data to I2c device

        :param int addr: I2C device Address
        :param bytearray data: data to write
        :return: True on success
        :rtype: bool
        """
        #pass

    @abc.abstractmethod
    def read(self, addr: int, readlen: int) -> Union[bytearray, None]:
        """
        Read data from I2C device

        :param int addr: I2C device Address
        :param int readlen: Number of bytes to read
        :return: Read data, None on error
        :rtype: Union[bytearray, None]
        """
        #pass

    @abc.abstractmethod
    def write_read(self, addr: int, data: bytearray, readlen: int) -> Union[bytearray, None]:
        """
        Write data and read answer

        :param int addr: I2C device Address
        :param bytearray data: Data to write
        :param int readlen: Number of bytes to read
        :return: Read data, None on error
        :rtype: Union[bytearray, None]
        """
        #pass
