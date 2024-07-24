import time
from time import ticks_ms, sleep
from machine import Pin, UART
import json
from neopixel import NeoPixel
from libs.miNetwork import MINetwork
import random
from libs.Stepper import Stepper
from libs import webrepl


# load config
with open("config.json") as f:
    config = json.load(f)
    
NETWORK = True

# Set up serial communication
# noinspection PyArgumentList
uart = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))
# noinspection PyArgumentList
uart.init(bits=8, parity=None, stop=2)

if NETWORK:
    network = MINetwork()
    
    

    # load webrepl
    webrepl.start()

    
    network.connect_to_network()
    network.connect_to_mqtt_broker(config["MQTT_CLIENT"], config["MQTT_SERVER"])
else:
    network = None
 


class Spider:
    def __init__(self, id_):
        self.id = id_
        self.state = None
        self.hunting_time = None
        self.sleeping_time = None

    def send_spider_command(self, cmd):
        msg = f"XX{self.id}{cmd}"
        uart.write(bytes(msg, 'utf8'))

    def get_spider_response(self):
        if uart.any():
            data = uart.read()
            decoded_data = data.decode('utf-8')

            # split into commands on XX
            cmds = decoded_data.split("XX")

            responses = []

            for cmd in cmds:
                # is there non-zero command length
                if len(cmd) > 0:
                    responses.append((int(cmd[0]), cmd[1]))
            return responses
        else:
            return None

    def wake_up(self):
        self.send_spider_command(self.hunt)

        self.update_status()
        
        if self.state is not self.hunt:
            print("ERROR!!! hasn't woken up")
        self.hunting_time = ticks_ms()

    def go_to_sleep(self):
        self.send_spider_command(self.sleep)
        self.update_status()

        if self.state is not self.sleep:
            print("ERROR!!! hasn't gone to sleep")
        self.sleeping_time = ticks_ms()


    def kill_it(self):
        self.send_spider_command(self.kill)
        self.update_status()
        if self.state is not self.kill:
            print("ERROR!!! hasn't died - probably dying")


    def update_status(self):
        self.send_spider_command(self.get_status)
        sleep(0.04)
        
        responses = self.get_spider_response()
        
        for response in responses:
            if response[0] == self.id:
                self.state = response[1]
        return self.state

    sleep = "z"
    kill = "k"
    hunt = "h"
    dying = "d"
    get_status = "s"



class EggMover:
    def __init__(self):
        # Define the pins
        self.step_pin = 13  # GPIO number where step pin is connected
        self.dir_pin = 14  # GPIO number where dir pin is connected

        # Initialize stepper
        self.stepper = Stepper(self.step_pin, self.dir_pin)

        self.egg_sensor = Pin(26, Pin.IN, Pin.PULL_UP)
        
        self.out_position = 1600

    def go_home(self):
        print("egg going home")
        self.stepper.set_speed(300)
        
        start_time = time.ticks_ms()  # capture start of home movement
        while self.egg_sensor.value() > 0 and time.ticks_ms() - start_time < 5000:  # Egg isn't at home..
            self.stepper.position = 0
            self.stepper.move_to(-40)

        if (time.ticks_ms() - start_time) > 8000:
            print("EggMover: home not found - timing out", 1)
        self.stepper.position = 0

    def go_out(self):
        print("egg going out")
        self.stepper.set_speed(400)
        self.stepper.move_to(self.out_position)
        

