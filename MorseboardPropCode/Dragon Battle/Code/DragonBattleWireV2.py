from machine import Pin, SoftI2C, UART
from libs.miNetwork import MINetwork
from libs import webrepl
import json
from time import sleep, ticks_ms
from neopixel import NeoPixel
import sys
import machine

from libs.expander import ExpanderPin, Expander

LED = Pin(25, Pin.OUT)

NETWORK = True

# Set up relay and 5V output
RELAY_PIN = Pin(22, Pin.OUT)
FIVE_VOLT_PIN = Pin(4, Pin.OUT)


RELAY_PIN.off()
FIVE_VOLT_PIN.on()

INDICATOR_LED_PIN = 10

# load config
with open("config.json") as f:
    config = json.load(f)
    


# Setup ic2 and use expander board

SCL_PIN = Pin(9, Pin.PULL_UP)
SDA_PIN = Pin(8, Pin.PULL_UP)
i2c = SoftI2C(scl=SCL_PIN, sda=SDA_PIN)

expander = Expander(i2c)

network = MINetwork()


# load webrepl
webrepl.start()


network.connect_to_network()
network.connect_to_mqtt_broker(config["MQTT_CLIENT"], config["MQTT_SERVER"])


class Puzzle:
    
    class Reader:
        def __init__(self, id, card_present_pin, card_correct_pin):
            self.id = id
            self.card_present_pin = card_present_pin
            self.card_correct_pin = card_correct_pin

        def card_check(self):
            return [self.id, self.card_present_pin.value(), self.card_correct_pin.value()]

    
    
    def __init__(self, network, topic):
        self.heartbeat_timer = ticks_ms()
        self.heartbeat_timeout = 10000
        
        self.indicator_timer = ticks_ms()
        self.indicator_timeout = 1000
        self.indicator_led = Pin(25, Pin.OUT)
        
        self.pong_timer = ticks_ms()
        self.pong_timeout = 5000
        
        self.network = network
        self.topic = topic
        
        self.readers = []
        self.readers.append(self.Reader(1, Pin(2, Pin.IN), Pin(4, Pin.IN)))
        self.readers.append(self.Reader(2, Pin(7, Pin.IN), Pin(5, Pin.IN)))
        self.readers.append(self.Reader(3, ExpanderPin(expander, 0, Pin.IN), Pin(13, Pin.IN)))
        self.readers.append(self.Reader(4, ExpanderPin(expander, 1, Pin.IN), ExpanderPin(expander, 6, Pin.IN)))
        self.readers.append(self.Reader(5, ExpanderPin(expander, 2, Pin.IN), ExpanderPin(expander, 7, Pin.IN)))
        self.readers.append(self.Reader(6, ExpanderPin(expander, 3, Pin.IN), ExpanderPin(expander, 15, Pin.IN)))
        self.readers.append(self.Reader(7, ExpanderPin(expander, 5, Pin.IN), ExpanderPin(expander, 13, Pin.IN)))
        self.readers.append(self.Reader(8, ExpanderPin(expander, 4, Pin.IN), ExpanderPin(expander, 14, Pin.IN)))
        
        
        self.last_status = None

        
 
    def step(self):
        if ticks_ms() - self.heartbeat_timer > self.heartbeat_timeout:
            network.send_mqtt_json(self.topic, {"heartbeat" : "alive"})
            self.heartbeat_timer = ticks_ms()
            
        if ticks_ms() - self.indicator_timer > self.indicator_timeout:
            self.indicator_led.toggle()
            self.indicator_timer = ticks_ms()
            
        if ticks_ms() - self.pong_timer > self.pong_timeout:
            self.network.check_mqtt_and_reconnect()
            self.pong_timer = ticks_ms()
            
        self.send_status()
        
            
    def process_message(self, topic, raw_message):
        message = raw_message.decode('utf-8')
       
        try:
            message_json = json.loads(message)
        except ValueError:
            print("not valid JSON")
            return
    

    def puzzle_json_generator(self, status):
        response = {"status": status}
        if NETWORK:
            communication.mqtt_send_json(response)
        return json.dumps(response)
    
    def send_status(self):
        status_json = {}
        for reader in self.readers:
            status_json[reader.id] = reader.card_check()
        if status_json != self.last_status:
            print(f"Updating status {status_json}")
            self.last_status = status_json
            self.network.send_mqtt_json(self.topic, self.last_status )



puzzle = Puzzle(network, config["MQTT_TOPIC"])
network.subscribe_to_topic(config["MQTT_TOPIC"], puzzle.process_message)

while not network.check_mqtt_and_reconnect():
    print("connecting to MQTT")
    network.subscribe_to_topic(config["MQTT_TOPIC"], puzzle.process_message)
    sleep(0.5)

while True:
    try:
        network.check_for_messages()
    except:
        network.check_mqtt_and_reconnect()
        
    puzzle.step()
    sleep(0.1)
