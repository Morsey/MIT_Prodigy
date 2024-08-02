from machine import Pin
import utime
 
class Stepper:
    def __init__(self, step_pin, dir_pin):
        self.step_pin = Pin(step_pin, Pin.OUT)
        self.dir_pin = Pin(dir_pin, Pin.OUT)
        self.position = 0
 
    def set_speed(self, speed):
        self.delay = 1 / abs(speed)  # delay in seconds
 
    def set_direction(self, direction):
        self.dir_pin.value(direction)
 
    def move_to(self, position):
        self.set_direction(1 if position > self.position else 0)
        while self.position != position:
            self.step_pin.value(1)
            utime.sleep(self.delay)
            self.step_pin.value(0)
            self.position += 1 if position > self.position else -1