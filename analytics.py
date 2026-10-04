"""
Analytics Engine for Smart Energy Monitoring System.

Processes raw sensor readings to produce:
- Summary statistics (total power, energy, cost)
- Time-series data for trend visualization
- Device-level aggregations for comparison charts
- Peak consumption identification

All analytics functions accept DataFrames and return
processed data ready for Plotly visualization.
"""

import pandas as pd

from config import DEFAULT_TARIFF_RATE


def calculate_total_power_kw(latest_readings: pd.DataFrame) -> float:
    """
    Calculate total instantaneous power consumption across all devices.

    Args:
        latest_readings: DataFrame with the most recent reading per device.

    Returns:
        Total power consumption in kilowatts (kW).
    """
    if latest_readings.empty or "power_w" not in latest_readings.columns:
        return 0.0
    return round(latest_readings["power_w"].sum() / 1000, 3)


def calculate_total_energy_kwh(all_readings: pd.DataFrame) -> float:
    """
    Calculate total cumulative energy consumption.

    Args:
        all_readings: DataFrame containing all historical readings.

    Returns:
        Total energy in kilowatt-hours (kWh).
    """
    if all_readings.empty or "energy_kwh" not in all_readings.columns:
        return 0.0
    return round(all_readings["energy_kwh"].sum(), 4)


def calculate_electricity_cost(
    energy_kwh: float,
    tariff_rate: float = DEFAULT_TARIFF_RATE,
) -> float:
    """
    Calculate estimated electricity cost in INR.

    Args:
        energy_kwh: Total energy consumed in kWh.
        tariff_rate: Price per kWh in INR.

    Returns:
        Estimated cost in INR.
    """
    return round(energy_kwh * tariff_rate, 2)


def get_power_over_time(all_readings: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate total power consumption per timestamp for time-series charting.

    Args:
        all_readings: DataFrame with columns [timestamp, power_w].

    Returns:
        DataFrame with columns [timestamp, total_power_kw].
    """
    if all_readings.empty:
        return pd.DataFrame(columns=["timestamp", "total_power_kw"])

    df = all_readings.copy()
    grouped = (
        df.groupby("timestamp")["power_w"]
        .sum()
        .reset_index()
    )
    grouped["total_power_kw"] = (grouped["power_w"] / 1000).round(3)
    grouped = grouped.sort_values("timestamp")
    return grouped[["timestamp", "total_power_kw"]]


def get_energy_over_time(all_readings: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate cumulative energy consumption over time.

    Args:
        all_readings: DataFrame with columns [timestamp, energy_kwh].

    Returns:
        DataFrame with columns [timestamp, cumulative_energy_kwh].
    """
    if all_readings.empty:
        return pd.DataFrame(columns=["timestamp", "cumulative_energy_kwh"])

    df = all_readings.copy()
    grouped = (
        df.groupby("timestamp")["energy_kwh"]
        .sum()
        .reset_index()
    )
    grouped = grouped.sort_values("timestamp")
    grouped["cumulative_energy_kwh"] = grouped["energy_kwh"].cumsum().round(4)
    return grouped[["timestamp", "cumulative_energy_kwh"]]


def get_device_energy_breakdown(all_readings: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate total energy consumption per device for pie/bar charts.

    Args:
        all_readings: DataFrame with columns [device_name, energy_kwh].

    Returns:
        DataFrame with columns [device_name, total_energy_kwh], sorted descending.
    """
    if all_readings.empty:
        return pd.DataFrame(columns=["device_name", "total_energy_kwh"])

    grouped = (
        all_readings.groupby("device_name")["energy_kwh"]
        .sum()
        .reset_index()
        .rename(columns={"energy_kwh": "total_energy_kwh"})
        .sort_values("total_energy_kwh", ascending=False)
    )
    grouped["total_energy_kwh"] = grouped["total_energy_kwh"].round(4)
    return grouped


def get_device_power_distribution(latest_readings: pd.DataFrame) -> pd.DataFrame:
    """
    Get current power consumption per device for distribution chart.

    Args:
        latest_readings: DataFrame with the most recent reading per device.

    Returns:
        DataFrame with columns [device_name, power_kw], sorted descending.
    """
    if latest_readings.empty:
        return pd.DataFrame(columns=["device_name", "power_kw"])

    df = latest_readings[["device_name", "power_w"]].copy()
    df["power_kw"] = (df["power_w"] / 1000).round(3)
    return df[["device_name", "power_kw"]].sort_values("power_kw", ascending=False)


def _format_recording_period(all_readings: pd.DataFrame) -> str:
    """
    Compute a human-readable string describing the time span of recorded data.

    Examples: "2 hr 15 min", "45 min", "No data"
    """
    if all_readings.empty or "timestamp" not in all_readings.columns:
        return "No data"

    timestamps = pd.to_datetime(all_readings["timestamp"])
    duration = timestamps.max() - timestamps.min()
    total_minutes = int(duration.total_seconds() / 60)

    if total_minutes < 1:
        return "< 1 min"
    elif total_minutes < 60:
        return f"{total_minutes} min"
    else:
        hours = total_minutes // 60
        mins = total_minutes % 60
        if mins == 0:
            return f"{hours} hr"
        return f"{hours} hr {mins} min"


def get_summary_statistics(
    latest_readings: pd.DataFrame,
    all_readings: pd.DataFrame,
    tariff_rate: float = DEFAULT_TARIFF_RATE,
) -> dict:
    """
    Compute a comprehensive summary of the energy monitoring system state.

    Returns a dictionary with keys:
      - total_power_kw: Current total power draw
      - total_energy_kwh: Cumulative energy consumed
      - estimated_cost_inr: Estimated electricity cost
      - online_devices: Count of devices with readings
      - total_devices: Total registered devices
      - total_readings: Number of stored data points
      - system_status: Overall system status string
    """
    total_power = calculate_total_power_kw(latest_readings)
    total_energy = calculate_total_energy_kwh(all_readings)
    cost = calculate_electricity_cost(total_energy, tariff_rate)

    online_devices = len(latest_readings.dropna(subset=["power_w"])) if not latest_readings.empty else 0
    from config import DEVICE_SPECS
    total_devices = len(DEVICE_SPECS)

    # Determine system status
    high_count = 0
    if not latest_readings.empty and "status" in latest_readings.columns:
        high_count = (latest_readings["status"] == "High").sum()

    if high_count > 2:
        system_status = "⚠️ Critical"
    elif high_count > 0:
        system_status = "⚡ Alert"
    else:
        system_status = "✅ Normal"

    return {
        "total_power_kw": total_power,
        "total_energy_kwh": total_energy,
        "estimated_cost_inr": cost,
        "online_devices": online_devices,
        "total_devices": total_devices,
        "total_readings": len(all_readings),
        "system_status": system_status,
        "recording_period": _format_recording_period(all_readings),
    }
