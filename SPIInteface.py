# -*- coding: utf-8 -*-
""" @package python_test_library.SPIInterface
 Generic SPI Interface Definition. It's used in BSI and VCU15 code.
"""

import abc
from typing import Union


class SPIBusException(Exception):
    """ Is raised when ever something unexpected happend on the SPI bus """
    #pass


class SPIInterface(abc.ABC):
    """
    An Interface definition for all SPI bus providers.

    It's main purpose is to define a common SPI Interface that may be used by any SPI-Device.
    That way it's possible to implement the SPI-Device behaviour independent from the actually SPI Bus
    implementation. (Over one of the many BSI channels, or a dedicated SPI-Master controller
    or a low level SPI Master driver, ...)

    Each actual implementation of this SPIInterface can describe any specific configuration
    needed for accessing the specific SPI bus,
    but provides always this common interface to higher level SPI Endpoint Device descriptions.    
     
    Example:
    @image html SPI_Concept-Example-1-BSI.png "SPI Application Example"

    Here BSI can generate SPI Interface objects based on a specific test setup description.
    These SPI_Interface objects can then be assigned to various SPI_Endpoint-Devices like EEPROMs.
    Once Done each EEPROM can be accessed from the test bench as independent device.
    The EEPROM-object knows then how it can be access it's actual device through the given
    SPI_Interface, even without knowing what actual Bus device realizes this SPI commands for it.
    """

    @abc.abstractmethod
    def write(self, addr: int, data: bytearray) -> bool:
        """
        Send data to SPI device

        :param int addr: SPI device Address
        :param bytearray data: data to write
        :return: True on success
        :rtype: bool
        """
        #pass

    @abc.abstractmethod
    def read(self, addr: int, readlen: int) -> Union[bytearray, None]:
        """
        Read data from SPI device

        :param int addr: SPI device Address
        :param int readlen: Number of bytes to read
        :return: Read data, None on error
        :rtype: Union[bytearray, None]
        """
        #pass

    @abc.abstractmethod
    def write_read(self, addr: int, data: bytearray, readlen: int) -> Union[bytearray, None]:
        """
        Write data and read answer

        :param int addr: SPI device Address
        :param bytearray data: Data to write
        :param int readlen: Number of bytes to read
        :return: Read data, None on error
        :rtype: Union[bytearray, None]
        """
        #pass
