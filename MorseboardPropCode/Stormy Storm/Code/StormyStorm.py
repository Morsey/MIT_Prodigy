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
        
        
        self.UV_Pin = Pin(15, Pin.OUT) # 5V out pin
        self.current_uv_status = None
        
        self.number_leds = 100
        
        self.np = NeoPixel(Pin(2), self.number_leds, bpp=4)
        self.mag_switch = Pin(3, Pin.IN, Pin.PULL_UP)
        self.hootini_switch = Pin(4, Pin.OUT)
        self.hootini_switch.off()
        
        self.maglock_on = False
        
        self.led_grid = [
            [1 , 2,  3,  4,  5,  6,  7,  8,  9,  10],
            [11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
            [21, 22, 23, 24, 25, 26, 27, 28, 29, 30],
            [31, 32, 33, 34, 35, 36, 37, 38, 39, 40],
            [41, 42, 43, 44, 45, 46, 47, 48, 49, 50],
            [51, 52, 53, 54, 55, 56, 57, 58, 59, 60],
            [61 ,62, 63, 64, 65, 66, 67, 68, 69, 70],
            [71, 72, 73, 74, 75, 76, 77, 78, 79, 80],
            [81, 82, 83, 84, 85, 86, 87, 88, 89, 90],
            [91, 92, 93, 94, 95, 96, 97, 98, 99, 100],
            ]
        
        self.rainbow_on = False
        self.UV_enabled = False
        
    def step(self):
        if ticks_ms() - self.heartbeat_timer > self.heartbeat_timeout:
            network.send_mqtt_json(self.topic, {"heartbeat" : network.nic.ifconfig()[0]})
            self.heartbeat_timer = ticks_ms()
            
        if ticks_ms() - self.indicator_timer > self.indicator_timeout:
            self.indicator_led.toggle()
            self.indicator_timer = ticks_ms()
            
        self.check_mag_switch()
        
        if self.rainbow_on:
            self.rainbow_step()
    
    def uv_light_status(self, status):
        if status == "on":
            self.UV_Pin.on()
        if status == "off":
            self.UV_Pin.off()
            
    def lightening(self, status):
        
        def led_action(status):
            for n in range(0,100):
                if status is "on" or status is 1:
                    self.np[n] = (0, 0, 0, 255)
                else:
                    self.np[n] = (0, 0, 0, 0)
            self.np.write()
                    
    
        if status == "all_flash":
            flash = [[50, 1],[100, 0], [100, 1], [200, 0], [75, 1], [150, 0]]
            
            for timing in flash:
                led_action(timing[1])
                
                sleep(timing[0] / 1000.0)
        
        if status == "random_nine":
            self.random_nine()
            
            


         
    def rainbow_step(self):
        
        
        def rainbow_cycle():
        
            def wheel(pos):
                # Input a value 0 to 255 to get a color value.
                # The colors are a transition r - g - b - back to r.
                if pos < 0 or pos > 255:
                    return (0, 0, 0, 0)
                if pos < 85:
                    return (255 - pos * 3, pos * 3, 0, 0)
                if pos < 170:
                    pos -= 85
                    return (0, 255 - pos * 3, pos * 3, 0)
                pos -= 170
                return (pos * 3, 0, 255 - pos * 3, 0, 0)
            
            
            for j in range(0,255,20):
                for i in range(10):
                    rc_index = (i * 255 // 10) + j
                   
                    self.np[i] = wheel(rc_index & 255)
                    self.np[i+10] = wheel(rc_index & 255)
                    self.np[i+20] = wheel(rc_index & 255)
                    self.np[i+30] = wheel(rc_index & 255)
                    self.np[i+40] = wheel(rc_index & 255)
                    self.np[i+50] = wheel(rc_index & 255)
                    self.np[i+60] = wheel(rc_index & 255)
                    self.np[i+70] = wheel(rc_index & 255)
                    self.np[i+80] = wheel(rc_index & 255)
                    self.np[i+90] = wheel(rc_index & 255)
                self.np.write()
            
        rainbow_cycle()
            
    def rainbow_pulse(self, status):
        if status is "on":
            self.rainbow_on = True
        else:
            self.rainbow_on = False
            for n in range(0,100):
                self.np[n] = (0, 0, 0, 0)
            self.np.write()
        
    def random_pulse(self, length):
        def pick_random_consecutive_sequence(arr, X):

            Y = len(arr)

            if X > Y:
                raise ValueError("X cannot be greater than the length of the array.")

            start_index = random.randint(0, Y - X)
            return arr[start_index:start_index + X]
        
        def led_action(leds, status):
            
            for n in range(0,100):
                self.np[n] = (0, 0, 0, 0)
            for n in leds:
                if status is "on" or status is 1:
                    self.np[n] = (0, 0, 0, 255)
               
                    
            self.np.write()
            
        
        led_picks = pick_random_consecutive_sequence(list(range(0,self.number_leds)),length)
         
        flash = [[50, 1],[100, 0], [100, 1], [200, 0], [75, 1], [150, 0]]
        
        
        for timing in flash:
            
            led_action(led_picks, timing[1])
                
            sleep(timing[0] / 1000.0)
            
            
    def random_nine(self):
        
        def led_action(leds, status):
            
            for n in range(0,100):
                self.np[n] = (0, 0, 0, 0)
            for n in leds:
                if status is "on" or status is 1:
                    self.np[n] = (0, 0, 0, 255)
               
                    
            self.np.write()
            
        height = len(self.led_grid)
        width = len(self.led_grid[1])
        
        random_height = random.randint(1, height-2)
        random_width = random.randint(1, width-2)
        
        action_leds = []
        for h in range(random_height-1, random_height+2):
            for w in range(random_width-1, random_width+2):
                action_leds.append(self.led_grid[h][w] -1)
                
        flash = [[50, 1],[100, 0], [100, 1], [200, 0], [75, 1], [150, 0]]
        
        
        for timing in flash:
            
            led_action(action_leds, timing[1])
                
            sleep(timing[0] / 1000.0)
     
            
    def process_message(self, topic, raw_message):
        message = raw_message.decode('utf-8')
       
        try:
            message_json = json.loads(message)
        except ValueError:
            print("not valid JSON")
            return
        
        if "enable_uv" in message_json:
            self.UV_enabled = message_json["enable_uv"]

        if "uv" in message_json:
            self.uv_light_status(message_json["uv"])
            
        if "lightening" in message_json:
            self.lightening(message_json["lightening"])
            
        if "random_pulse" in message_json:
            self.random_pulse(message_json["random_pulse"])
            
        if "maglock" in message_json:
            self.maglock(message_json["maglock"])
            
        if "rainbow" in message_json:
            self.rainbow_pulse(message_json["rainbow"])
            
        
        if "open_hootini" in message_json:
            # if maglock is off, pulse on in order to give power
            if not self.maglock_on:
                self.relay_pin.on()
                
            self.hootini_switch.on()
            sleep(0.2)
            self.hootini_switch.off()
            
            # switch maglock off again if needed
            if not self.maglock_on:
                self.relay_pin.off()
        
            
            
    def maglock(self, status):
        if status == "on":
            print("relay on")
            self.relay_pin.on()
            self.maglock_on = True
        else:
            print("relay off")
            self.relay_pin.off()
            self.maglock_on = False
    
    def check_mag_switch(self):
        
        initial_value = self.mag_switch.value()
        sleep(0.02)
        final_value = self.mag_switch.value()
        
        if initial_value == final_value:
            if initial_value != self.current_uv_status:
                self.current_uv_status = initial_value
                
                if initial_value == 0:
                    if self.UV_enabled:
                        self.uv_light_status("on")
                        network.send_mqtt_json(self.topic, {"uv_status" : "on"})
                else:
                    self.uv_light_status("off")
                    network.send_mqtt_json(self.topic, {"uv_status" : "off"})

puzzle = Puzzle(network, config["MQTT_TOPIC"])
network.subscribe_to_topic(config["MQTT_TOPIC"], puzzle.process_message)

while True:
    
    sleep(0.1)
    network.check_mqtt_and_reconnect()
    network.check_for_messages()
    
    puzzle.step()
    