class Puzzle:
    
    def __init__(self, network, topic):
        self.heartbeat_timer = ticks_ms()
        self.heartbeat_timeout = 10000
        
        self.indicator_timer = ticks_ms()
        self.indicator_timeout = 1000
        self.indicator_led = Pin(25, Pin.OUT)
        
        self.pong_timer = ticks_ms()
        self.pong_timeout = 5000
        
        self.relay_pin = Pin(22, Pin.OUT)
        
        if NETWORK:
            self.network = network
            
        self.topic = topic
        
        self.light_pin = Pin(15, Pin.OUT)
        
        self.startup_indicator()
        
        self.status = None
        self.spiders = None
        
        self.egg_mover = EggMover()
        self.initialise_egg()
        
    
    def process_message(self, topic, raw_message):
        message = raw_message.decode('utf-8')
       
        try:
            message_json = json.loads(message)
        except ValueError:
            print("not valid JSON")
            return


        if "spider action" in message_json:
            if message_json["spider action"] == "wake all":
                self.wake_all_spiders()
            
            elif message_json["spider action"] == "sleep all":
                self.sleep_all_spiders()()
                
            elif message_json["spider action"] == "kill all":
                self.kill_all_spiders()()
            else:
                print(f"spider action not understood: {message_json}")
                
        if "spider multi action" in message_json:
            cmds = message_json["spider multi action"]
            
            for cmd in cmds:
                if cmd[1] == "wake":
                    self.wake_spider_id(cmd[0])
                if cmd[1] == "sleep":
                    self.sleep_spider_id(cmd[0])
                if cmd[1] == "kill":
                    self.kill_spider_id(cmd[0])
                    

        if "egg position" in message_json:
            if message_json["egg position"] == "go home":
                self.egg_mover.go_home()
            
            if message_json["egg position"] == "go out":
                self.egg_mover.go_out()
        
        if "light" in message_json:
            self.light_control(message_json["light"])


    def light_control(self, status):
        if status == "on":
            self.light_pin.on()
            print("light on")
        else:
            self.light_pin.off()
            print("light off")

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
            
        self.check_to_send_statuses()
            
    
    def startup_indicator(self):
        for i in range(0,3):
            sleep(0.1)
            self.light_pin.on()
            sleep(0.1)
            self.light_pin.off()
    
            
    def initialise_egg(self):
        self.egg_mover.go_home()
        self.egg_mover.go_out()
    
    
    def initialise_spiders(self, ids):
        #  initialise spiders
        self.spiders = {}
        for id_ in ids:
            self.spiders[id_] = Spider(id_)

        print(self.spiders)

        # send all to sleep
        print("sleeping all spiders")
        self.sleep_all_spiders()
        sleep(2)

        # wake up
        print("waking up all spiders")
        self.wake_all_spiders()
        sleep(2)

        # kill all
        print("killing all spiders")
        self.kill_all_spiders()
        sleep(2)

    
    def sleep_all_spiders(self):
        print("sleeping all spiders")
        for _id in self.spiders:
            self.sleep_spider_id(_id)
            
    def wake_all_spiders(self):
        print("waking all spiders")
        for _id in self.spiders:
            self.wake_spider_id(_id)
               
    def kill_all_spiders(self):
        print("killing all spiders")
        for _id in self.spiders:
            self.kill_spider_id(_id)
            
    def wake_spider_id(self, _id):
        if _id in self.spiders: 
            print(f"Waking spiker {_id}")
            self.spiders[_id].wake_up()
            
    def kill_spider_id(self, _id):
        if _id in self.spiders:
            self.spiders[_id].kill_it()
            
    def sleep_spider_id(self, _id):
        if _id in self.spiders:
            print(_id)
            self.spiders[_id].go_to_sleep()
            
    def get_all_spiders_statuses(self):
        statuses = {}
        for _id in self.spiders:
            statuses[_id] = self.get_spider_status(_id)
        return statuses
    
    def get_spider_status(self, _id):
        if _id in self.spiders:
            return self.spiders[_id].update_status()
        return
    
    def check_to_send_statuses(self):
        new_status = self.get_all_spiders_statuses()
        if new_status != self.status:
            self.status = new_status
            print(self.status)


  

puzzle = Puzzle(network, config["MQTT_TOPIC"])
if NETWORK:
    network.subscribe_to_topic(config["MQTT_TOPIC"], puzzle.process_message)


puzzle.initialise_spiders([1, 2, 3, 4])
while False:
    network.check_for_messages()
    puzzle.step()
    sleep(0.01)



# for use in final when need to check for dropped network
while True:
    if NETWORK:
        try:
            network.check_for_messages()
        except:
            print("error checking mqtt - this could be from within the functions")
            network.check_mqtt_and_reconnect()
            
    puzzle.step()
    sleep(0.01)
    

