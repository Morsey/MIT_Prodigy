from time import ticks_ms, sleep
from machine import Pin, SoftI2C
import json
from neopixel import NeoPixel
from libs.miNetwork import MINetwork
from libs import webrepl
from libs import pn5180_morse
from libs.expander import Expander, ExpanderPin
import random



# load config
with open("config.json") as f:
    config = json.load(f)


network = MINetwork()

    
# load webrepl
webrepl.start()

network.connect_to_network()
network.connect_to_mqtt_broker(config["MQTT_CLIENT"], config["MQTT_SERVER"])





# Setup ic2

SCL_PIN = Pin(9, Pin.PULL_UP)
SDA_PIN = Pin(8, Pin.PULL_UP)
i2c = SoftI2C(scl=SCL_PIN, sda=SDA_PIN)
expander = Expander(i2c)

class card_reader:
    
    def __init__(self, card_index):
        
        # bespoke pins for 3 port board
        busy_pins_numbers = [2, 7, 100, 101, 102]
        rst_pins_numbers =  [3, 6, 14,  112, 111]
        nss_pins_numbers =  [4, 5, 13,  106, 107]
        
        
         # prepare pins for card
        if busy_pins_numbers[card_index] < 100:
            busy_pin = Pin(busy_pins_numbers[card_index], Pin.IN, Pin.PULL_UP)
        else:
            busy_pin = ExpanderPin(expander, busy_pins_numbers[card_index] - 100, Pin.IN, Pin.PULL_UP)

        if rst_pins_numbers[card_index] < 100:
            rst_pin = Pin(rst_pins_numbers[card_index], Pin.OUT)
        else:
            rst_pin = ExpanderPin(expander, rst_pins_numbers[card_index] - 100)

        if nss_pins_numbers[card_index] < 100:
            nss_pin = Pin(nss_pins_numbers[card_index], Pin.OUT)
        else:
            nss_pin = ExpanderPin(expander, nss_pins_numbers[card_index] - 100)
        
        self.nfc = pn5180_morse.NFC(nss_pin, rst_pin, busy_pin, card_reader_id=card_index, sck=10, mosi=11, miso=12)
        
        self.nfc.begin()
        self.nfc.reset()
        self.id = card_index
        
        print(f"card : {card_index}")
        print(f"firmware: {self.nfc.get_firmware()}")
        print(f"product version: {self.nfc.get_product_version()}")
        print(f"eeprom version: {self.nfc.get_eeprom_version()}")
        
    def read_card(self):
        try:
            result = self.nfc.read_card_serial()
        except :
            print(f"issue with {self.id }")
            sleep(0.01)
            return None

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
                
        self.relay_pin = Pin(22, Pin.OUT)
        self.relay_pin.off()
        self.cards = []
        for i in range(0,5):
            self.cards.append(card_reader(i))
        
        self.last_status = None
        
        self.mode = "LEDS"
        self.leds = NeoPixel(Pin(22), 4)
        
        self.led_brightness = 0
        self.led_colours = [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]]
        
        self.update_LEDS()
        
        self.boot_up_indication()
        self.one_pulse = False
        
    def boot_up_indication(self):
        def wheel(pos):
            """Generate rainbow colors across 0-255 positions."""
            if pos < 85:
                return pos * 3, 255 - pos * 3, 0
            elif pos < 170:
                pos -= 85
                return 255 - pos * 3, 0, pos * 3
            else:
                pos -= 170
                return 0, pos * 3, 255 - pos * 3

        for i in range (1):
            for x in range (255):
                for led in range(len(self.leds)):
                    self.leds[led] = wheel(x)
                    self.leds.write()
                    sleep(0.001)

        self.blank_leds()
        
    def blank_leds(self):
        
        for led in range(len(self.leds)):
            self.leds[led] = [0, 0, 0]
        self.leds.write()
        
    def get_brightness(self):
        self.led_brightness += 5
        if self.led_brightness > 255 * 2:
            self.led_brightness = 0
            # reset one pulse
            if self.one_pulse:
                self.one_pulse = False
                self.led_colours = [[0,0,0],[0, 0, 0],[0, 0, 0],[0, 0, 0]]
        if self.led_brightness < 256:
            return self.led_brightness
        if self.led_brightness > 255:
            return 255 - (self.led_brightness - 256)
        
        
    def update_LEDS(self):
        brightness = self.get_brightness()
        for l in range(len(self.leds)):
            r = int(self.led_colours[l][0] * brightness/255)
            g = int(self.led_colours[l][1] * brightness/255)
            b = int(self.led_colours[l][2] * brightness/255)
            self.leds[l] = [r,g,b]
        self.leds.write()    
            
            
    def led_sequence(self, sequence):
        
        def get_brightness(led_brightness):
            led_brightness += 5
            if led_brightness > 255 * 2:
                led_brightness = 0
            if led_brightness < 256:
                return led_brightness
            if led_brightness > 255:
                return 255 - (led_brightness - 256)
            
        for pulse in sequence:
            colour = pulse["colour"]
            led_no = pulse["led_no"]
            speed = pulse["speed"]
            brightness = 0
            led_brightness = brightness
            pulsing = True
            
            while pulsing:
                
                r = int(colour[0] * led_brightness/255)
                g = int(colour[1] * led_brightness/255)
                b = int(colour[2] * led_brightness/255)
                self.leds[led_no] = [r,g,b]
                
                self.leds.write()
    
                brightness+=5
    
                if brightness > 255 * 2:
                    pulsing = False
                if brightness < 256:
                     led_brightness = brightness
                if brightness > 255:
                    led_brightness = 255 - (brightness - 256)
                    
                sleep(speed)
            
            self.leds[led_no] = [0,0,0]
                
                
            
        pass
        
    def read_cards(self):
        status = {}
        for card in self.cards:
            result = card.read_card()
  
            if result and result != 0:
                status[card.id] = result
            else:
                status[card.id] = None
        
        return status
    
    
    
    def step(self):

        if ticks_ms() - self.heartbeat_timer > self.heartbeat_timeout:
            network.send_mqtt_json(self.topic, {"heartbeat" : network.nic.ifconfig()[0]})
            self.heartbeat_timer = ticks_ms()
            
        if ticks_ms() - self.indicator_timer > self.indicator_timeout:
            self.indicator_led.toggle()
            self.indicator_timer = ticks_ms()
            
            
        if self.mode is "RFID":
            status = self.read_cards()
           
            if status != self.last_status:
                 print(status)
                 self.last_status = status
            
                 network.send_mqtt_json(self.topic, {"cards" : status})
                 
        else:
            self.update_LEDS()
        
            
    def send_rfid_status(self):
        status = self.read_cards()
        self.last_status = status

        network.send_mqtt_json(self.topic, {"cards" : status})
            
    def process_message(self, topic, raw_message):
        message = raw_message.decode('utf-8')
       
        try:
            message_json = json.loads(message)
        except ValueError:
            print("not valid JSON")
            return

        if "mode" in message_json:
            self.mode = message_json["mode"]
            
        
        if "led" in message_json:
            print("led change")
            self.led_brightness = 0
            self.led_colour = message_json["led"]["colour"]
            self.one_pulse = message_json["led"]["one_pulse"]
            

        if "led_sequence" in message_json:
            self.led_sequence(message_json["led_sequence"])
            
        if "rfid_status" in message_json:
            self.send_rfid_status()

puzzle = Puzzle(network, config["MQTT_TOPIC"])

network.subscribe_to_topic(config["MQTT_TOPIC"], puzzle.process_message)

while True:
    
    sleep(0.01)
  
    
    try:
        network.check_for_messages()
    except:
        network.check_mqtt_and_reconnect()
    
    puzzle.step()
    