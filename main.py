import time
import json
import network
import dht
import machine
from umqtt.simple import MQTTClient

# Configuration 
WIFI_SSID     = "Talamson"   # Wokwi's built-in WiFi AP
WIFI_PASSWORD = "0792314330"               # No password in Wokwi

MQTT_BROKER   = "172.20.10.2"
MQTT_PORT     = 1883
MQTT_TOPIC    = b"iot/lab/sensor"
MQTT_CLIENT_ID = "Group_6"

DHT_PIN       = 4                # GPIO 4 
READ_INTERVAL = 5                # seconds between readings
# 

sensor = dht.DHT22(machine.Pin(DHT_PIN))


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    
    # Full reset of WiFi radio
    wlan.active(False)
    time.sleep(1)
    wlan.active(True)
    time.sleep(1)
    
    if not wlan.isconnected():
        print(f"[WiFi] Connecting to '{WIFI_SSID}' ...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 15
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(f"  Waiting... {timeout}s left")
        print()
    if wlan.isconnected():
        print("[WiFi] Connected! IP:", wlan.ifconfig()[0])
    else:
        raise RuntimeError("[WiFi] Failed – check SSID/password")
    return wlan


def connect_mqtt():
    """Connect to MQTT broker and return the client."""
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
    client.connect()
    print(f"[MQTT] Connected to {MQTT_BROKER}:{MQTT_PORT}")
    return client


def read_sensor():
    """Read DHT22 and return (temperature_C, humidity_percent)."""
    sensor.measure()
    return sensor.temperature(), sensor.humidity()


def build_payload(temperature, humidity, reading_id):
    """Build a JSON payload string."""
    payload = {
        "device_id": MQTT_CLIENT_ID,
        "reading_id": reading_id,
        "temperature": temperature,
        "humidity": humidity,
        "unit_temp": "C",
        "unit_humidity": "%"
    }
    return json.dumps(payload)


# Main 
def main():
    # 1. Connect WiFi
    connect_wifi()

    # 2. Connect MQTT
    client = connect_mqtt()

    print(f"\n[Sensor] Starting readings on GPIO {DHT_PIN} every {READ_INTERVAL}s")
    print(f"[MQTT]   Publishing to topic: {MQTT_TOPIC.decode()}\n")

    reading_id = 1

    while True:
        try:
            temp, hum = read_sensor()
            payload = build_payload(temp, hum, reading_id)

            client.publish(MQTT_TOPIC, payload)

            print(f"[{reading_id:03d}] Published → {payload}")
            reading_id += 1

        except OSError as e:
            print(f"[ERROR] Sensor read failed: {e}")

        time.sleep(READ_INTERVAL)


main()