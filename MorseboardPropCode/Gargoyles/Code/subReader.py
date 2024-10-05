from machine import Pin, SPI
from os import uname
from time import ticks_ms
import json
import utime
from time import sleep


class MFRC522:

    OK = 0
    NOTAGERR = 1
    ERR = 2

    REQIDL = 0x26
    REQALL = 0x52
    AUTHENT1A = 0x60
    AUTHENT1B = 0x61

    def __init__(self, sck, mosi, miso, rst, cs, spi_bus):

        self.sck = Pin(sck, Pin.OUT)
        self.mosi = Pin(mosi, Pin.OUT)
        self.miso = Pin(miso)
        self.rst = Pin(rst, Pin.OUT)
        self.cs = Pin(cs, Pin.OUT)
        self.spi_bus = spi_bus

        self.rst.value(0)
        self.cs.value(1)

        board = uname()[0]
        #self._spi = SPI(0, baudrate=1000000, sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
        self.spi = SPI(spi_bus, baudrate=4000000, polarity=0, phase=0, sck=self.sck, mosi=self.mosi, miso=self.miso)

        self.spi.init()

        self.rst.value(1)

        self.init()

    def _wreg(self, reg, val):

        self.cs.value(0)
        self.spi.write(b'%c' % int(0xff & ((reg << 1) & 0x7e)))
        self.spi.write(b'%c' % int(0xff & val))
        self.cs.value(1)

    def _rreg(self, reg):

        self.cs.value(0)
        self.spi.write(b'%c' % int(0xff & (((reg << 1) & 0x7e) | 0x80)))
        val = self.spi.read(1)
        self.cs.value(1)

        return val[0]

    def _sflags(self, reg, mask):
        self._wreg(reg, self._rreg(reg) | mask)

    def _cflags(self, reg, mask):
        self._wreg(reg, self._rreg(reg) & (~mask))

    def _tocard(self, cmd, send):

        recv = []
        bits = irq_en = wait_irq = n = 0
        stat = self.ERR

        if cmd == 0x0E:
            irq_en = 0x12
            wait_irq = 0x10
        elif cmd == 0x0C:
            irq_en = 0x77
            wait_irq = 0x30

        self._wreg(0x02, irq_en | 0x80)
        self._cflags(0x04, 0x80)
        self._sflags(0x0A, 0x80)
        self._wreg(0x01, 0x00)

        for c in send:
            self._wreg(0x09, c)
        self._wreg(0x01, cmd)

        if cmd == 0x0C:
            self._sflags(0x0D, 0x80)

        i = 2000
        while True:
            n = self._rreg(0x04)
            i -= 1
            if ~((i != 0) and ~(n & 0x01) and ~(n & wait_irq)):
                break

        self._cflags(0x0D, 0x80)

        if i:
            if (self._rreg(0x06) & 0x1B) == 0x00:
                stat = self.OK

                if n & irq_en & 0x01:
                    stat = self.NOTAGERR
                elif cmd == 0x0C:
                    n = self._rreg(0x0A)
                    lbits = self._rreg(0x0C) & 0x07
                    if lbits != 0:
                        bits = (n - 1) * 8 + lbits
                    else:
                        bits = n * 8

                    if n == 0:
                        n = 1
                    elif n > 16:
                        n = 16

                    for _ in range(n):
                        recv.append(self._rreg(0x09))
            else:
                stat = self.ERR

        return stat, recv, bits

    def _crc(self, data):

        self._cflags(0x05, 0x04)
        self._sflags(0x0A, 0x80)

        for c in data:
            self._wreg(0x09, c)

        self._wreg(0x01, 0x03)

        i = 0xFF
        while True:
            n = self._rreg(0x05)
            i -= 1
            if not ((i != 0) and not (n & 0x04)):
                break

        return [self._rreg(0x22), self._rreg(0x21)]

    def init(self):

        self.reset()
        self._wreg(0x2A, 0x8D)
        self._wreg(0x2B, 0x3E)
        self._wreg(0x2D, 30)
        self._wreg(0x2C, 0)
        self._wreg(0x15, 0x40)
        self._wreg(0x11, 0x3D)
        self.antenna_on()

    def reset(self):
        self._wreg(0x01, 0x0F)

    def antenna_on(self, on=True):

        if on and ~(self._rreg(0x14) & 0x03):
            self._sflags(0x14, 0x03)
        else:
            self._cflags(0x14, 0x03)

    def request(self, mode):

        self._wreg(0x0D, 0x07)
        (stat, recv, bits) = self._tocard(0x0C, [mode])

        if (stat != self.OK) | (bits != 0x10):
            stat = self.ERR

        return stat, bits

    def anticoll(self):

        ser_chk = 0
        ser = [0x93, 0x20]

        self._wreg(0x0D, 0x00)
        (stat, recv, bits) = self._tocard(0x0C, ser)

        if stat == self.OK:
            if len(recv) == 5:
                for i in range(4):
                    ser_chk = ser_chk ^ recv[i]
                if ser_chk != recv[4]:
                    stat = self.ERR
            else:
                stat = self.ERR

        return stat, recv

    def select_tag(self, ser):

        buf = [0x93, 0x70] + ser[:5]
        buf += self._crc(buf)
        (stat, recv, bits) = self._tocard(0x0C, buf)
        return self.OK if (stat == self.OK) and (bits == 0x18) else self.ERR

    def auth(self, mode, addr, sect, ser):
        return self._tocard(0x0E, [mode, addr] + sect + ser[:4])[0]

    def stop_crypto1(self):
        self._cflags(0x08, 0x08)

    def read(self, addr):

        data = [0x30, addr]
        data += self._crc(data)
        (stat, recv, _) = self._tocard(0x0C, data)
        return recv if stat == self.OK else None

    def write(self, addr, data):

        buf = [0xA0, addr]
        buf += self._crc(buf)
        (stat, recv, bits) = self._tocard(0x0C, buf)

        if not (stat == self.OK) or not (bits == 4) or not ((recv[0] & 0x0F) == 0x0A):
            stat = self.ERR
        else:
            buf = []
            for i in range(16):
                buf.append(data[i])
            buf += self._crc(buf)
            (stat, recv, bits) = self._tocard(0x0C, buf)
            if not (stat == self.OK) or not (bits == 4) or not ((recv[0] & 0x0F) == 0x0A):
                stat = self.ERR

        return stat


