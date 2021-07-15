import time
import datetime
from raspi_io import GPIO, GPIOTimingContentManager
__all__ = ['DS1302']


class DS1302(object):
    REG_SIZE = 7
    RAM_SIZE = 31

    CLK_DELAY = 5e-6
    DT_STR_FMT = '%S %M %H %d %m %u %y'

    WP_REG_READ, WP_REG_WRITE = 0x8f, 0x8e
    CHR_REG_READ, CHR_REG_WRITE = 0x91, 0x90
    REG_BURST_READ, REG_BURST_WRITE = 0xbf, 0xbe
    RAM_BURST_READ, RAW_BURST_WRITE = 0xff, 0xfe

    def __init__(self, raspberry, clk_pin=4, io_pin=17, rst_pin=27, mode=GPIO.BCM, timeout=1, verbose=1):
        """DS1302

        :param raspberry: raspberry address
        :param clk_pin: DS1302 clk pin
        :param io_pin: DS1302 io pin
        :param rst_pin: DS1302 reset pin
        :param mode: raspberry GPIO mode
        """

        # Init raspberry gpio and set mode
        self.gpio = GPIO(raspberry, timeout=timeout, verbose=verbose)
        self.gpio.setmode(mode)

        self._io_pin = io_pin
        self._clk_pin = clk_pin
        self._rst_pin = rst_pin

        # Setup clk and reset pin as output and initial state is low
        self.gpio.setup([self._clk_pin, self._rst_pin], GPIO.OUT, initial=GPIO.LOW)

        # Turn off write protection
        with GPIOTimingContentManager(self.gpio, start=self._start_tx, end=self._end_tx):
            self._write_byte(self.WP_REG_WRITE)
            self._write_byte(0x00)

        # Disable charge
        with GPIOTimingContentManager(self.gpio, start=self._start_tx, end=self._end_tx):
            self._write_byte(self.CHR_REG_WRITE)
            self._write_byte(0x00)

    def __del__(self):
        self.gpio.cleanup([self._io_pin, self._clk_pin, self._rst_pin])

    def _sleep(self):
        time.sleep(self.CLK_DELAY)

    def _start_tx(self, gpio):
        """
        Start of transaction.
        """
        gpio.output(self._clk_pin, GPIO.LOW)
        gpio.output(self._rst_pin, GPIO.HIGH)

    def _end_tx(self, gpio):
        """
        End of transaction.
        """
        gpio.setup(self._io_pin, GPIO.IN)
        gpio.output(self._clk_pin, GPIO.LOW)
        gpio.output(self._rst_pin, GPIO.LOW)

    def _read_byte(self):
        """
        Read a byte from the chip.

        :return: byte value 0 - 0xff
        """
        # Setup io pin as input mode
        self.gpio.setup(self._io_pin, GPIO.IN)

        byte = 0
        for i in range(8):
            # Read data on the falling edge of clk
            self.gpio.output(self._clk_pin, GPIO.HIGH)
            self._sleep()

            self.gpio.output(self._clk_pin, GPIO.LOW)
            self._sleep()

            bit = self.gpio.input(self._io_pin)
            byte |= ((2 ** i) * bit)

        return byte

    def _write_byte(self, byte):
        """
        Write a byte to the chip.

        :param byte: byte value 0 - 0xff
        """

        # Setup io pin as output
        self.gpio.setup(self._io_pin, GPIO.OUT)

        for _ in range(8):
            # Write data on the rising edge of clk
            self.gpio.output(self._clk_pin, GPIO.LOW)
            self._sleep()

            self.gpio.output(self._io_pin, byte & 0x01)

            byte >>= 1
            self.gpio.output(self._clk_pin, GPIO.HIGH)
            self._sleep()

    def read_ram(self):
        """
        Read RAM as bytes

        :return: RAM dumps (bytearray)
        """
        with GPIOTimingContentManager(self.gpio, start=self._start_tx, end=self._end_tx):
            self._write_byte(self.RAM_BURST_READ)

            ram = bytearray()
            for _ in range(self.RAM_SIZE):
                ram.append(self._read_byte())

        return ram

    def write_ram(self, ram):
        """
        Write RAM with bytes

        :param ram: bytes to write
        :type ram: bytearray
        """
        with GPIOTimingContentManager(self.gpio, start=self._start_tx, end=self._end_tx):
            self._write_byte(self.RAW_BURST_WRITE)

            for i in range(min(len(ram), self.RAM_SIZE)):
                self._write_byte(ord(ram[i: i + 1]))

    def read_datetime(self):
        """
        Read current date and time from RTC chip.

        :return: date and time
        :rtype: datetime.datetime
        """
        with GPIOTimingContentManager(self.gpio, start=self._start_tx, end=self._end_tx):
            self._write_byte(self.REG_BURST_READ)

            regs = list()
            for _ in range(self.REG_SIZE):
                regs.append(self._read_byte())

        # Decode bytes to datetime
        return datetime.datetime.strptime(" ".join(["{:x}".format(x) for x in regs]), self.DT_STR_FMT)

    def write_datetime(self, dt):
        """
        Write a python datetime to RTC chip.

        :param dt: datetime to write
        :type dt: datetime.datetime
        """
        # format message
        regs = [int("0x{}".format(i), 16) for i in dt.strftime(self.DT_STR_FMT).split()] + [0] * 2
        with GPIOTimingContentManager(self.gpio, start=self._start_tx, end=self._end_tx):
            self._write_byte(self.REG_BURST_WRITE)
            for byte in regs:
                self._write_byte(byte)