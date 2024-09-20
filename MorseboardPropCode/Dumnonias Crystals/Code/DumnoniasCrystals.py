from machine import Pin, SoftI2C, UART
from libs.miNetwork import MINetwork
from libs import webrepl
from libs.debounced_input import DebouncedInput
import json
from time import sleep, ticks_ms
from neopixel import NeoPixel
import sys
import machine
import math
import gc


# Function to print memory status
def print_memory_status():
    gc.collect()  # Trigger garbage collection
    free_mem = gc.mem_free()  # Get available free memory
    allocated_mem = gc.mem_alloc()  # Get allocated memory
    print(f"Free memory: {free_mem}, Allocated memory: {allocated_mem}")


LED = Pin(25, Pin.OUT)


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

# global function for callback
def button_pressed(pin, pressed, duration_ms, btn_id):
    # trigger on button down
    if pressed:
        puzzle.button_pressed(btn_id)
    
class Buttons:
    
    def __init__(self):
        self.pin_numbers = [3,4,5,6]
        self.pins = []
        for p in self.pin_numbers:
            self.pins.append(Pin(p, Pin.IN, Pin.PULL_UP))
            
        self.last_status ={1:1, 2:1, 3:1, 0:1}
            
        
    def check_buttons(self):
        status = {}
        for i in range(0, len(self.pins)):
            status[i]= self.pins[i].value()
        return status


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

        self.button_leds = NeoPixel(Pin(2), 4)
        self.crystal_leds = NeoPixel(Pin(7),34)
        
        self.button_colours = [[0,0,0],
                               [0,0,0],
                               [0,0,0],
                               [0,0,0]]
        
        self.crystal_colours = {"speed": 1,
                                "start_hue": 189,
                                "end_hue": 268,
                                "current_hue": 189,
                                "direction": "up",
                                "enabled": False,
                                "level":0}

        #self.buttons = [None, None, None, None]
        #self.buttons[0] = DebouncedInput(3, button_pressed, pin_pull=Pin.PULL_UP, button_id=0, debounce_ms=50,pin_logic_pressed=False)
        #self.buttons[1] = DebouncedInput(4, button_pressed, pin_pull=Pin.PULL_UP, button_id=1, debounce_ms=50,pin_logic_pressed=False)
        #self.buttons[2] = DebouncedInput(5, button_pressed, pin_pull=Pin.PULL_UP, button_id=2, debounce_ms=50,pin_logic_pressed=False)
        #self.buttons[3] = DebouncedInput(6, button_pressed, pin_pull=Pin.PULL_UP, button_id=3, debounce_ms=50,pin_logic_pressed=False)
        
        
        self.buttons = Buttons()
        
        self.touchingSymbolsPin = Pin(10, Pin.IN, Pin.PULL_UP)
        self.touchingSymbolState = False
        
        
        self.room_leds = NeoPixel(Pin(11),100)
        self.room_leds_mode = "rainbow"

        self.count = 0

        self.room_colours = {"speed": 1,
                                "start_hue": 189,
                                "end_hue": 268,
                                "current_hue": 189,
                                "direction": "up",
                                "enabled": True,
                                "level":0}
        
        
    def make_rainbow_array(self):
        pass
        
    def step(self):
        if ticks_ms() - self.heartbeat_timer > self.heartbeat_timeout:
            network.send_mqtt_json(self.topic, {"heartbeat" : network.nic.ifconfig()[0]})
            
            self.heartbeat_timer = ticks_ms()
           
            
        if ticks_ms() - self.indicator_timer > self.indicator_timeout:
            self.indicator_led.toggle()
            self.indicator_timer = ticks_ms()
            
        if ticks_ms() - self.pong_timer > self.pong_timeout:
            self.network.check_mqtt_and_reconnect()
            self.pong_timer = ticks_ms()
            
        self.update_crystal_leds()
        self.check_touchingSymbols()
        self.update_room_leds()
        self.check_buttons()
        
    def check_buttons(self):
        status = self.buttons.check_buttons()
        if status != self.buttons.last_status:
            # check each button if it has changed from 1 to 0 send a pressed message
            for b in range(0,4):
                if status[b] != self.buttons.last_status[b] and status[b] == 0 :
                    print(f"{b} - {status[b]}")
                    self.puzzle_json_generator({"pressed":b})
            self.buttons.last_status = status
            
    
            
        
    def update_room_leds(self):
        if self.room_leds_mode == "rainbow":
            def hsl_to_rgb(h, s, v):
                h = float(h)
                s = float(s)
                v = float(v)
                h60 = h / 60.0
                h60f = math.floor(h60)
                hi = int(h60f) % 6
                f = h60 - h60f
                p = v * (1 - s)
                q = v * (1 - f * s)
                t = v * (1 - (1 - f) * s)
                r, g, b = 0, 0, 0
                if hi == 0: r, g, b = v, t, p
                elif hi == 1: r, g, b = q, v, p
                elif hi == 2: r, g, b = p, v, t
                elif hi == 3: r, g, b = p, q, v
                elif hi == 4: r, g, b = t, p, v
                elif hi == 5: r, g, b = v, p, q
                r, g, b = int(r * 255), int(g * 255), int(b * 255)
                return r, g, b
            

            if self.room_colours["direction"] is "up":
                self.room_colours["current_hue"] +=self.room_colours["speed"]
                
                if self.room_colours["current_hue"] > self.room_colours["end_hue"]:
                    self.room_colours["direction"] = "down"
            
            if self.room_colours["direction"] is "down":
                self.room_colours["current_hue"] -= self.room_colours["speed"]
                
                if self.room_colours["current_hue"] < self.room_colours["start_hue"]:
                    self.room_colours["direction"] = "up"
                
            
            r,g,b = hsl_to_rgb(self.room_colours["current_hue"], 0.9, 0.7)
            
            
            
            for i in range(0,100):
                self.room_leds[i] = [g,r,b]
                
            
            for i in range(30,38):
                self.room_leds[i] = [255,255,255]
                
            self.room_leds.write()
            
        
    def check_touchingSymbols(self):
        currentState = self.touchingSymbolsPin.value()
        if currentState != self.touchingSymbolState:
            self.touchingSymbolState = currentState
            self.puzzle_json_generator({"symbols":self.touchingSymbolState})
                
        
    def set_button_colours(self, colours):
        print(colours)
        for idx in colours:
            self.button_colours[int(idx) -1] = colours[idx]
            self.button_leds[int(idx)-1] = colours[idx]
        self.button_leds.write()
            
    def set_crystal_colours(self, colours):
        print(colours)
        if "enabled" in colours:
            self.crystal_colours["enabled"] = colours["enabled"]
            print(f"crystals are enabled: {colours['enabled']}")
        
        self.crystal_colours["level"] = colours["level"]
            
    def update_crystal_leds(self):
        def hsl_to_rgb(h, s, v):
            h = float(h)
            s = float(s)
            v = float(v)
            h60 = h / 60.0
            h60f = math.floor(h60)
            hi = int(h60f) % 6
            f = h60 - h60f
            p = v * (1 - s)
            q = v * (1 - f * s)
            t = v * (1 - (1 - f) * s)
            r, g, b = 0, 0, 0
            if hi == 0: r, g, b = v, t, p
            elif hi == 1: r, g, b = q, v, p
            elif hi == 2: r, g, b = p, v, t
            elif hi == 3: r, g, b = p, q, v
            elif hi == 4: r, g, b = t, p, v
            elif hi == 5: r, g, b = v, p, q
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
            return r, g, b
        

        if self.crystal_colours["direction"] is "up":
            self.crystal_colours["current_hue"] +=self.crystal_colours["speed"]
            
            if self.crystal_colours["current_hue"] > self.crystal_colours["end_hue"]:
                self.crystal_colours["direction"] = "down"
        
        if self.crystal_colours["direction"] is "down":
            self.crystal_colours["current_hue"] -=self.crystal_colours["speed"]
            
            if self.crystal_colours["current_hue"] < self.crystal_colours["start_hue"]:
                self.crystal_colours["direction"] = "up"
            
        
        r,g,b = hsl_to_rgb(self.crystal_colours["current_hue"], 0.9, 0.7)
        
        
            
            
            
        for i in range(0,34):
                self.crystal_leds[i] = [0,0,0]
                
        if self.crystal_colours["level"] > 0:
            for i in range(0,4):
                self.crystal_leds[i] = [g,r,b]
        
        if self.crystal_colours["level"] > 1:
            for i in range(30,34):
                self.crystal_leds[i] = [g,r,b]
                
        
        if self.crystal_colours["level"] > 2:
            for i in range(5,9):
                self.crystal_leds[i] = [g,r,b]
                
        
        if self.crystal_colours["level"] > 3:
            for i in range(26,29):
                self.crystal_leds[i] = [g,r,b]
                
        
        if self.crystal_colours["level"] >4:
            for i in range(10,14):
                self.crystal_leds[i] = [g,r,b]
            
            for i in range(21,25):
                self.crystal_leds[i] = [g,r,b]
                
        
        if self.crystal_colours["level"] >5:
            for i in range(0,34):
                self.crystal_leds[i] = [g,r,b]
                
                
        self.crystal_leds.write()
    
    def process_message(self, topic, raw_message):
        message = raw_message.decode('utf-8')
       
        try:
            message_json = json.loads(message)
        except ValueError:
            print("not valid JSON")
            return
    
        if "button_colours" in message_json:
            self.set_button_colours(message_json['button_colours'])
            
        if "crystal_colours" in message_json:
            self.set_crystal_colours(message_json["crystal_colours"])
            
        if "latch_lock" in message_json:
            if message_json["latch_lock"] == "open":
                RELAY_PIN.on()
                sleep(0.5)
                RELAY_PIN.off()
                
        if "touching_symbols_state" in message_json:
            self.puzzle_json_generator({"symbols":self.touchingSymbolState})
            
    def button_pressed(self, button_id):
        self.puzzle_json_generator({"pressed":button_id})

    def puzzle_json_generator(self, status):
        print(f"sending {status}")
        self.network.send_mqtt_json(self.topic, status)
        return json.dumps(status)
    
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


        
 
while True:
    
    network.check_for_messages()
        
    puzzle.step()
    sleep(0.01)
