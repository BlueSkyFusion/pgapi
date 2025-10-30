"""
mqtt_subscriber.py

Created on: 2025-10-30
Edited on: 2025-10-30
Author: R. Andrew Ballard (c) 2025 "Andwardo"
Version: v1.0.0

MQTT Subscriber Service for PianoGuard Telemetry
Subscribes to MQTT broker and stores telemetry data in PostgreSQL database
"""

import asyncio
import json
import logging
import signal
import ssl
import sys
from typing import Dict, Any, Optional
from datetime import datetime

import asyncpg
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
from dotenv import load_dotenv

from env import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/mqtt-subscriber.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883  # Using non-TLS port for testing
MQTT_TOPIC = "pianoguard/+/telemetry"
MQTT_CA_CERT = "/etc/mosquitto/mosquitto.crt"
MQTT_USERNAME = "dcm_client"
MQTT_PASSWORD = "secure_mqtt_pass"
USE_TLS = False  # Disable TLS for testing

# Global database pool and event loop
db_pool: Optional[asyncpg.Pool] = None
mqtt_client: Optional[mqtt.Client] = None
event_loop: Optional[asyncio.AbstractEventLoop] = None
running = True


async def init_db_pool():
    """Initialize asyncpg connection pool"""
    global db_pool

    try:
        db_pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=int(DB_PORT),
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise


async def close_db_pool():
    """Close asyncpg connection pool"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")


async def store_telemetry(data: Dict[str, Any]) -> None:
    """Store telemetry data in PostgreSQL database"""
    if not db_pool:
        logger.error("Database pool not initialized")
        return

    try:
        async with db_pool.acquire() as conn:
            # Upsert device info with online status
            await conn.execute("""
                INSERT INTO "Devices" (device_id, last_seen, "createdAt", "updatedAt")
                VALUES ($1, to_timestamp($2), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (device_id)
                DO UPDATE SET
                    last_seen = EXCLUDED.last_seen,
                    "updatedAt" = CURRENT_TIMESTAMP
            """,
                data.get("device_id"),
                data.get("timestamp")
            )

            # Insert telemetry data
            await conn.execute("""
                INSERT INTO "TelemetryData" (
                    device_id, timestamp, fw_version, wifi_ssid, wifi_rssi,
                    uptime_ms, free_heap, battery_voltage,
                    led_power, led_water, led_pads,
                    "createdAt", "updatedAt"
                )
                VALUES ($1, to_timestamp($2), $3, $4, $5, $6, $7, $8, $9, $10, $11, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
                data.get("device_id"),
                data.get("timestamp"),
                data.get("fw_version"),
                data.get("wifi_ssid"),
                data.get("wifi_rssi"),
                data.get("uptime_ms"),
                data.get("free_heap"),
                data.get("battery_voltage"),
                data.get("status", {}).get("power") if isinstance(data.get("status"), dict) else False,
                data.get("status", {}).get("water") if isinstance(data.get("status"), dict) else False,
                data.get("status", {}).get("pads") if isinstance(data.get("status"), dict) else False
            )

            logger.info(f"Stored telemetry for device {data.get('device_id')}")

    except Exception as e:
        logger.error(f"Failed to store telemetry: {e}")


def on_connect(client, userdata, flags, reason_code, properties):
    """MQTT connection callback (API v2)"""
    if reason_code == 0:
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        logger.info(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        logger.error(f"Failed to connect to MQTT broker, reason code: {reason_code}")


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    """MQTT disconnection callback (API v2)"""
    if reason_code != 0:
        logger.warning(f"Unexpected disconnection from MQTT broker, reason code: {reason_code}")
    else:
        logger.info("Disconnected from MQTT broker")


def on_message(client, userdata, msg):
    """MQTT message callback"""
    try:
        # Parse JSON payload
        payload = json.loads(msg.payload.decode())
        logger.debug(f"Received message on topic {msg.topic}: {payload}")

        # Validate required fields
        required_fields = ["device_id", "timestamp"]
        if not all(field in payload for field in required_fields):
            logger.warning(f"Missing required fields in payload: {payload}")
            return

        # Store telemetry asynchronously from MQTT thread
        if event_loop:
            asyncio.run_coroutine_threadsafe(store_telemetry(payload), event_loop)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON payload: {e}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


def setup_mqtt_client() -> mqtt.Client:
    """Setup and configure MQTT client"""
    # Use CallbackAPIVersion.VERSION2 to fix deprecation warning
    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        client_id="pianoguard_subscriber",
        clean_session=True
    )

    # Set callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Configure TLS if enabled
    if USE_TLS:
        try:
            client.tls_set(
                ca_certs=MQTT_CA_CERT,  # Use server cert as CA for self-signed
                certfile=None,
                keyfile=None,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLSv1_2,
                ciphers=None
            )
            client.tls_insecure_set(True)  # Skip hostname verification
            logger.info(f"TLS configured with self-signed cert: {MQTT_CA_CERT}")
        except Exception as e:
            logger.error(f"Failed to configure TLS: {e}")
            raise
    else:
        logger.info("TLS disabled - connecting without encryption")

    # Set authentication (optional since allow_anonymous=true in Mosquitto)
    # Uncomment if you configure authentication in Mosquitto
    # client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    return client


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    running = False


async def main():
    """Main event loop"""
    global mqtt_client, running, event_loop

    # Store event loop reference for MQTT callbacks
    event_loop = asyncio.get_running_loop()

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting PianoGuard MQTT Subscriber Service")

    try:
        # Initialize database connection pool
        await init_db_pool()

        # Setup MQTT client
        mqtt_client = setup_mqtt_client()

        # Connect to MQTT broker
        logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

        # Start MQTT loop in separate thread
        mqtt_client.loop_start()

        # Keep service running
        while running:
            await asyncio.sleep(1)

        logger.info("Shutting down service...")

        # Cleanup
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            logger.info("MQTT client disconnected")

        await close_db_pool()

    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
        raise
    finally:
        logger.info("PianoGuard MQTT Subscriber Service stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service crashed: {e}")
        sys.exit(1)
