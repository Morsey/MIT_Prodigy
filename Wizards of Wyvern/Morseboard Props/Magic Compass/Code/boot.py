from time import sleep
from machine import Pin


if False:  ## Easy bypass when debugging
    try:
        
        LED = Pin(25, Pin.OUT)
        
        # Emergency connection buffer time
        emergency_timeout = 5
        for i in range(0,emergency_timeout):
            sleep(0.2)
            LED.on()
            sleep(0.2)
            LED.off()
            print(f"Waiting for emergency connection {emergency_timeout - i}")


        import MagicCompassV2
        
    except:
        
            for i in range(0,emergency_timeout):
                for p in range(0,10):
                    sleep(0.05)
                    LED.on()
                    sleep(0.05)
                    LED.off()
                print(f"Crashing {emergency_timeout - i}")

            machine.reset()
    
