from machine import Pin, SPI
from time import sleep
import utime

DEBUG = False
DEBUG_LEVEL = 4

SLEEP_TIME = 0.002

BAUDRATE = 4000000

def log(string, level=1):
    if DEBUG:
        if DEBUG_LEVEL >= level:
            print(string)

# PN5180 Stuff - Fold to keep out the way!

# PN5180 Registers
class Regs:
    _SYSTEM_CONFIG = 0x00
    _IRQ_ENABLE = 0x01
    _IRQ_STATUS = 0x02
    _IRQ_CLEAR = 0x03
    # _TRANSCEIVE_CONTROL = 0x04
    # _TIMER1_RELOAD      = 0x0c
    # _TIMER1_CONFIG      = 0x0f
    # _RX_WAIT_CONFIG     = 0x11
    _CRC_RX_CONFIG = 0x12
    _RX_STATUS = 0x13
    # _TX_WAIT_CONFIG     = 0x17
    # _TX_CONFIG          = 0x18
    _CRC_TX_CONFIG = 0x19
    _RF_STATUS = 0x1d
    # _SYSTEM_STATUS      = 0x24
    # _TEMP_CONTRO        = 0x25
    # _AGC_REF_CONFIG     = 0x26Transceiver not in state WaitTransmit!?


_PN5180_READ_REGISTER = 0x04  # Reads one 32bit register value
_PN5180_READ_EEPROM = 0x07  # Processes an array of EEPROM addresses from a start address and reads the values from these addresses
_PN5180_LOAD_RF_CONFIG = 0x11  # This instruction is used to update the RF configuration from EEPROM into the configuration registers
_PN5180_RF_ON = 0x16  # This instruction switch on the RF Field
_PN5180_RF_OFF = 0x17  # This instruction switch off the RF Field
_PN5180_WRITE_REGISTER = 0x00  # Write one 32bit register value
_PN5180_WRITE_REGISTER_OR_MASK = 0x01  # Write one 32bit register value using a 32 bit OR mask
_PN5180_WRITE_REGISTER_AND_MASK = 0x02  # Write one 32bit register value using a 32 bit AND mask
_PN5180_SEND_DATA = 0x09  # This instruction is used to write data into the transmission buffer, the START_SEND bit is auto-set.
_PN5180_READ_DATA = 0x0A  # This instruction is used to send data into the transmission buffer, the START_SEND bit is auto-set.

# PN5180 EEPROM Addresses
_DIE_IDENTIFIER = 0x00
_PRODUCT_VERSION = 0x10
_FIRMWARE_VERSION = 0x12
_EEPROM_VERSION = 0x14
_IRQ_PIN_CONFIG = 0x1A

# PN5180 IRQ_STATUS
_RX_IRQ_STAT = 1 << 0  # End of RF rececption IRQ
_TX_IRQ_STAT = 1 << 1  # End of RF transmission IRQ
_IDLE_IRQ_STAT = 1 << 2  # IDLE IRQ
_RFOFF_DET_IRQ_STAT = 1 << 6  # RF Field OFF detection IRQ
_RFON_DET_IRQ_STAT = 1 << 7  # RF Field ON detection IRQ
_TX_RFOFF_IRQ_STAT = 1 << 8  # RF Field OFF in PCD IRQ
_TX_RFON_IRQ_STAT = 1 << 9  # RF Field ON in PCD IRQ
_RX_SOF_DET_IRQ_STAT = 1 << 14  # RF SOF Detection IRQ
_GENERAL_ERROR_IRQ_STAT = 1 << 17  # General error IRQ
_LPCD_IRQ_STAT = 1 << 19  # LPCD Detection IRQ

# PN5180 IRQ_STATUS
IRQ = {
    "_RX_IRQ_STAT": 1 << 0,  # End of RF rececption IRQ
    "_TX_IRQ_STAT": 1 << 1,  # End of RF transmission IRQ
    "_IDLE_IRQ_STAT ": 1 << 2,  # IDLE IRQ
    "MODE_DETECTED_IRQ_STAT ": 1 << 3,
    "CARD_ACTIVATED_IRQ_STAT ": 1 << 4,
    "STATE_CHANGE_IRQ_STAT ": 1 << 5,
    "_RFOFF_DET_IRQ_STAT ": 1 << 6,  # RF Field OFF detection IRQ
    "_RFON_DET_IRQ_STAT": 1 << 7,  # RF Field ON detection IRQ
    "_TX_RFOFF_IRQ_STAT": 1 << 8,  # RF Field OFF in PCD IRQ
    "_TX_RFON_IRQ_STAT": 1 << 9,  # RF Field ON in PCD IRQ
    "_RX_SOF_DET_IRQ_STAT": 1 << 14,  # RF SOF Detection IRQ
    "_GENERAL_ERROR_IRQ_STAT": 1 << 17,  # General error IRQ
    "_LPCD_IRQ_STAT": 1 << 19,  # LPCD Detection IRQ
}

