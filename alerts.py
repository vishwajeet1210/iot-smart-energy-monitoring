"""
Alert and Recommendation Engine for Smart Energy Monitoring System.

Provides two key functions:
1. High-consumption alerts — flags devices exceeding the configured threshold.
2. Energy-saving recommendations — generates dynamic, context-aware tips
   based on actual consumption patterns.
"""

import pandas as pd

from config import HIGH_CONSUMPTION_THRESHOLD_KW, DEVICE_SPECS


# ─────────────────────────────────────────────
# Alert Generation
# ─────────────────────────────────────────────

def check_high_consumption(
    latest_readings: pd.DataFrame,
    threshold_kw: float = HIGH_CONSUMPTION_THRESHOLD_KW,
) -> list[dict]:
    """
    Identify devices whose current power consumption exceeds the threshold.

    Args:
        latest_readings: DataFrame with most recent reading per device.
            Must contain columns: device_name, power_w, location.
        threshold_kw: Threshold in kilowatts.

    Returns:
        A list of alert dictionaries with keys:
          - device_name: Name of the device
          - power_kw: Current consumption in kW
          - location: Device location
          - severity: 'HIGH' or 'CRITICAL'
          - message: Human-readable alert message
    """
    alerts = []

    if latest_readings.empty:
        return alerts

    for _, row in latest_readings.iterrows():
        power_w = row.get("power_w")
        if power_w is None or pd.isna(power_w):
            continue

        power_kw = power_w / 1000
        device_name = row.get("device_name", "Unknown Device")
        location = row.get("location", "Unknown Location")

        if power_kw >= threshold_kw:
            severity = "CRITICAL" if power_kw >= threshold_kw * 1.5 else "HIGH"
            alerts.append({
                "device_name": device_name,
                "power_kw": round(power_kw, 3),
                "location": location,
                "severity": severity,
                "message": (
                    f"{device_name} ({location}) is consuming "
                    f"{power_kw:.2f} kW — exceeds threshold of {threshold_kw} kW."
                ),
            })

    # Sort: critical first, then by power descending
    alerts.sort(key=lambda a: (-1 if a["severity"] == "CRITICAL" else 0, -a["power_kw"]))
    return alerts


# ─────────────────────────────────────────────
# Dynamic Recommendations
# ─────────────────────────────────────────────

# Base recommendations always shown
_BASE_RECOMMENDATIONS = [
    {
        "icon": "💡",
        "title": "Use Energy-Efficient Appliances",
        "detail": "Replace old appliances with BEE 5-star rated models to reduce consumption by up to 30%.",
    },
    {
        "icon": "🔌",
        "title": "Eliminate Standby Power",
        "detail": "Unplug chargers, adapters, and electronics when not in use. Standby power can account for 5-10% of household energy use.",
    },
    {
        "icon": "🌡️",
        "title": "Optimise AC Temperature",
        "detail": "Set air conditioning to 24°C instead of lower temperatures. Each degree lower increases energy use by 3-5%.",
    },
    {
        "icon": "⏰",
        "title": "Schedule High-Power Appliances",
        "detail": "Run washing machines and water heaters during off-peak hours to benefit from lower tariff rates.",
    },
    {
        "icon": "📊",
        "title": "Monitor Consumption Regularly",
        "detail": "Review your energy dashboard daily to identify abnormal consumption patterns and take corrective action.",
    },
]


def generate_recommendations(
    latest_readings: pd.DataFrame,
    total_energy_kwh: float = 0.0,
    threshold_kw: float = HIGH_CONSUMPTION_THRESHOLD_KW,
) -> list[dict]:
    """
    Generate dynamic energy-saving recommendations based on current data.

    The engine:
    1. Identifies the highest-consuming device and generates a targeted tip.
    2. Checks for devices exceeding the threshold and adds specific advice.
    3. Appends general best-practice recommendations.

    Args:
        latest_readings: DataFrame with most recent reading per device.
        total_energy_kwh: Total cumulative energy consumed.
        threshold_kw: High-consumption threshold in kW.

    Returns:
        A list of recommendation dicts with keys: icon, title, detail.
    """
    recommendations = []

    if not latest_readings.empty and "power_w" in latest_readings.columns:
        # Filter out rows with no readings
        valid = latest_readings.dropna(subset=["power_w"])

        if not valid.empty:
            # ── Highest consumer ──
            top_device = valid.loc[valid["power_w"].idxmax()]
            top_name = top_device.get("device_name", "Unknown")
            top_power_kw = top_device["power_w"] / 1000

            recommendations.append({
                "icon": "🔴",
                "title": f"Reduce {top_name} Usage",
                "detail": (
                    f"{top_name} is your highest consumer at {top_power_kw:.2f} kW. "
                    f"Consider reducing its operating time or switching to a more efficient model."
                ),
            })

            # ── Devices exceeding threshold ──
            high_devices = valid[valid["power_w"] / 1000 >= threshold_kw]
            if len(high_devices) > 1:
                names = ", ".join(high_devices["device_name"].tolist())
                recommendations.append({
                    "icon": "⚠️",
                    "title": "Multiple High-Consumption Devices",
                    "detail": (
                        f"{len(high_devices)} devices exceed the {threshold_kw} kW threshold: {names}. "
                        f"Avoid running them simultaneously to reduce peak load."
                    ),
                })

            # ── Low-consumption devices that are on ──
            low_devices = valid[valid["power_w"] / 1000 < 0.1]
            if not low_devices.empty:
                names = ", ".join(low_devices["device_name"].tolist())
                recommendations.append({
                    "icon": "🔋",
                    "title": "Turn Off Low-Usage Devices",
                    "detail": (
                        f"{names} {'is' if len(low_devices) == 1 else 'are'} consuming very little power. "
                        f"Consider turning {'it' if len(low_devices) == 1 else 'them'} off if not needed."
                    ),
                })

    # ── Cost-saving tip if energy is significant ──
    if total_energy_kwh > 0.5:
        recommendations.append({
            "icon": "💰",
            "title": "Consider Solar Energy",
            "detail": (
                f"Your cumulative consumption is {total_energy_kwh:.2f} kWh. "
                f"Installing a rooftop solar system can offset 60-80% of your electricity bill."
            ),
        })

    # Append base recommendations
    recommendations.extend(_BASE_RECOMMENDATIONS)

    return recommendations
