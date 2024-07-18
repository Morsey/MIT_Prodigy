from machine import Pin, SPI, SoftI2C
import network
from time import sleep, ticks_ms
import usocket
from libs.simple_mqtt import MQTTClient
import json


# Networking class to manage the network connection, including connection to MQTT broker
# includes functions to test if network alive and reconnect as needed
# LED double pulse means disconnected (0.1 on, 0.1 off, 0.1 on, 0.7 off)
class MINetwork:

    class Statuses:
        connected = "connected"
        unknown = "unknown"
        disconnected = "disconnected"

    def __init__(self, network_type="dhcp"):

        # SPI connection: pins and settings defined by the W5500 board
        self.spi = SPI(0, 2_000_000, mosi=Pin(19), miso=Pin(16), sck=Pin(18))

        # Network connection
        self.nic = network.WIZNET5K(self.spi, Pin(17), Pin(20))  # spi,cs,reset pin

        # if not using DHCP
        # nic.ifconfig(('192.168.0.18','255.255.255.0','192.168.0.1','8.8.8.8'))

        self.status = self.Statuses.unknown

        self.mqtt_server = None
        self.mqtt_connection = None
        self.mqtt_topic = None
        self.mqtt_client = None
        
        self.indicator_led = Pin(25, Pin.OUT)

        self.subscription_list = {}

    def connect_to_network(self, connection_timeout=10):
        self.nic.active(True)

        start_time = ticks_ms()
        while not self.nic.isconnected() and (ticks_ms() - start_time) < (connection_timeout * 1000):
            sleep(0.5)
            print(f"attempting connecting ...")

        if self.nic.isconnected():
            self.status = self.Statuses.connected
            print('IP address :', self.nic.ifconfig())

        else:
            self.status = self.Statuses.disconnected
            return False

    # resolve IP given hostname - this doesn't always work...
    @staticmethod
    def resolve_ip(host):
        return usocket.getaddrinfo(host, 80, 0, usocket.SOCK_STREAM)[0][4][0]

    # Check the status of the network connection
    def check_status_network_connection(self):
        return self.nic.isconnected()
    
    # Check the mqtt connection status
    def check_status_mqtt_connection(self, timeout=2):
        
        start_time = ticks_ms()
        
        try:
            self.mqtt_connection.ping()
            pong_recieved = False
            while ticks_ms() - start_time < timeout * 1000 and not pong_recieved:
                response = self.mqtt_connection.check_msg()
                
                if response == "pong":
                    pong_recieved = True
                 
            if pong_recieved:
                
                print("miNetwork: mqtt pong recieved")
                return True
            else:
                
                print("miNetwork: no pong within timeout")
                return False
                
        
        except:
            print("miNetwork: mqtt down")
            return False

    # Connect to an mqtt broker
    def connect_to_mqtt_broker(self, client_id, broker_address):
        self.mqtt_client = client_id
        self.mqtt_server = broker_address
        try:
            self.mqtt_connection = MQTTClient(self.mqtt_client, self.mqtt_server)
            
            self.mqtt_connection.connect()
            return True
        except:
            print("miNetwork: error connecting to mqtt server")
            return False

    # check and re-instate mqtt connection
    def check_mqtt_and_reconnect(self):
        while not self.check_status_mqtt_connection():
            
            # show status showing we have lost mqtt
            self.indicator_led.on()
            sleep(0.1)
            self.indicator_led.off()
            sleep(0.1)
            self.indicator_led.on()
            sleep(0.1)
            self.indicator_led.off()
            sleep(0.7)

            if self.connect_to_mqtt_broker(self.mqtt_client, self.mqtt_server):
                self.resubscribe_to_all()
        return True
            
        
    # Send a string mqtt message
    def send_mqtt_message(self, topic, message):
        self.mqtt_connection.publish(topic, message)
        
    # Send a json mqtt message
    def send_mqtt_json(self, topic, json_):
        self.mqtt_connection.publish(topic, json.dumps(json_))
        
    # Subscribe to a topic and set callback
    def subscribe_to_topic(self, topic, callback):
        self.mqtt_connection.set_callback(callback)
        self.mqtt_connection.subscribe(topic)
        self.subscription_list[topic] = callback
       
    # resubscribe to all in list   
    def resubscribe_to_all(self):
        for topic, callback in self.subscription_list.items():
            print(f"miNetwork: resubscribing to {topic} with {callback}")
            self.subscribe_to_topic(topic, callback)
        
    # Check for any messages waiting - non-blocking
    def check_for_messages(self):
        return self.mqtt_connection.check_msg()



