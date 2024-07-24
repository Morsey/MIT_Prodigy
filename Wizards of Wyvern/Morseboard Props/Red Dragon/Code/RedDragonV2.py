from machine import Pin, SoftI2C, UART

from libs.miNetwork import MINetwork
from libs import webrepl

import json
from time import sleep, ticks_ms
from neopixel import NeoPixel

import sys
import machine

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

network = MINetwork()


# load webrepl
webrepl.start()


network.connect_to_network()
network.connect_to_mqtt_broker(config["MQTT_CLIENT"], config["MQTT_SERVER"])

class RedDragon:
    def __init__(self):
        self.station_pin = Pin(2,Pin.IN, Pin.PULL_UP)
        self.tunnel_pin = Pin(3,Pin.IN, Pin.PULL_UP)
    
    def forward(self):
        RELAY_PIN.on()
        FIVE_VOLT_PIN.on()
        
    def backward(self):
        RELAY_PIN.on()
        FIVE_VOLT_PIN.off()
        
    def stop(self):
        RELAY_PIN.off()
        
    def go_to_station(self):
        print("to station")
        start_time = ticks_ms()
        if self.station_pin.value() == 1:
            self.forward()
            while self.station_pin.value() == 1 and (ticks_ms()-start_time) < 16000:
                sleep(0.001)
                pass
        self.stop()
        
    def go_to_tunnel(self):
        print("to_tunnel")
        start_time = ticks_ms()
        if self.tunnel_pin.value() == 1:
            self.backward()
            while self.tunnel_pin.value() == 1 and ((ticks_ms() - start_time) < 16000):
                sleep(0.001)
                pass
        self.stop()
        
    def where_are_you(self):
        if not self.station_pin.value():
            return "station"
        if not self.tunnel_pin.value():
            return "tunnel"
        return "in_motion"
    
 
                

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
        
        self.red_dragon = RedDragon()
    
 
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
        
            
    def process_message(self, topic, raw_message):
        message = raw_message.decode('utf-8')
       
        try:
            message_json = json.loads(message)
        except ValueError:
            print("not valid JSON")
            return
        
        if "direction" in message_json:
            if message_json["direction"] is "station":
                self.network.send_mqtt_json(self.topic, {"status": "in_motion"})
                self.red_dragon.go_to_station()
                self.network.send_mqtt_json(self.topic, {"status": self.red_dragon.where_are_you()})
                 
            if message_json["direction"] is "tunnel":
                self.network.send_mqtt_json(self.topic, {"status":"in_motion"})
                self.red_dragon.go_to_tunnel()
                self.network.send_mqtt_json(self.topic, {"status": self.red_dragon.where_are_you()})
                
        if "location" in message_json:
            print("location?")
            self.network.send_mqtt_json(self.topic, {"status": self.red_dragon.where_are_you()})


    def puzzle_json_generator(self, status):
        response = {"status": status}
        if NETWORK:
            communication.mqtt_send_json(response)
        return json.dumps(response)

puzzle = Puzzle(network, config["MQTT_TOPIC"])
network.subscribe_to_topic(config["MQTT_TOPIC"], puzzle.process_message)

while True:
    try:
        network.check_for_messages()
    except:
        network.check_mqtt_and_reconnect()
        
    puzzle.step()
    sleep(0.1)
    



    