# load config
with open("config_rfid.json") as f:
    config = json.load(f)


# A class to hold and manage the configuration
class Configuration:
    def __init__(self, filename):
        self.config = None
        self.filename = filename
        self.load()
        pass

    # Load configuration json from file
    def load(self):
        with open(self.filename) as f:
            self.config = json.load(f)

    # Save configuration json to file
    def save(self):
        settings_json = json.dumps(self.config)
        print('Saving:', settings_json)
        try:
            f = open(self.filename, "w")
            f.write(settings_json)
            f.close()
            return True
        except:
            return False

    # get list of known cards
    def known_cards(self, card_no):
        return self.config[f"known_cards_{card_no}"]

    # add card string to saved cards
    def add_card(self, card_no, card_hex_string):
        self.config[f"known_cards_{card_no}"].append(card_hex_string)
        self.save()

    def wipe_cards(self, card_no):
        self.config[f"known_cards_{card_no}"] = []
        self.save()

    def get_id(self):
        return self.config["id"]

# load the configuration
configuration = Configuration("config_rfid.json")

# pins

present = [None, None]
known = [None, None]
present[0] = Pin(16, Pin.OUT)
known[0] = Pin(18, Pin.OUT)

present[1] = Pin(17, Pin.OUT)
known[1] = Pin(19, Pin.OUT)

learn = Pin(20, Pin.IN, Pin.PULL_DOWN)

# Initialise readers
#def __init__(self, sck, mosi, miso, rst, cs):
rdr = []
rdr.append(MFRC522(2, 3, 0, 28, 1, 0))
rdr.append(MFRC522(10, 11, 8, 27, 9, 1))

LED = Pin(25, Pin.OUT)
        

while True:
    sleep(0.01) # some downtime
    

#   Read Cards
    for reader in rdr:
        
        reader.init()
        (stat, tag_type) = reader.request(reader.REQIDL)

        if stat == reader.OK:

            (stat, raw_uid) = reader.anticoll()

            if stat == reader.OK:
                hex_string = ''.join(hex(i)[2:] for i in raw_uid)
                result = hex_string
                
        else:
            result = None
        
    
        print(f"{reader.spi_bus} - has card {result}")
        print(f"{present[reader.spi_bus].value()}   {known[reader.spi_bus].value()}  ")
        if result:
            present[reader.spi_bus].on()
            
            
            if hex_string in configuration.known_cards(reader.spi_bus):
                print(f"{reader.spi_bus} - known")
                known[reader.spi_bus].on()
                
                
                for i in range(0,reader.spi_bus+2):
                    
                    LED.on()
                    sleep(0.05)
                    LED.off()
                    sleep(0.05)
                    

   
            else:
                known[reader.spi_bus].off()
                for i in range(0,reader.spi_bus+1):
                
                    LED.on()
                    sleep(0.05)
                    LED.off()
                    sleep(0.05)
                                
                # if learn button is gnd, save to the file
                if learn.value() > 0:
                    print(f"{reader.spi_bus} - learning {hex_string}")
                    configuration.wipe_cards(reader.spi_bus)
                    configuration.add_card(reader.spi_bus, hex_string)
                
        else:
            present[reader.spi_bus].off()
            known[reader.spi_bus].off()
            
        
            
            
                
                
                
                
            
            
            
                