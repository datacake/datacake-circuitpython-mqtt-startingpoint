import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import board
import sparkfun_qwiicrelay
import time
import neopixel
import feathers3
from adafruit_bme280 import basic as adafruit_bme280
import supervisor

# MQTT Settings
MQTT_BROKER = "mqtt.datacake.co"
MQTT_PORT = 8883
MQTT_DTCK_PRODUCT_SLUG = "circuit-python-demo"
MQTT_DTCK_ID = "yourdatacakedeviceid"
MQTT_DTCK_TOKEN = "yourdatacaketoken"
MQTT_SENDING_INTERVAL = 60 # Seconds

# Relay Settings
MQTT_DTCK_RELAY_FIELD = "RELAY_CONTROL"

# WiFi Settings
WIFI_SSID = "WIFISSID"
WIFI_PWD = "WIFIPASSWORD"

# Turn on the power to the NeoPixel
feathers3.set_ldo2_power(True)
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3, auto_write=True, pixel_order=neopixel.GRB)

# Qwiic peripherials
i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
bme280.sea_level_pressure = 1013.25
relay = sparkfun_qwiicrelay.Sparkfun_QwiicRelay(i2c)

# Setup WiFi
wifi.radio.connect(WIFI_SSID, WIFI_PWD)

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Set up a MiniMQTT Client
mqtt_client = MQTT.MQTT(
    broker=MQTT_BROKER,
    port=MQTT_PORT,
    username=MQTT_DTCK_TOKEN,
    password=MQTT_DTCK_TOKEN,
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# MQTT Routines
def parse_mqtt_message(topic, message):
    if topic == f'dtck/{MQTT_DTCK_PRODUCT_SLUG}/{MQTT_DTCK_ID}/{MQTT_DTCK_RELAY_FIELD}':
        if message == "True":
            relay.relay_on()
            pixel[0] = ( 0, 255, 0, 0.5)
        else:
            relay.relay_off()
            pixel[0] = ( 255, 0, 0, 0.5)

# MQTT library callbacks
def connect(mqtt_client, userdata, flags, rc):
    print("Connected to MQTT Broker!")
    print("Flags: {0}\n RC: {1}".format(flags, rc))

def disconnect(mqtt_client, userdata, rc):
    print("Disconnected from MQTT Broker!")

def subscribe(mqtt_client, userdata, topic, granted_qos):
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

def unsubscribe(mqtt_client, userdata, topic, pid):
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))

def publish(mqtt_client, userdata, topic, pid):
    print("Published to {0} with PID {1}".format(topic, pid))

def message(client, topic, message):
    print("New message on topic {0}: {1}".format(topic, message))
    parse_mqtt_message(topic, message)

# Connect callback handlers to mqtt_client
mqtt_client.on_connect = connect
mqtt_client.on_disconnect = disconnect
mqtt_client.on_subscribe = subscribe
mqtt_client.on_unsubscribe = unsubscribe
mqtt_client.on_publish = publish
mqtt_client.on_message = message

#print("Attempting to connect to %s" % mqtt_client.broker)
mqtt_client.connect()

# Add Relay Subscription
mqtt_client.subscribe(f'dtck/{MQTT_DTCK_PRODUCT_SLUG}/{MQTT_DTCK_ID}/{MQTT_DTCK_RELAY_FIELD}')

# Sending interval control
now = time.time()
before = 0

while True:

    # Poll the message queue
    mqtt_client.loop()

    # Check interval if sending is due
    if ((time.time() - before) > MQTT_SENDING_INTERVAL):
        
        before = time.time()

        mqtt_client.publish(f'dtck-pub/{MQTT_DTCK_PRODUCT_SLUG}/{MQTT_DTCK_ID}/TEMPERATURE', round(bme280.temperature, 2))
        mqtt_client.publish(f'dtck-pub/{MQTT_DTCK_PRODUCT_SLUG}/{MQTT_DTCK_ID}/HUMIDITY', round(bme280.relative_humidity, 2))
        mqtt_client.publish(f'dtck-pub/{MQTT_DTCK_PRODUCT_SLUG}/{MQTT_DTCK_ID}/PRESSURE', round(bme280.pressure, 2))
        mqtt_client.publish(f'dtck-pub/{MQTT_DTCK_PRODUCT_SLUG}/{MQTT_DTCK_ID}/ALTITUDE', round(bme280.altitude, 2))
        
    time.sleep(0.05)

mqtt_client.disconnect()
supervisor.reload()