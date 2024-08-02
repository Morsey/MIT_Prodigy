from machine import Pin, SPI, SoftI2C
import network
import time
import usocket


# W5x00 chip init
def w5x00_init():
    spi = SPI(0,2_000_000, mosi=Pin(19),miso=Pin(16),sck=Pin(18))
    nic = network.WIZNET5K(spi,Pin(17),Pin(20)) #spi,cs,reset pin
    nic.active(True)
    
    # None DHCP
    # nic.ifconfig(('192.168.0.18','255.255.255.0','192.168.0.1','8.8.8.8'))

    connection_timeout = 0

    while not nic.isconnected():
        time.sleep(0.5)
        print("connecting ... ")
        connection_timeout += 1
        if connection_timeout > 20:
            return False, False
        
    
    # DHCP
    print('IP address :', nic.ifconfig())
    
    return nic.ifconfig(), nic


def get_ip(host = 'mi-postoffice.lan'):
    return usocket.getaddrinfo(host, 80, 0, usocket.SOCK_STREAM)[0][4][0]