"""
data.py

Data API routes - serves sensor data from database (populated by MQTT subscriber)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import asyncpg
from env import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD
)

router = APIRouter(prefix="/api/data", tags=["data"])

# Global connection pool
db_pool: Optional[asyncpg.Pool] = None


# Pydantic response models
class StatusDict(BaseModel):
    power: bool
    water: bool
    pads: bool


class TelemetryResponse(BaseModel):
    device_id: str
    timestamp: int
    fw_version: str
    wifi_ssid: str
    wifi_rssi: int
    uptime_ms: int
    free_heap: int
    battery_voltage: float
    status: StatusDict


class HistoryResponse(BaseModel):
    data: List[TelemetryResponse]
    total_records: int


class DeviceInfo(BaseModel):
    device_id: str
    last_seen: Optional[int] = None
    fw_version: Optional[str] = None


async def init_db_pool():
    """Initialize asyncpg connection pool"""
    global db_pool

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

    # Create tables if they don't exist
    await create_tables()


async def close_db_pool():
    """Close asyncpg connection pool"""
    global db_pool
    if db_pool:
        await db_pool.close()


async def create_tables():
    """Create database tables with proper schema"""
    if not db_pool:
        raise RuntimeError("Database pool not initialized")

    async with db_pool.acquire() as conn:
        # Create Devices table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS "Devices" (
                device_id VARCHAR(255) PRIMARY KEY,
                last_seen BIGINT,
                fw_version VARCHAR(50),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create TelemetryData table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS "TelemetryData" (
                id SERIAL PRIMARY KEY,
                device_id VARCHAR(255) NOT NULL,
                timestamp BIGINT NOT NULL,
                fw_version VARCHAR(50),
                wifi_ssid VARCHAR(255),
                wifi_rssi INTEGER,
                uptime_ms BIGINT,
                free_heap INTEGER,
                battery_voltage FLOAT,
                led_power BOOLEAN,
                led_water BOOLEAN,
                led_pads BOOLEAN,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES "Devices" (device_id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp
            ON "TelemetryData" (timestamp DESC)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_device_id
            ON "TelemetryData" (device_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_device_timestamp
            ON "TelemetryData" (device_id, timestamp DESC)
        """)


