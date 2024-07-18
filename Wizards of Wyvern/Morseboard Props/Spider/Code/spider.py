from neopixel import NeoPixel
from machine import UART, Pin
from time import sleep
from utime import ticks_ms
import json


class Spider:
    def __init__(self):
        self.state = self.sleeping
        self.brightness_step = 0
        self.brightness_array = list(range(10, 100)) + list(range(100, 10, -1))
        self.speed = 100
        self.shot_time = ticks_ms()
        self.colours = {
            "hunting": (255, 0, 0),
            "dormant": (0, 10, 0),
            "dying": (0, 0, 255),
        }

    def _brightness_factor(self):
        self.brightness_step += 1
        return self.brightness_array[self.brightness_step % len(self.brightness_array)] / self.speed

    def led_colour(self):
        if self.state is self.sleeping:
            return [int(x * self._brightness_factor()) for x in self.colours["dormant"]]

        if self.state is self.hunting:
            return [int(x * self._brightness_factor()) for x in self.colours["hunting"]]

        if self.state is self.dying:
            return [int(x * self._brightness_factor()) for x in self.colours["dying"]]

    def kill(self):
        spider.state = Spider.dying
        self.shot_time = ticks_ms()

    def wake(self):
        self.state = self.hunting

    def dormantify(self):
        self.state = self.sleeping

    def update(self):
        # still dying?
        if self.state == self.dying and ticks_ms() - self.shot_time > self.dying_time:
            self.state = self.sleeping

    def set_colours(self, hunting, dormant, dying):

        self.colours["hunting"] = (hunting[0], hunting[1], hunting[2])
        self.colours["dormant"] = (dormant[0], dormant[1], dormant[2])
        self.colours["dying"] = (dying[0], dying[1], dying[2])

    sleeping = "z"
    hunting = "h"
    dying = "d"
    state = sleeping
    dying_time = 3000


# load config
with open("spider_config.json") as f:
    config = json.load(f)

spider_ID = config["spider_id"]

np = NeoPixel(Pin(19), 1)
sensor = Pin(21, Pin.IN)


# Set up serial communication
# noinspection PyArgumentList
def initialise_serial():
    uart = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))
    uart.init(bits=8, parity=None, stop=2)

    return uart


# Send a message through the serial connection
def send_message(uart, message):
    msg = bytes(f"{spider_ID}{message}", 'utf8')
    print(f"sending {msg}")
    uart.write(msg)


# look at serial connection for a command and act on it
def check_for_instruction(uart):
    
    # check for uart instruction
    if uart.any():
        data = uart.read()
        decoded_data = data.decode('utf-8')
        print(decoded_data)
        # split into commands on XX
        cmds = decoded_data.split("XX")
        
        for cmd in cmds:
            # is there non-zero command length
            if len(cmd) > 0:
            
                # does this match our ID?
                if cmd[0] == spider_ID:

                    if cmd[1] == "s":  # check the spider state
                        print("sending state")
                        send_message(uart, f"{spider.state}")

                    if cmd[1] == "h":  # wake up the spider to hunt...
                        print("hunting")
                        spider.wake()
                        send_message(uart, f"{spider.state}")

                    if cmd[1] == "k":  # kill the spider - triggers dying sequence
                        print("killing")
                        spider.kill()
                        send_message(uart, f"{spider.state}")

                    if cmd[1] == "z":  # send spider instantly dormant
                        print("dormantify")
                        spider.dormantify()
                        send_message(uart, f"{spider.state}")


# initialise uart
local_uart = initialise_serial()

# initialise a spider
spider = Spider()

# set colours
spider.set_colours(config["hunt_colour"], config["dormant_colour"], config["dying_colour"])

# initialise shot time
shot_time = ticks_ms()

# set spider to dormant
spider.wake()

while True:
    # check to see for instruction
    check_for_instruction(local_uart)

    spider.update()

    np[0] = spider.led_colour()
    np.write()

    # check to see if shot
    if spider.state is Spider.hunting:
        s = sensor.value()
        if s < 1:
            spider.kill()

    sleep(0.01)
        
    
