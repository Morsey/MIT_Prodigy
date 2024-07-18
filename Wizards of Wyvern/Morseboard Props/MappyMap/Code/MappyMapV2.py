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
        
        self.pong_timer = ticks_ms()
        self.pong_timeout = 5000
        
        self.network = network
        self.topic = topic
        
        self.communication = None
        
        INDICATOR_LED_PIN = 10
        self.LED = NeoPixel(Pin(INDICATOR_LED_PIN), 4)
        
        self.locations = self.setup_pins()
        self.last_locations_on = None
        
    def setup_pins(self):
        
        across = [7, 10, 11, 12, 13]
        down = [2, 3, 4, 5, 6]


        across_pins = [
            Pin(across[0], Pin.OUT),
            Pin(across[1], Pin.OUT),
            Pin(across[2], Pin.OUT),
            Pin(across[3], Pin.OUT),
            Pin(across[4], Pin.OUT)
            ]

        down_pins = [
            Pin(down[0], Pin.IN, Pin.PULL_DOWN),
            Pin(down[1], Pin.IN, Pin.PULL_DOWN),
            Pin(down[2], Pin.IN, Pin.PULL_DOWN),
            Pin(down[3], Pin.IN, Pin.PULL_DOWN),
            Pin(down[4], Pin.IN, Pin.PULL_DOWN),
            ]
        
        locations = []

        location_number = 1

        # Initialise locations
        for y in down_pins:
            y.off()
            for x in across_pins:
                locations.append([location_number, x, y])
                location_number += 1
        
        return locations

 
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
        
        self.check_locations()
        
        
    def process_message(self, topic, raw_message):
        message = raw_message.decode('utf-8')
       
        try:
            message_json = json.loads(message)
        except ValueError:
            print("not valid JSON")
            return
        print(message_json)
                 
                 
    def check_locations(self):
        
        # Build arrays of initial and final locations sensed
        start_location_array = [0] * 25
        end_location_array = [0] * 25
        
        for location in self.locations:
            location[1].on()
            start_location_array[location[0]-1] = location[2].value()  # correct location for numbering 1-25 not 0-24
            location[1].off()
        sleep(0.1)
        for location in self.locations:
            location[1].on()
            end_location_array[location[0]-1] = location[2].value()  # correct location for numbering 1-25 not 0-24
            location[1].off()
        
        # Look for location in both
        locations_on = []
        for index, (loc_start, loc_end) in enumerate(zip(start_location_array, end_location_array)):
            if loc_start + loc_end == 2:
                locations_on.append(index + 1) # +1 to give 1 start location numbers not zero
            
        if locations_on != self.last_locations_on:
            self.last_locations_on = locations_on.copy()
            network.send_mqtt_json(self.topic, {"locations": locations_on})
    

puzzle = Puzzle(network, config["MQTT_TOPIC"])
network.subscribe_to_topic(config["MQTT_TOPIC"], puzzle.process_message)


while True:
    
    network.check_for_messages()
    puzzle.step()
    sleep(0.01)
    