@router.get("/latest", response_model=TelemetryResponse)
async def get_latest_data(device_id: Optional[str] = Query(None, description="Filter by device ID")):
    """Get latest sensor data, optionally filtered by device_id"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")

    async with db_pool.acquire() as conn:
        if device_id:
            row = await conn.fetchrow("""
                SELECT device_id, timestamp, fw_version, wifi_ssid, wifi_rssi,
                       uptime_ms, free_heap, battery_voltage,
                       led_power, led_water, led_pads
                FROM "TelemetryData"
                WHERE device_id = $1
                ORDER BY timestamp DESC
                LIMIT 1
            """, device_id)
        else:
            row = await conn.fetchrow("""
                SELECT device_id, timestamp, fw_version, wifi_ssid, wifi_rssi,
                       uptime_ms, free_heap, battery_voltage,
                       led_power, led_water, led_pads
                FROM "TelemetryData"
                ORDER BY timestamp DESC
                LIMIT 1
            """)

        if not row:
            raise HTTPException(status_code=404, detail="No telemetry data found")

        return TelemetryResponse(
            device_id=row["device_id"],
            timestamp=row["timestamp"],
            fw_version=row["fw_version"] or "",
            wifi_ssid=row["wifi_ssid"] or "",
            wifi_rssi=row["wifi_rssi"] or 0,
            uptime_ms=row["uptime_ms"] or 0,
            free_heap=row["free_heap"] or 0,
            battery_voltage=row["battery_voltage"] or 0.0,
            status=StatusDict(
                power=row["led_power"] or False,
                water=row["led_water"] or False,
                pads=row["led_pads"] or False
            )
        )


@router.get("/history", response_model=HistoryResponse)
async def get_data_history(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
):
    """Get historical sensor data, optionally filtered by device_id"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")

    async with db_pool.acquire() as conn:
        # Get total count
        if device_id:
            total_count = await conn.fetchval(
                'SELECT COUNT(*) FROM "TelemetryData" WHERE device_id = $1',
                device_id
            )
        else:
            total_count = await conn.fetchval('SELECT COUNT(*) FROM "TelemetryData"')

        # Get limited historical data ordered by timestamp descending
        if device_id:
            rows = await conn.fetch("""
                SELECT device_id, timestamp, fw_version, wifi_ssid, wifi_rssi,
                       uptime_ms, free_heap, battery_voltage,
                       led_power, led_water, led_pads
                FROM "TelemetryData"
                WHERE device_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """, device_id, limit)
        else:
            rows = await conn.fetch("""
                SELECT device_id, timestamp, fw_version, wifi_ssid, wifi_rssi,
                       uptime_ms, free_heap, battery_voltage,
                       led_power, led_water, led_pads
                FROM "TelemetryData"
                ORDER BY timestamp DESC
                LIMIT $1
            """, limit)

        telemetry_data = [
            TelemetryResponse(
                device_id=row["device_id"],
                timestamp=row["timestamp"],
                fw_version=row["fw_version"] or "",
                wifi_ssid=row["wifi_ssid"] or "",
                wifi_rssi=row["wifi_rssi"] or 0,
                uptime_ms=row["uptime_ms"] or 0,
                free_heap=row["free_heap"] or 0,
                battery_voltage=row["battery_voltage"] or 0.0,
                status=StatusDict(
                    power=row["led_power"] or False,
                    water=row["led_water"] or False,
                    pads=row["led_pads"] or False
                )
            )
            for row in rows
        ]

        return HistoryResponse(data=telemetry_data, total_records=total_count)


@router.get("/devices", response_model=List[DeviceInfo])
async def get_devices():
    """Get list of all registered devices"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT device_id, last_seen, fw_version
            FROM "Devices"
            ORDER BY last_seen DESC NULLS LAST
        """)

        return [
            DeviceInfo(
                device_id=row["device_id"],
                last_seen=row["last_seen"],
                fw_version=row["fw_version"]
            )
            for row in rows
        ]


# Internal function for MQTT subscriber to store data
async def store_sensor_data(data: Dict[str, Any]) -> None:
    """Store sensor data from MQTT (internal use only)"""
    if not db_pool:
        raise RuntimeError("Database pool not initialized")

    async with db_pool.acquire() as conn:
        # Upsert device info
        await conn.execute("""
            INSERT INTO "Devices" (device_id, last_seen, fw_version)
            VALUES ($1, $2, $3)
            ON CONFLICT (device_id)
            DO UPDATE SET
                last_seen = EXCLUDED.last_seen,
                fw_version = EXCLUDED.fw_version,
                updated_at = CURRENT_TIMESTAMP
        """,
            data.get("device_id"),
            data.get("timestamp"),
            data.get("fw_version")
        )

        # Insert telemetry data
        await conn.execute("""
            INSERT INTO "TelemetryData" (
                device_id, timestamp, fw_version, wifi_ssid, wifi_rssi,
                uptime_ms, free_heap, battery_voltage,
                led_power, led_water, led_pads
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
            data.get("device_id"),
            data.get("timestamp"),
            data.get("fw_version"),
            data.get("wifi_ssid"),
            data.get("wifi_rssi"),
            data.get("uptime_ms"),
            data.get("free_heap"),
            data.get("battery_voltage"),
            data.get("status", {}).get("power") if isinstance(data.get("status"), dict) else data.get("led_power"),
            data.get("status", {}).get("water") if isinstance(data.get("status"), dict) else data.get("led_water"),
            data.get("status", {}).get("pads") if isinstance(data.get("status"), dict) else data.get("led_pads")
        )
