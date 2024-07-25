from time import ticks_ms, sleep
from machine import Pin
import json
from neopixel import NeoPixel
from libs.miNetwork import MINetwork
from libs import webrepl
from libs import pn5180_morse # note - customised to use SPI 0, not 1 like other boards
import random



# load config
with open("config.json") as f:
    config = json.load(f)

NETWORK = False


if NETWORK:
    network = MINetwork()


    # load webrepl
    webrepl.start()



    network.connect_to_network()
    network.connect_to_mqtt_broker(config["MQTT_CLIENT"], config["MQTT_SERVER"])
else:
    network = None
     
     
class card_reader:
    
    def __init__(self, card_index):
        
        # bespoke pins for 3 port board
        busy_pins_numbers = [12, 7, 26]
        rst_pins_numbers =  [11, 6, 14]
        nss_pins_numbers =  [10, 5, 13]
        
        self.nfc = pn5180_morse.NFC(nss_pins_numbers[card_index], rst_pins_numbers[card_index], busy_pins_numbers[card_index], card_reader_id=card_index, sck=2, mosi=3, miso=4)
        
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
        

class Puzzle:
    def __init__(self, network, topic):
        self.heartbeat_timer = ticks_ms()
        self.heartbeat_timeout = 10000
        
        self.indicator_timer = ticks_ms()
        self.indicator_timeout = 1000
        self.indicator_led = Pin(25, Pin.OUT)
        
        self.relay_pin = Pin(22, Pin.OUT)
        
        self.network = network
        self.topic = topic
        
        self.cards = [card_reader(0),card_reader(1),card_reader(2)]
        
        self.last_status = None
        
        
    def read_cards(self):
        status = {}
        for card in self.cards:
            try:
                result = card.read_card()
            except:
                result = None
                print("issue reading card")
                sleep(0.01)
            if result and result != 0:
                status[card.id] = result
            else:
                status[card.id] = None
        
        return status
    
    def step(self):

        if NETWORK:

            if ticks_ms() - self.heartbeat_timer > self.heartbeat_timeout:
                network.send_mqtt_json(self.topic, {"heartbeat" : "alive"})
                self.heartbeat_timer = ticks_ms()
            
        if ticks_ms() - self.indicator_timer > self.indicator_timeout:
            self.indicator_led.toggle()
            self.indicator_timer = ticks_ms()
            
        status = self.read_cards()
        if status != self.last_status:
            print(status)
            self.last_status = status
            if NETWORK:
                network.send_mqtt_json(self.topic, {"cards" : status})
                
            
    def process_message(self, topic, raw_message):
        message = raw_message.decode('utf-8')
       
        try:
            message_json = json.loads(message)
        except ValueError:
            print("not valid JSON")
            return

puzzle = Puzzle(network, config["MQTT_TOPIC"])

if NETWORK:
    network.subscribe_to_topic(config["MQTT_TOPIC"], puzzle.process_message)

while True:
    
    sleep(0.1)
    if NETWORK:
        network.check_mqtt_and_reconnect()
        network.check_for_messages()
    
    puzzle.step()
    