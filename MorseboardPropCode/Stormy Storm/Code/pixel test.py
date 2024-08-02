from machine import Pin
from neopixel import NeoPixel
from utime import sleep

NEOPIXEL_PIN = 2
NUMBER_PIXELS = 100
strip = NeoPixel(Pin(NEOPIXEL_PIN), NUMBER_PIXELS, bpp=4)

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colors are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return [pos * 3, 0, 255 - pos * 3,255]

def rainbow_cycle(wait):
    global NUMBER_PIXELS, strip
    for j in range(0,255,20):
        for i in range(10):
            rc_index = (i * 255 // NUMBER_PIXELS) + j
            print(wheel(rc_index & 255))
            strip[i] = wheel(rc_index & 255)
            strip[i+10] = wheel(rc_index & 255)
            strip[i+20] = wheel(rc_index & 255)
            strip[i+30] = wheel(rc_index & 255)
            strip[i+40] = wheel(rc_index & 255)
            strip[i+50] = wheel(rc_index & 255)
            strip[i+60] = wheel(rc_index & 255)
            strip[i+70] = wheel(rc_index & 255)
            strip[i+80] = wheel(rc_index & 255)
            strip[i+90] = wheel(rc_index & 255)
        strip.write()
    

counter = 0
offset = 0
while True:
    print('Running cycle', counter)
    rainbow_cycle(0.00001)
    counter += 1
