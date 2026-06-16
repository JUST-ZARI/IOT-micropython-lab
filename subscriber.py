#!/usr/bin/env python3
"""
ICS 4111 – PC-Side MQTT Subscriber & SQLite Logger
===================================================
Run this on your PC BEFORE starting the Wokwi simulation.

Install dependencies:
    pip install paho-mqtt

Usage:
    python subscriber.py

It will:
  1. Connect to broker.hivemq.com
  2. Subscribe to iot/lab/sensor
  3. Print every incoming JSON message
  4. Store each reading in sensor_data.db (SQLite)
  5. Keep a count – the lab requires at least 10 messages received

After receiving readings, query the database:
    python subscriber.py --query
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("ERROR: paho-mqtt not installed. Run:  pip install paho-mqtt")
    sys.exit(1)

# Configuration
MQTT_BROKER   = "172.20.10.2"
MQTT_PORT     = 1883
MQTT_TOPIC    = "iot/lab/sensor"
DB_FILE       = "sensor_data.db"
TARGET_COUNT  = 10   # requires ≥ 10 messages
# 

message_count = 0


# Database
def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id   TEXT,
            reading_id  INTEGER,
            temperature REAL,
            humidity    REAL,
            received_at TEXT
        )
    """)
    conn.commit()
    print(f"[DB] Database '{DB_FILE}' ready.")


def store_reading(conn, data, timestamp):
    conn.execute("""
        INSERT INTO sensor_readings
            (device_id, reading_id, temperature, humidity, received_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data.get("device_id", "unknown"),
        data.get("reading_id", -1),
        data.get("temperature"),
        data.get("humidity"),
        timestamp
    ))
    conn.commit()


def query_db():
    """Print all stored readings – use for lab screenshot."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.execute(
        "SELECT id, device_id, reading_id, temperature, humidity, received_at "
        "FROM sensor_readings ORDER BY id"
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No readings stored yet.")
        return

    print(f"\n{'ID':<5} {'Device':<25} {'#':<6} {'Temp(°C)':<12} {'Humidity(%)':<14} {'Received At'}")
    print("-" * 80)
    for row in rows:
        print(f"{row[0]:<5} {row[1]:<25} {row[2]:<6} {row[3]:<12} {row[4]:<14} {row[5]}")
    print(f"\nTotal rows: {len(rows)}")


# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT] Connected to {MQTT_BROKER}")
        client.subscribe(MQTT_TOPIC)
        print(f"[MQTT] Subscribed to topic: {MQTT_TOPIC}")
        print(f"[MQTT] Waiting for {TARGET_COUNT}+ messages...\n")
    else:
        print(f"[MQTT] Connection failed with code {rc}")
        sys.exit(1)


def on_message(client, userdata, msg):
    global message_count
    db_conn = userdata["db"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        payload_str = msg.payload.decode("utf-8")
        data = json.loads(payload_str)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"[WARN] Could not parse message: {e}")
        return

    message_count += 1
    store_reading(db_conn, data, timestamp)

    print(
        f"[{message_count:03d}] {timestamp} | "
        f"Temp: {data.get('temperature')}°C | "
        f"Humidity: {data.get('humidity')}% | "
        f"Device: {data.get('device_id')}"
    )

    if message_count == TARGET_COUNT:
        print(f"\n {TARGET_COUNT} messages received.")


# Main 
def main():
    parser = argparse.ArgumentParser(description="MQTT Subscriber + SQLite Logger")
    parser.add_argument("--query", action="store_true",
                        help="Print stored readings from SQLite and exit")
    args = parser.parse_args()

    if args.query:
        query_db()
        return

    db_conn = sqlite3.connect(DB_FILE)
    init_db(db_conn)

    client = mqtt.Client(userdata={"db": db_conn})
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[MQTT] Connecting to {MQTT_BROKER}:{MQTT_PORT} ...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"\n[INFO] Stopped. {message_count} messages received total.")
        db_conn.close()


if __name__ == "__main__":
    main()
