from time import ticks_ms, sleep
from machine import Pin
import json
from neopixel import NeoPixel
from libs.miNetwork import MINetwork
from libs import webrepl
import random


# load config
with open("config.json") as f:
    config = json.load(f)


network = MINetwork()


# load webrepl
webrepl.start()



network.connect_to_network()
network.connect_to_mqtt_broker(config["MQTT_CLIENT"], config["MQTT_SERVER"])
 

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
        
        
        
    def step(self):
        if ticks_ms() - self.heartbeat_timer > self.heartbeat_timeout:
            network.send_mqtt_json(self.topic, {"heartbeat" : "alive"})
            self.heartbeat_timer = ticks_ms()
            
        if ticks_ms() - self.indicator_timer > self.indicator_timeout:
            self.indicator_led.toggle()
            self.indicator_timer = ticks_ms()
            
      
    def process_message(self, topic, raw_message):
        message = raw_message.decode('utf-8')
       
        try:
            message_json = json.loads(message)
        except ValueError:
            print("not valid JSON")
            return

        if "uv" in message_json:
            self.uv_light_status(message_json["uv"])
            
        if "lightening" in message_json:
            self.lightening(message_json["lightening"])
            
        if "maglock" in message_json:
            self.maglock(message_json["maglock"])
            
            
puzzle = Puzzle(network, config["MQTT_TOPIC"])
network.subscribe_to_topic(config["MQTT_TOPIC"], puzzle.process_message)

while True:
    
    sleep(0.1)
   
    network.check_for_messages()
    
    puzzle.step()
    