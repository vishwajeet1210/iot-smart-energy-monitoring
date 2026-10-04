"""
Configuration module for Smart Energy Monitoring System.

Centralizes all configurable parameters including device specifications,
tariff rates, alert thresholds, and simulation parameters.
This follows the separation-of-concerns principle by isolating
configuration from business logic.
"""

import os

# ─────────────────────────────────────────────
# Database Configuration
# ─────────────────────────────────────────────
DATABASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DATABASE_PATH = os.path.join(DATABASE_DIR, "energy.db")

# ─────────────────────────────────────────────
# Electricity Tariff (INR per kWh)
# ─────────────────────────────────────────────
DEFAULT_TARIFF_RATE = 8.0  # ₹8 per kWh

# ─────────────────────────────────────────────
# Alert Thresholds
# ─────────────────────────────────────────────
HIGH_CONSUMPTION_THRESHOLD_KW = 1.20  # kW — devices above this trigger alerts

# ─────────────────────────────────────────────
# IoT Device Specifications
# ─────────────────────────────────────────────
# Each device has realistic operating ranges for voltage, current, and power.
# These ranges are used by the IoT simulator to produce plausible readings.
#
# Format:
#   "device_id": {
#       "name": str,
#       "location": str,
#       "voltage_range": (min_V, max_V),
#       "current_range": (min_A, max_A),
#       "power_range": (min_W, max_W),
#       "category": str,            # appliance category
#       "typical_hours": float,     # typical daily usage hours
#   }

DEVICE_SPECS = {
    "DEV-AC-001": {
        "name": "Air Conditioner",
        "location": "Living Room",
        "voltage_range": (220, 240),
        "current_range": (5.0, 7.5),
        "power_range": (1100, 1800),
        "category": "Cooling",
        "typical_hours": 8,
    },
    "DEV-RF-002": {
        "name": "Refrigerator",
        "location": "Kitchen",
        "voltage_range": (220, 240),
        "current_range": (0.8, 1.5),
        "power_range": (150, 350),
        "category": "Kitchen",
        "typical_hours": 24,
    },
    "DEV-WM-003": {
        "name": "Washing Machine",
        "location": "Utility Room",
        "voltage_range": (220, 240),
        "current_range": (2.0, 4.5),
        "power_range": (400, 1000),
        "category": "Laundry",
        "typical_hours": 1,
    },
    "DEV-PC-004": {
        "name": "Desktop Computer",
        "location": "Study Room",
        "voltage_range": (220, 240),
        "current_range": (1.0, 2.5),
        "power_range": (200, 600),
        "category": "Electronics",
        "typical_hours": 6,
    },
    "DEV-LT-005": {
        "name": "LED Lighting",
        "location": "Hall",
        "voltage_range": (220, 240),
        "current_range": (0.1, 0.5),
        "power_range": (20, 100),
        "category": "Lighting",
        "typical_hours": 10,
    },
    "DEV-WH-006": {
        "name": "Water Heater",
        "location": "Bathroom",
        "voltage_range": (220, 240),
        "current_range": (6.0, 9.0),
        "power_range": (1500, 2000),
        "category": "Heating",
        "typical_hours": 1,
    },
}

# ─────────────────────────────────────────────
# Simulation Parameters
# ─────────────────────────────────────────────
READING_INTERVAL_SECONDS = 300  # 5 minutes between readings (matches historical data generation)
ENERGY_CALCULATION_HOURS = READING_INTERVAL_SECONDS / 3600  # Convert interval to hours for kWh

# ─────────────────────────────────────────────
# UI Configuration
# ─────────────────────────────────────────────
APP_TITLE = "⚡ Smart Energy Monitor"
APP_ICON = "⚡"
PAGE_LAYOUT = "wide"
