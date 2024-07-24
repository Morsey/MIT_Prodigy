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
        
        self.compass = Compass()
        self.compass.all_off()
        self.communication = None
        
        INDICATOR_LED_PIN = 10
        self.LED = NeoPixel(Pin(INDICATOR_LED_PIN), 4)
        
        self.led_colour = [0, 0, 0]
        self.blank_led()
        self.last_change = ticks_ms()
        self.led_brightness = 0
        self.current_duration = 0
        
        self.pointing = False
        
        self.animals = Animals()
        
 
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
        
        if ((ticks_ms() - self.last_change) > (self.current_duration * 1000)) and self.pointing:
            self.led_colour = [0, 0, 0]
            self.compass.all_off()
            self.pointing = False
            
        self.update_LED()
        
        self.check_animals()
        
    def check_animals(self):
        status = self.animals.check_pins()
        if status != self.animals.last_status:
            self.animals.last_status = status
            network.send_mqtt_json(self.topic, {"animals": status})
    
                     
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
                for led in range(len(self.LED)):
                    self.LED[led] = wheel(x)
                    self.LED.write()
                    sleep(0.001)

        self.blank_led()

    def blank_led(self):
        for led in range(len(self.LED)):
            self.LED[led] = [0, 0, 0]
        self.LED.write()

    def process_message(self, topic, raw_message):
        message = raw_message.decode('utf-8')
       
        try:
            message_json = json.loads(message)
        except ValueError:
            print("not valid JSON")
            return
        print(message_json)
        if "duration" in message_json:
            self.current_duration = message_json["duration"]
            
        if "led" in message_json:
            self.led_colour = message_json["led"]
            
        action_made = False
        if "direction" in message_json:
            self.last_change = ticks_ms()
            if message_json["direction"] is "north":
                self.compass.point("north")
                self.pointing = True
                 
            if message_json["direction"] is "south":
                self.compass.point("south")
                self.pointing = True
                
            if message_json["direction"] is "west":
                self.compass.point("west")
                self.pointing = True
                
            if message_json["direction"] is "east":
                self.compass.point("east")
                self.pointing = True
                 
            if message_json["direction"] is "none":
                self.compass.all_off()
                self.pointing = False
                 
            if message_json["direction"] is "spin":
                for l in range(0,4):
                    self.LED[l] = self.led_colour
                    self.LED.brightness = 0
                self.LED.write()
                puzzle.incorrect(3, [0, 255, 0])
                self.pointing = False
                 
        

    def point(self, direction, led_colour, duration=None):
        self.compass.point(direction)
        self.last_change = ticks_ms()
        self.current_duration = duration
        self.led_colour = led_colour

    def get_brightness(self):
        self.led_brightness += 5
        if self.led_brightness > 255 * 2:
            self.led_brightness = 0
        if self.led_brightness < 256:
            return self.led_brightness
        if self.led_brightness > 255:
            return 255 - (self.led_brightness - 256)
        
    def update_LED(self):
        brightness = self.get_brightness()
        r = int(self.led_colour[0] * brightness/255)
        g = int(self.led_colour[1] * brightness/255)
        b = int(self.led_colour[2] * brightness/255)
        for l in range(len(self.LED)):
            self.LED[l] = [r,g,b]
            self.LED.write()
            
    # this is a blocking function
    def incorrect(self, duration, led_colour = [0, 255, 0]):
        start_time = ticks_ms()
        self.led_colour = led_colour
        TICK_COUNT = 200
        tick_to_change = TICK_COUNT
        directions = [Compass.Directions.West, Compass.Directions.South, Compass.Directions.East, Compass.Directions.North]
        direction = 0
        while ticks_ms() - start_time < duration * 1000:
            
            sleep(0.001)
            self.update_LED()
            tick_to_change-=1
            
            if tick_to_change < 0:
                tick_to_change = TICK_COUNT
                direction +=1
                if direction > 3:
                    direction = 0
                self.compass.point(directions[direction])
                print(directions[direction])
                
        self.compass.all_off()
        self.led_colour = [0,0,0]
             
            

    
class Compass:
    
    class Directions:
        North = "north"
        South = "south"
        East = "east"
        West = "west"
        Off = "off"
    
    def __init__(self):
        
        WEST_PIN = 14 #w
        EAST_PIN = 11
        SOUTH_PIN = 13 # soutn
        NORTH_PIN = 12 #north

        self.n = Pin(NORTH_PIN, Pin.OUT)
        self.s = Pin(SOUTH_PIN, Pin.OUT)
        self.e = Pin(EAST_PIN, Pin.OUT)
        self.w = Pin(WEST_PIN, Pin.OUT)
        self.points = {self.Directions.North: [self.n],
                       self.Directions.East: [self.e],
                       self.Directions.South: [self.s],
                       self.Directions.West: [self.w]}

    def all_off(self):
        for point in self.points:
            for pin in self.points[point]:
                pin.off()
        
    def point(self, direction):
        self.all_off()
        for pin in self.points[direction]:
            pin.on()
            
    def spin(self, duration_s):
        start_time = ticks_ms()
        wait = 0.5

        while (ticks_ms() - start_time) < (duration_s * 1000):
            for direction in [self.Directions.North, self.Directions.West, self.Directions.South, self.Directions.EAST]:

                sleep(wait)
                self.point(direction)
                wait -= 0.05
                if wait < 0.2:
                    wait = 0.2

        self.all_off()
        

class Animals:
    
    def __init__(self):
        self.pin_numbers = [2,3,4,5,6]
        self.pins = []
        for p in self.pin_numbers:
            self.pins.append(Pin(p, Pin.IN, Pin.PULL_UP))
            
        self.last_status ={}
            
        
    def check_pins(self):
        status = {}
        for i in range(0, len(self.pins)):
            status[i]= self.pins[i].value()
        return status

puzzle = Puzzle(network, config["MQTT_TOPIC"])
network.subscribe_to_topic(config["MQTT_TOPIC"], puzzle.process_message)
puzzle.boot_up_indication()

while True:
    try:
        network.check_for_messages()
    except:
        network.check_mqtt_and_reconnect()
        
    puzzle.step()
    sleep(0.01)
    