PN5180TransceiveStat = {
    "PN5180_TS_Idle": 0,
    "PN5180_TS_WaitTransmit": 1,
    "PN5180_TS_Transmitting": 2,
    "PN5180_TS_WaitReceive": 3,
    "PN5180_TS_WaitForData": 4,
    "PN5180_TS_Receiving": 5,
    "PN5180_TS_LoopBack": 6,
    "PN5180_TS_RESERVED": 7
}

_PN5180_TS_Idle = 0
_PN5180_TS_WaitTransmit = 1
_PN5180_TS_Transmitting = 2
_PN5180_TS_WaitReceive = 3
_PN5180_TS_WaitForData = 4
_PN5180_TS_Receiving = 5
_PN5180_TS_LoopBack = 6
_PN5180_TS_RESERVED = 7


class NFC:
    def __init__(self, nss_pin, rst_pin, bsy_pin, card_reader_id = None, sck=10, mosi=11, miso=12):


        if type(nss_pin) is int:
           self._nss_pin = Pin(nss_pin, Pin.OUT)
        else:
            self._nss_pin = nss_pin

        if type(rst_pin) is int:
            self._rst_pin = Pin(rst_pin, Pin.OUT)
        else:
            self._rst_pin = rst_pin

        if type(bsy_pin) is int:
            self._bsy_pin = Pin(bsy_pin, Pin.IN, Pin.PULL_UP)
        else:
            self._bsy_pin = bsy_pin

        self._card_reader_id = card_reader_id

        log(f"Initialised NFC:{card_reader_id} with nss={nss_pin}, rst={rst_pin}, bsy={bsy_pin}")

        # start SPI
        self._spi = SPI(0, baudrate=1000000, sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
        log(f"Initialised SPI with sck={sck}, mosi={mosi}, miso={miso}")

        self._timeout = 50  # set timeout to 200 ms

    def begin(self):

        self._nss_pin.on()  # set pin high (we don't want to talk to it)
        self._rst_pin.on()  # set bsy pin high
        log("Initialised nfc", 2)

    def reset(self):
        # cycle rst pin
        self._rst_pin.off()
        sleep(.01)
        self._rst_pin.on()
        sleep(.01)

        # wait to ready
        starting_time = utime.ticks_ms()
        # Ensure that get_irq_status() returns bytes before using int.from_bytes()
        irq_status = self.get_irq_status()
        if not isinstance(irq_status, bytes):
            log("Error: get_irq_status() did not return bytes.", 1)
            return False

        while _IDLE_IRQ_STAT != _IDLE_IRQ_STAT & int.from_bytes(irq_status, 'little'):
            if (utime.ticks_ms() - starting_time) > self._timeout:
                log("Timeout waiting for reset to complete", 1)
                return False

        return True

    def get_irq_status(self):

        irq_status = self.read_register(Regs._IRQ_STATUS)

        return irq_status

    def transceive_command(self, send_buffer, response_length):
        value = None

        # Step 0: wait for bsy to be low
        starting_time = utime.ticks_ms()
        while 0 != self._bsy_pin.value():
            if utime.ticks_ms() - starting_time > self._timeout:
                log("T:0 timeout on waiting for bsy low")
                return False

        # Step 1: turn off nss to communicate
        self._nss_pin.off()
        sleep(.001)  # delay to allow pin to turn off

        # Step 2: send SPI buffer
        self._spi.write(bytearray(send_buffer))

        # Step 3: wait for bsy to be high
        starting_time = utime.ticks_ms()
        while 1 != self._bsy_pin.value():
            if utime.ticks_ms() - starting_time > self._timeout:
                log("T:5 timeout on waiting for bsy high")
                return False

        # Step 4: Turn on nss pin
        self._nss_pin.on()
        #sleep(.001)

        # Step 5: wait for bsy to be low
        starting_time = utime.ticks_ms()
        while 0 != self._bsy_pin.value():
            if utime.ticks_ms() - starting_time > self._timeout:
                log("T:5 timeout on waiting for bsy high")
                return False

        # check if we are expecting a response
        if response_length == 0:
            return True

        # Step 6: Turn off nss pin for communication
        self._nss_pin.off()
        sleep(.001)

        # Step 7: Read SPI buffer
        data = self._spi.read(response_length)

        # Step 8: wait for bsy to be high
        starting_time = utime.ticks_ms()
        while 1 != self._bsy_pin.value():
            if utime.ticks_ms() - starting_time > self._timeout:
                log("T:8 timeout on waiting for bsy high")
                return False

        # Step 9: Turn on nss pin
        self._nss_pin.on()
        #sleep(.001)

        # Step 10: wait for bsy to be low
        starting_time = utime.ticks_ms()
        while 0 != self._bsy_pin.value():
            if utime.ticks_ms() - starting_time > self._timeout:
                log("T:10 timeout on waiting for bsy high")
                return False


        return data

    def read_eeprom(self, address, response_length):
        return self.transceive_command([_PN5180_READ_EEPROM, address, response_length], response_length)

    def get_firmware(self):
        data = self.read_eeprom(_FIRMWARE_VERSION, 2)
        if data:
            return f"{data[0]}.{data[1]}"
        else:
            return "error"

    def get_product_version(self):
        data = self.read_eeprom(_PRODUCT_VERSION, 2)
        if data:
            return f"{data[0]}.{data[1]}"
        else:
            return "error"

    def get_eeprom_version(self):
        data = self.read_eeprom(_EEPROM_VERSION, 2)
        if data:
            return f"{data[0]}.{data[1]}"
        else:
            return "error"

    def write_register(self, reg, value):
        cmd = [_PN5180_WRITE_REGISTER, reg]
        value = list(value.to_bytes(4, 'little'))
        cmd += value  # Give list of bytes
        self.transceive_command(cmd, 0)
        return True

    def clear_irq_status(self, irq_mask):
        return self.write_register(Regs._IRQ_CLEAR, irq_mask)

    def load_radio_configuration(self, tx_config, rx_config):
        self.transceive_command([_PN5180_LOAD_RF_CONFIG, tx_config, rx_config], 0)
        return True

    def log_irq_values(self, selection=None):
        if not selection:
            for key, value in IRQ.items():
                print(f"IRQ - {key} = {value == value & int.from_bytes(self.get_irq_status(), 'little')}")
        else:
            for key, value in IRQ["filter"].items():
                print(f"IRQ - {key} = {value == value & int.from_bytes(self.get_irq_status(), 'little')}")

    def setup_radio(self, protocol="ISO14443"):

        # load correct config
        if protocol == "ISO14443":

            if self.load_radio_configuration(0x00, 0x80):
                log("Radio configuration loaded")
                pass
            else:
                return False

            if self.transceive_command([_PN5180_RF_ON, 0x00], 0):
                pass
            else:
                return False

            sleep(0.01)  # wait for radio to start 10ms reduced to 2

            # check RF IRQ is on
            starting_time = utime.ticks_ms()
            while _TX_RFON_IRQ_STAT != (_TX_RFON_IRQ_STAT & int.from_bytes(self.get_irq_status(), 'little')):
                if utime.ticks_ms() - starting_time > self._timeout:
                    log("timeout on waiting for RF field to turn on")
                    return False

            # clear RF on IRQ
            self.clear_irq_status(_TX_RFON_IRQ_STAT)

        log("Radio turned on")
        return True

    def read_card_serial(self, type = "ISO14443"):
        if type == "ISO14443":
            data = self.mifar_activate_type_A()

            # process valid response and clean up

            self.mifare_halt()
            return data

    def mifar_activate_type_A(self):


        buffer = [0] * 10
        self.reset()
        self.setup_radio()


        # Turn off crypto
        if not self.write_register_with_and_mask(Regs._SYSTEM_CONFIG, 0xFFFFFFBF):
            log("Failed to turn off crypto")
            return False

        # Clear TX CRC
        if not self.write_register_with_and_mask(Regs._CRC_TX_CONFIG, 0xFFFFFFFE):
            log("Failed to turn clear TX CRC")
            return False

        # Clear RX CRC
        if not self.write_register_with_and_mask(Regs._CRC_RX_CONFIG, 0xFFFFFFFE):
            log("Failed to turn clear RX CRC")
            return False


        # Set to IDLE
        if not self.write_register_with_and_mask(Regs._SYSTEM_CONFIG, 0xFFFFFFF8):
            log("Failed to set to IDLE")
            return False

        # Activate transceive routine
        if not self.write_register_with_or_mask(Regs._SYSTEM_CONFIG, 0x00000003):
            log("Failed to set to IDLE")
            return False

        # Check for wait-transmit status
        transceiveState = self.get_transceive_state()
        if _PN5180_TS_WaitTransmit != transceiveState:
            log("*** ERROR: Transceiver not in state WaitTransmit!?")
            return False

        # Send REQA command
        self.transceive_command([_PN5180_SEND_DATA, 0x07, 0x26], 0)


        sleep(0.005)  # wait for RF reception

        # read 2 bytes ATQA into buffer
        buffer[0:1] = list(self.read_data(2))

        # Wait for TS_wait_transmit
        starting_time = utime.ticks_ms()
        while _PN5180_TS_WaitTransmit != self.get_transceive_state():
            if ( utime.ticks_ms() - starting_time) > 0.002:  # timeout waiting for a card 20ms
                log(" *** Error : timeout on waiting transceive state")
                return False

        # clear IRQs
        self.clear_irq_status(0xffffffff)

        # Send anti collision 1, 8 bits in last byte
        log("sending AC 1", 2)
        self.send_data([0x93, 0x20], 4, 0x00)

        sleep(0.005)

        num_bytes = self.rx_bytes_received()
        if num_bytes != 5:
            log("*** Error: read 5 bytes failed", 1)
            return 0

        five_bytes = self.read_data(5)

        self.write_register_with_or_mask(Regs._CRC_RX_CONFIG, 0x01)
        self.write_register_with_or_mask(Regs._CRC_TX_CONFIG, 0x01)

        # send anticollision information
        data = self.send_data([0x93, 0x70] + list(five_bytes), 7, 0x00)

        if not data:
            # we have the whole 4 byte UID - return what we have, ignoring first byte
            return five_bytes[1:]

        # Read 1 byte SAK into buffer
        data = self.read_data(1)
        buffer[2] = int.from_bytes(data, 'little')

        if buffer[2] & 0x04 == 0:  # Have a 4 byte UID
            buffer[3:8] = list(five_bytes)[:4]
            return buffer[3:7]

        else:
            if list(five_bytes)[0] != 0x88:
                log("problem in card reading 0x88 not there")
                return False
            buffer[3:6] = list(five_bytes)[1:]

            # Clear TX CRC
            if not self.write_register_with_and_mask(Regs._CRC_TX_CONFIG, 0xFFFFFFFE):
                log("Failed to turn clear TX CRC")
                return False

            # Clear RX CRC
            if not self.write_register_with_and_mask(Regs._CRC_RX_CONFIG, 0xFFFFFFFE):
                log("Failed to turn clear RX CRC")
                return False

            # Send anti collision 2, 8 bits in last byte
            log("sending AC 2", 2)
            self.send_data([0x95, 0x20], 4, 0x00)

            five_bytes = self.read_data(5)

            buffer[6:9] = list(five_bytes)[:4]

            return buffer[3:10]



    def mifare_halt(self):

        pass

    def write_register_with_and_mask(self, reg, mask):
        cmd = [_PN5180_WRITE_REGISTER_AND_MASK, reg]
        mask = list(mask.to_bytes(4, 'little'))
        cmd += mask  # Give list of bytes
        self.transceive_command(cmd, 0)
        return True

    def write_register_with_or_mask(self, reg, mask):
        cmd = [_PN5180_WRITE_REGISTER_OR_MASK, reg]
        mask = list(mask.to_bytes(4, 'little'))
        cmd += mask  # Give list of bytes
        self.transceive_command(cmd, 0)
        return True

    def get_transceive_state(self):
        status = self.read_register(Regs._RF_STATUS)

        if not isinstance(status, bytes):
            log("Error: status did not return bytes.", 1)
            return False

        state = (int.from_bytes(status, 'little') >> 24) & 0x07
        return state

    def read_register(self, register_to_read):
        log(f"Reading register {register_to_read}", 2)
        response = self.transceive_command([_PN5180_READ_REGISTER, register_to_read], 4)
        if not response:
            log(f"*** Error reading register {register_to_read}")
            return False
        return response

    def read_data(self, length):
        data = self.transceive_command([_PN5180_READ_DATA, 0x00], length)
        return data

    def send_data(self, data, length, valid_bits):

        self.write_register_with_and_mask(Regs._SYSTEM_CONFIG, 0xfffffff8)  # Idle/StopCom Command
        self.write_register_with_or_mask(Regs._SYSTEM_CONFIG, 0x00000003)  # Transceive Command

        # Check for wait-transmit status
        transceiveState = self.get_transceive_state()
        if _PN5180_TS_WaitTransmit != transceiveState:
            log("*** ERROR: Transceiver not in state WaitTransmit!?")
            return False

        data = self.transceive_command([_PN5180_SEND_DATA, valid_bits] + data, 0)
        return data

    def rx_bytes_received(self):
        data = self.read_register(Regs._RX_STATUS)
        len = int.from_bytes(data, 'little') & 0x000001ff
        return len

