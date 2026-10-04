"""
Database Layer for Smart Energy Monitoring System.

Handles all SQLite interactions including:
- Schema creation and migration
- Device registration
- Sensor reading storage and retrieval
- Aggregation queries for analytics

Uses parameterized queries to prevent SQL injection.
Follows the Repository pattern for clean data access.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional

import pandas as pd

from config import DATABASE_PATH, DATABASE_DIR, DEVICE_SPECS


def _get_connection() -> sqlite3.Connection:
    """Create and return a database connection with row factory enabled."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent read performance
    conn.execute("PRAGMA foreign_keys=ON")   # Enforce referential integrity
    return conn


def initialize_database() -> None:
    """
    Create the database schema if it doesn't exist.

    Tables:
      - devices: Master list of IoT energy sensors/devices.
      - readings: Time-series sensor readings linked to devices.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        # ── Devices table ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id   TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                location    TEXT NOT NULL,
                category    TEXT NOT NULL,
                status      TEXT DEFAULT 'Online',
                created_at  TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # ── Readings table ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id   TEXT NOT NULL,
                voltage     REAL NOT NULL,
                current     REAL NOT NULL,
                power_w     REAL NOT NULL,
                energy_kwh  REAL NOT NULL,
                status      TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                FOREIGN KEY (device_id) REFERENCES devices(device_id)
            )
        """)

        # ── Index for faster time-range queries ──
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_timestamp
            ON readings(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_device
            ON readings(device_id)
        """)

        conn.commit()

        # ── Seed devices from config ──
        _seed_devices(conn)

    finally:
        conn.close()


def _seed_devices(conn: sqlite3.Connection) -> None:
    """Insert configured devices if they don't already exist."""
    cursor = conn.cursor()
    for device_id, spec in DEVICE_SPECS.items():
        cursor.execute(
            """
            INSERT OR IGNORE INTO devices (device_id, name, location, category)
            VALUES (?, ?, ?, ?)
            """,
            (device_id, spec["name"], spec["location"], spec["category"]),
        )
    conn.commit()


# ─────────────────────────────────────────────
# Write Operations
# ─────────────────────────────────────────────

def insert_reading(
    device_id: str,
    voltage: float,
    current: float,
    power_w: float,
    energy_kwh: float,
    status: str,
    timestamp: Optional[str] = None,
) -> int:
    """
    Insert a single sensor reading into the database.

    Args:
        device_id: The unique identifier of the device.
        voltage: Measured voltage in Volts.
        current: Measured current in Amps.
        power_w: Calculated power in Watts.
        energy_kwh: Calculated energy in kWh.
        status: Device status ('Normal', 'High', 'Warning').
        timestamp: ISO-format timestamp. Defaults to current time.

    Returns:
        The row ID of the inserted reading.

    Raises:
        sqlite3.IntegrityError: If device_id does not exist.
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO readings (device_id, voltage, current, power_w, energy_kwh, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (device_id, voltage, current, power_w, energy_kwh, status, timestamp),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def insert_readings_batch(readings: list[dict]) -> int:
    """
    Insert multiple sensor readings in a single transaction.

    Args:
        readings: List of dicts with keys matching insert_reading params.

    Returns:
        Number of rows inserted.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO readings (device_id, voltage, current, power_w, energy_kwh, status, timestamp)
            VALUES (:device_id, :voltage, :current, :power_w, :energy_kwh, :status, :timestamp)
            """,
            readings,
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


# ─────────────────────────────────────────────
# Read Operations
# ─────────────────────────────────────────────

def get_all_devices() -> pd.DataFrame:
    """Retrieve all registered devices as a DataFrame."""
    conn = _get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM devices ORDER BY name", conn)
        return df
    finally:
        conn.close()


def get_latest_readings() -> pd.DataFrame:
    """
    Get the most recent reading for each device.

    Uses a window function to efficiently find the latest reading per device,
    then joins with the devices table for device metadata.
    """
    query = """
        SELECT
            d.device_id,
            d.name AS device_name,
            d.location,
            d.category,
            r.voltage,
            r.current,
            r.power_w,
            r.energy_kwh,
            r.status,
            r.timestamp
        FROM devices d
        LEFT JOIN (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY timestamp DESC) AS rn
            FROM readings
        ) r ON d.device_id = r.device_id AND r.rn = 1
        ORDER BY r.power_w DESC
    """
    conn = _get_connection()
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def get_all_readings(limit: int = 1000) -> pd.DataFrame:
    """
    Retrieve readings with device metadata, ordered by timestamp descending.

    Args:
        limit: Maximum number of readings to return.
    """
    query = """
        SELECT
            r.id,
            d.name AS device_name,
            d.location,
            d.category,
            r.voltage,
            r.current,
            r.power_w,
            r.energy_kwh,
            r.status,
            r.timestamp
        FROM readings r
        JOIN devices d ON r.device_id = d.device_id
        ORDER BY r.timestamp DESC
        LIMIT ?
    """
    conn = _get_connection()
    try:
        return pd.read_sql_query(query, conn, params=(limit,))
    finally:
        conn.close()


def get_readings_for_analytics() -> pd.DataFrame:
    """
    Retrieve all readings with device info for analytics processing.
    Returns data sorted chronologically for time-series charts.
    """
    query = """
        SELECT
            r.id,
            r.device_id,
            d.name AS device_name,
            d.location,
            d.category,
            r.voltage,
            r.current,
            r.power_w,
            r.energy_kwh,
            r.status,
            r.timestamp
        FROM readings r
        JOIN devices d ON r.device_id = d.device_id
        ORDER BY r.timestamp ASC
    """
    conn = _get_connection()
    try:
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    finally:
        conn.close()


def get_total_energy_kwh() -> float:
    """Calculate total energy consumed across all devices."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(energy_kwh), 0) FROM readings")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def get_reading_count() -> int:
    """Get the total number of stored readings."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM readings")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def clear_all_readings() -> int:
    """Delete all readings. Returns number of rows deleted."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM readings")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
