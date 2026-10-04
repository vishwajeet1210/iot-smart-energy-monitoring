"""
IoT Sensor Simulation Layer for Smart Energy Monitoring System.

Simulates realistic energy sensor readings from household IoT devices.
Each simulated reading includes voltage, current, power, and energy values
within manufacturer-specified operating ranges for each appliance type.

The simulator uses Gaussian noise around typical operating points
to produce realistic, non-random data patterns.
"""

import random
from datetime import datetime, timedelta
from typing import Optional

from config import (
    DEVICE_SPECS,
    HIGH_CONSUMPTION_THRESHOLD_KW,
    READING_INTERVAL_SECONDS,
)


def generate_single_reading(
    device_id: str,
    timestamp: Optional[str] = None,
) -> dict:
    """
    Generate a single realistic sensor reading for a given device.

    The simulation applies Gaussian noise to the midpoint of each device's
    operating range to produce realistic fluctuations.

    Args:
        device_id: The unique identifier of the device from DEVICE_SPECS.
        timestamp: Optional ISO-format timestamp. Defaults to now.

    Returns:
        A dictionary containing all reading fields ready for DB insertion.

    Raises:
        ValueError: If device_id is not found in DEVICE_SPECS.
    """
    if device_id not in DEVICE_SPECS:
        raise ValueError(f"Unknown device ID: {device_id}")

    spec = DEVICE_SPECS[device_id]

    # Generate voltage with realistic grid fluctuation (±2%)
    v_min, v_max = spec["voltage_range"]
    voltage = round(random.uniform(v_min, v_max), 1)

    # Generate current within device operating range
    c_min, c_max = spec["current_range"]
    midpoint = (c_min + c_max) / 2
    std_dev = (c_max - c_min) / 6  # ~99.7% within range
    current = round(max(c_min, min(c_max, random.gauss(midpoint, std_dev))), 2)

    # Calculate power (P = V × I) and clamp to spec range
    power_raw = voltage * current
    p_min, p_max = spec["power_range"]
    power_w = round(max(p_min, min(p_max, power_raw)), 1)

    # Calculate energy for this reading interval (kWh)
    # energy = power (kW) × time (hours)
    energy_kwh = round(
        (power_w / 1000) * (READING_INTERVAL_SECONDS / 3600), 6
    )

    # Determine device status based on consumption threshold
    power_kw = power_w / 1000
    if power_kw >= HIGH_CONSUMPTION_THRESHOLD_KW:
        status = "High"
    elif power_kw >= HIGH_CONSUMPTION_THRESHOLD_KW * 0.75:
        status = "Warning"
    else:
        status = "Normal"

    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "device_id": device_id,
        "device_name": spec["name"],
        "location": spec["location"],
        "category": spec["category"],
        "voltage": voltage,
        "current": current,
        "power_w": power_w,
        "energy_kwh": energy_kwh,
        "status": status,
        "timestamp": timestamp,
    }


def generate_all_readings(
    timestamp: Optional[str] = None,
) -> list[dict]:
    """
    Generate one reading for every registered device.

    Args:
        timestamp: Shared timestamp for the reading batch.

    Returns:
        A list of reading dictionaries.
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    readings = []
    for device_id in DEVICE_SPECS:
        reading = generate_single_reading(device_id, timestamp)
        readings.append(reading)

    return readings


def generate_historical_data(hours: int = 2, interval_minutes: int = 5) -> list[dict]:
    """
    Generate historical sensor data for initial dashboard population.

    Creates realistic time-series data stretching back `hours` from now,
    with readings every `interval_minutes`.

    Args:
        hours: Number of hours of historical data to generate.
        interval_minutes: Minutes between each reading batch.

    Returns:
        A list of reading dictionaries sorted chronologically.
    """
    readings = []
    now = datetime.now()
    start_time = now - timedelta(hours=hours)
    current_time = start_time

    while current_time <= now:
        ts = current_time.strftime("%Y-%m-%d %H:%M:%S")
        batch = generate_all_readings(timestamp=ts)
        readings.extend(batch)
        current_time += timedelta(minutes=interval_minutes)

    return readings


def get_device_info(device_id: str) -> dict:
    """
    Retrieve the specification/metadata for a device.

    Args:
        device_id: The unique identifier of the device.

    Returns:
        A copy of the device specification dictionary.

    Raises:
        ValueError: If device_id is not found.
    """
    if device_id not in DEVICE_SPECS:
        raise ValueError(f"Unknown device ID: {device_id}")
    return dict(DEVICE_SPECS[device_id])


def get_all_device_ids() -> list[str]:
    """Return a list of all registered device IDs."""
    return list(DEVICE_SPECS.keys())
