from time import ticks_ms, sleep
from machine import Pin
import json
from neopixel import NeoPixel
from libs.miNetwork import MINetwork
from libs import webrepl
from libs import pn5180_morse # note - customised to use SPI 0, not 1 like other boards
import random


class card_reader:
    
    def __init__(self, card_index):
        
        # bespoke pins for 3 port board
        busy_pins_numbers = [12, 7, 15]
        rst_pins_numbers =  [11, 6, 14]
        nss_pins_numbers =  [10, 5, 13]
        
        self.nfc = pn5180_morse.NFC(nss_pins_numbers[card_index], rst_pins_numbers[card_index], busy_pins_numbers[card_index], card_reader_id=card_index, sck=26, mosi=27, miso=28)
#self.nfc = pn5180_morse.NFC(nss_pins_numbers[card_index], rst_pins_numbers[card_index], busy_pins_numbers[card_index], card_reader_id=card_index, sck=2, mosi=3, miso=4)
        
        self.nfc.begin()
        self.nfc.reset()
        self.id = card_index
        
        print(f"card : {card_index}")
        print(f"firmware: {self.nfc.get_firmware()}")
        print(f"product version: {self.nfc.get_product_version()}")
        print(f"eeprom version: {self.nfc.get_eeprom_version()}")
        
    def read_card(self):
        
        result = self.nfc.read_card_serial()

        return result
    
    
a = card_reader(2)

while True:
    
    sleep(0.1)
    print(a.read_card())
        