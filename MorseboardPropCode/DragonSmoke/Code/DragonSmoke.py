from machine import Pin, SoftI2C, UART

from libs.miNetwork import MINetwork
from libs import webrepl

import json
from time import sleep, ticks_ms
from neopixel import NeoPixel

import sys
import machine

LED = Pin(25, Pin.OUT)

NETWORK = False

# Set up relay and 5V output
FIVE_VOLT_PIN = Pin(15, Pin.OUT)

FIVE_VOLT_PIN.off()

INDICATOR_LED_PIN = 10

# load config
with open("config.json") as f:
    config = json.load(f)


if NETWORK:
    network = MINetwork()


    # load webrepl
    webrepl.start()


    network.connect_to_network()
    network.connect_to_mqtt_broker(config["MQTT_CLIENT"], config["MQTT_SERVER"])

else:
    network = None

class Puzzle:
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
        
    
 
    def step(self):
        if NETWORK:
            if ticks_ms() - self.heartbeat_timer > self.heartbeat_timeout:
                network.send_mqtt_json(self.topic, {"heartbeat" : "alive"})
                self.heartbeat_timer = ticks_ms()
                
            if ticks_ms() - self.pong_timer > self.pong_timeout:
                self.network.check_mqtt_and_reconnect()
                self.pong_timer = ticks_ms()
        
            
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
        
        if "power" in message_json:
            if message_json["power"] is "on":
                FIVE_VOLT_PIN.on()
            else:
                FIVE_VOLT_PIN.off()


puzzle = Puzzle(network, config["MQTT_TOPIC"])
                              
if NETWORK:
    network.subscribe_to_topic(config["MQTT_TOPIC"], puzzle.process_message)

while False:
    
    if NETWORK:
        try:
            network.check_for_messages()
        except:
            network.check_mqtt_and_reconnect()
        
    puzzle.step()
    sleep(0.1)
    



    



