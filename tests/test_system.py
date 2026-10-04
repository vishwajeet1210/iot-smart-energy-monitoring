"""
Automated Tests for Smart Energy Monitoring System.

Tests cover:
1. IoT sensor data generation (realistic values, correct structure)
2. Energy calculation (power → energy conversion)
3. Electricity cost calculation (energy × tariff)
4. High-consumption alert detection (threshold logic)
5. Database insertion and retrieval (CRUD operations)
6. Analytics computations (aggregations, summaries)
7. Recommendation generation (dynamic tips)

Run with:
    pytest tests/test_system.py -v
"""

import os
import sys
import sqlite3
import tempfile
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

# Add parent directory to path so we can import project modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEVICE_SPECS, HIGH_CONSUMPTION_THRESHOLD_KW, DEFAULT_TARIFF_RATE
from iot_simulator import (
    generate_single_reading,
    generate_all_readings,
    generate_historical_data,
    get_all_device_ids,
)
from analytics import (
    calculate_total_power_kw,
    calculate_total_energy_kwh,
    calculate_electricity_cost,
    get_power_over_time,
    get_energy_over_time,
    get_device_energy_breakdown,
    get_device_power_distribution,
    get_summary_statistics,
)
from alerts import check_high_consumption, generate_recommendations


# ═════════════════════════════════════════════
# TEST 1: IoT Sensor Data Generation
# ═════════════════════════════════════════════

class TestIoTSimulator:
    """Tests for the IoT sensor simulation layer."""

    def test_single_reading_structure(self):
        """Verify a generated reading contains all required fields."""
        reading = generate_single_reading("DEV-AC-001")
        required_keys = {
            "device_id", "device_name", "location", "category",
            "voltage", "current", "power_w", "energy_kwh",
            "status", "timestamp",
        }
        assert required_keys.issubset(reading.keys()), \
            f"Missing keys: {required_keys - reading.keys()}"

    def test_single_reading_values_in_range(self):
        """Verify generated values fall within configured device ranges."""
        device_id = "DEV-AC-001"
        spec = DEVICE_SPECS[device_id]
        reading = generate_single_reading(device_id)

        assert spec["voltage_range"][0] <= reading["voltage"] <= spec["voltage_range"][1], \
            f"Voltage {reading['voltage']} out of range {spec['voltage_range']}"
        assert spec["current_range"][0] <= reading["current"] <= spec["current_range"][1], \
            f"Current {reading['current']} out of range {spec['current_range']}"
        assert spec["power_range"][0] <= reading["power_w"] <= spec["power_range"][1], \
            f"Power {reading['power_w']} out of range {spec['power_range']}"

    def test_single_reading_energy_positive(self):
        """Energy consumed must be a positive value."""
        reading = generate_single_reading("DEV-RF-002")
        assert reading["energy_kwh"] > 0, "Energy must be positive"

    def test_single_reading_status_valid(self):
        """Status must be one of the defined values."""
        reading = generate_single_reading("DEV-WH-006")
        assert reading["status"] in ("Normal", "Warning", "High"), \
            f"Invalid status: {reading['status']}"

    def test_single_reading_custom_timestamp(self):
        """A custom timestamp should be reflected in the reading."""
        ts = "2026-01-15 10:30:00"
        reading = generate_single_reading("DEV-LT-005", timestamp=ts)
        assert reading["timestamp"] == ts

    def test_unknown_device_raises_error(self):
        """Requesting a reading for an unknown device should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown device ID"):
            generate_single_reading("DEV-INVALID-999")

    def test_generate_all_readings_count(self):
        """generate_all_readings should produce one reading per device."""
        readings = generate_all_readings()
        assert len(readings) == len(DEVICE_SPECS), \
            f"Expected {len(DEVICE_SPECS)} readings, got {len(readings)}"

    def test_generate_all_readings_unique_devices(self):
        """Each reading should be for a different device."""
        readings = generate_all_readings()
        device_ids = [r["device_id"] for r in readings]
        assert len(set(device_ids)) == len(device_ids), "Duplicate device IDs found"

    def test_generate_historical_data_non_empty(self):
        """Historical data generation should produce multiple readings."""
        readings = generate_historical_data(hours=1, interval_minutes=15)
        # 1 hour / 15 min = ~5 timestamps × 6 devices = ~30 readings
        assert len(readings) >= 20, f"Expected ≥20 readings, got {len(readings)}"

    def test_get_all_device_ids(self):
        """Should return all configured device IDs."""
        ids = get_all_device_ids()
        assert set(ids) == set(DEVICE_SPECS.keys())


# ═════════════════════════════════════════════
# TEST 2: Energy Calculation
# ═════════════════════════════════════════════

class TestEnergyCalculation:
    """Tests for energy (kWh) calculations."""

    def test_energy_from_power(self):
        """Verify energy = power(kW) × time(hours) formula."""
        # 1000 W for 1 hour = 1 kWh
        # Our simulator uses READING_INTERVAL_SECONDS = 300 (5 minutes)
        # So energy = (1000/1000) * (300/3600) ≈ 0.0833 kWh
        reading = generate_single_reading("DEV-AC-001")
        power_kw = reading["power_w"] / 1000
        expected_energy = power_kw * (300 / 3600)
        assert abs(reading["energy_kwh"] - expected_energy) < 0.001, \
            f"Energy mismatch: {reading['energy_kwh']} vs expected {expected_energy}"

    def test_total_energy_from_dataframe(self):
        """Total energy should sum all readings' energy_kwh."""
        data = pd.DataFrame({
            "energy_kwh": [0.001, 0.002, 0.003, 0.004]
        })
        total = calculate_total_energy_kwh(data)
        assert abs(total - 0.01) < 0.0001

    def test_total_energy_empty_dataframe(self):
        """Empty DataFrame should return 0."""
        assert calculate_total_energy_kwh(pd.DataFrame()) == 0.0

    def test_total_power_calculation(self):
        """Total power should be the sum of all devices' power in kW."""
        data = pd.DataFrame({
            "power_w": [1000, 500, 200]
        })
        total = calculate_total_power_kw(data)
        assert abs(total - 1.7) < 0.001

    def test_total_power_empty(self):
        """Empty DataFrame should return 0 kW."""
        assert calculate_total_power_kw(pd.DataFrame()) == 0.0


# ═════════════════════════════════════════════
# TEST 3: Electricity Cost Calculation
# ═════════════════════════════════════════════

class TestElectricityCost:
    """Tests for electricity cost estimation."""

    def test_cost_at_default_tariff(self):
        """Cost = energy × tariff."""
        cost = calculate_electricity_cost(10.0, DEFAULT_TARIFF_RATE)
        assert cost == 10.0 * DEFAULT_TARIFF_RATE

    def test_cost_at_custom_tariff(self):
        """Cost should scale with the tariff rate."""
        cost = calculate_electricity_cost(5.0, 12.0)
        assert cost == 60.0

    def test_cost_zero_energy(self):
        """Zero energy should produce zero cost."""
        cost = calculate_electricity_cost(0.0)
        assert cost == 0.0

    def test_cost_precision(self):
        """Cost should be rounded to 2 decimal places."""
        cost = calculate_electricity_cost(1.333333, 8.0)
        # 1.333333 * 8 = 10.666664
        assert cost == 10.67


# ═════════════════════════════════════════════
# TEST 4: High-Consumption Alert Detection
# ═════════════════════════════════════════════

class TestAlerts:
    """Tests for the alert detection engine."""

    def _make_readings_df(self, power_values):
        """Helper: create a latest_readings-like DataFrame."""
        rows = []
        for i, pw in enumerate(power_values):
            rows.append({
                "device_name": f"Device {i}",
                "power_w": pw,
                "location": f"Room {i}",
                "status": "Normal",
            })
        return pd.DataFrame(rows)

    def test_alert_triggered_above_threshold(self):
        """Devices above threshold should generate alerts."""
        df = self._make_readings_df([1500, 200, 1300])  # 1.5kW and 1.3kW > 1.2kW
        alerts = check_high_consumption(df, threshold_kw=1.2)
        assert len(alerts) == 2

    def test_no_alert_below_threshold(self):
        """Devices below threshold should not generate alerts."""
        df = self._make_readings_df([100, 200, 300])
        alerts = check_high_consumption(df, threshold_kw=1.2)
        assert len(alerts) == 0

    def test_alert_severity_critical(self):
        """Power ≥ 1.5× threshold should be CRITICAL."""
        df = self._make_readings_df([2000])  # 2.0 kW ≥ 1.2 * 1.5 = 1.8 kW
        alerts = check_high_consumption(df, threshold_kw=1.2)
        assert alerts[0]["severity"] == "CRITICAL"

    def test_alert_severity_high(self):
        """Power above threshold but below 1.5× should be HIGH."""
        df = self._make_readings_df([1300])  # 1.3 kW < 1.8 kW
        alerts = check_high_consumption(df, threshold_kw=1.2)
        assert alerts[0]["severity"] == "HIGH"

    def test_alert_empty_dataframe(self):
        """Empty DataFrame should produce no alerts."""
        alerts = check_high_consumption(pd.DataFrame(), threshold_kw=1.2)
        assert len(alerts) == 0

    def test_alert_message_content(self):
        """Alert message should contain device name and power value."""
        df = self._make_readings_df([1500])
        alerts = check_high_consumption(df, threshold_kw=1.2)
        assert "Device 0" in alerts[0]["message"]
        assert "1.50" in alerts[0]["message"] or "1.5" in alerts[0]["message"]


# ═════════════════════════════════════════════
# TEST 5: Database Operations
# ═════════════════════════════════════════════

class TestDatabase:
    """Tests for database CRUD operations using a temporary database."""

    @pytest.fixture(autouse=True)
    def setup_temp_db(self, tmp_path):
        """Redirect database to a temporary path for test isolation."""
        temp_db = str(tmp_path / "test_energy.db")
        self._patches = [
            patch("database.DATABASE_PATH", temp_db),
            patch("database.DATABASE_DIR", str(tmp_path)),
        ]
        for p in self._patches:
            p.start()

        # Import after patching
        import database
        database.initialize_database()
        self.db = database
        yield
        for p in self._patches:
            p.stop()

    def test_initialize_creates_tables(self):
        """Database initialization should create devices and readings tables."""
        conn = sqlite3.connect(self.db.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert "devices" in tables
        assert "readings" in tables

    def test_devices_seeded(self):
        """All configured devices should be present in the DB."""
        devices = self.db.get_all_devices()
        assert len(devices) == len(DEVICE_SPECS)

    def test_insert_and_retrieve_reading(self):
        """A single inserted reading should be retrievable."""
        row_id = self.db.insert_reading(
            device_id="DEV-AC-001",
            voltage=230.0,
            current=6.5,
            power_w=1495.0,
            energy_kwh=0.002,
            status="High",
            timestamp="2026-01-01 12:00:00",
        )
        assert row_id > 0

        latest = self.db.get_latest_readings()
        ac_row = latest[latest["device_name"] == "Air Conditioner"]
        assert not ac_row.empty
        assert ac_row.iloc[0]["power_w"] == 1495.0

    def test_batch_insert(self):
        """Batch insert should store all readings."""
        readings = [
            {
                "device_id": "DEV-AC-001",
                "voltage": 230,
                "current": 6.0,
                "power_w": 1380,
                "energy_kwh": 0.002,
                "status": "High",
                "timestamp": "2026-01-01 12:00:00",
            },
            {
                "device_id": "DEV-RF-002",
                "voltage": 228,
                "current": 1.1,
                "power_w": 250,
                "energy_kwh": 0.0003,
                "status": "Normal",
                "timestamp": "2026-01-01 12:00:00",
            },
        ]
        count = self.db.insert_readings_batch(readings)
        assert count == 2
        assert self.db.get_reading_count() == 2

    def test_clear_readings(self):
        """Clearing readings should remove all data."""
        self.db.insert_reading("DEV-LT-005", 232, 0.3, 70, 0.0001, "Normal")
        assert self.db.get_reading_count() == 1
        self.db.clear_all_readings()
        assert self.db.get_reading_count() == 0

    def test_get_readings_for_analytics(self):
        """Analytics query should return data with proper columns."""
        self.db.insert_reading("DEV-PC-004", 230, 1.8, 414, 0.0006, "Normal")
        df = self.db.get_readings_for_analytics()
        assert not df.empty
        assert "device_name" in df.columns
        assert "power_w" in df.columns
        assert "timestamp" in df.columns


# ═════════════════════════════════════════════
# TEST 6: Analytics Computations
# ═════════════════════════════════════════════

class TestAnalytics:
    """Tests for analytics aggregation functions."""

    def _sample_readings(self):
        """Create a sample readings DataFrame for analytics tests."""
        return pd.DataFrame({
            "device_name": ["AC", "AC", "Fridge", "Fridge"],
            "power_w": [1500, 1400, 250, 300],
            "energy_kwh": [0.002, 0.002, 0.0003, 0.0004],
            "timestamp": pd.to_datetime([
                "2026-01-01 12:00:00",
                "2026-01-01 12:05:00",
                "2026-01-01 12:00:00",
                "2026-01-01 12:05:00",
            ]),
        })

    def test_power_over_time(self):
        """Power over time should aggregate per timestamp."""
        df = self._sample_readings()
        result = get_power_over_time(df)
        assert len(result) == 2  # Two distinct timestamps
        assert "total_power_kw" in result.columns

    def test_energy_over_time(self):
        """Cumulative energy should be monotonically increasing."""
        df = self._sample_readings()
        result = get_energy_over_time(df)
        assert result["cumulative_energy_kwh"].is_monotonic_increasing

    def test_device_energy_breakdown(self):
        """Breakdown should have one row per device."""
        df = self._sample_readings()
        result = get_device_energy_breakdown(df)
        assert len(result) == 2  # AC and Fridge

    def test_device_power_distribution(self):
        """Distribution should list devices by current power."""
        latest = pd.DataFrame({
            "device_name": ["AC", "Fridge"],
            "power_w": [1400, 300],
        })
        result = get_device_power_distribution(latest)
        assert result.iloc[0]["device_name"] == "AC"  # AC should be first (highest)

    def test_summary_statistics(self):
        """Summary should contain all expected keys."""
        latest = pd.DataFrame({
            "power_w": [1400, 300],
            "status": ["High", "Normal"],
        })
        all_r = self._sample_readings()
        summary = get_summary_statistics(latest, all_r)
        expected_keys = {
            "total_power_kw", "total_energy_kwh", "estimated_cost_inr",
            "online_devices", "total_devices", "total_readings", "system_status",
        }
        assert expected_keys.issubset(summary.keys())


# ═════════════════════════════════════════════
# TEST 7: Recommendations
# ═════════════════════════════════════════════

class TestRecommendations:
    """Tests for dynamic recommendation generation."""

    def test_recommendations_non_empty(self):
        """Should always return at least base recommendations."""
        recs = generate_recommendations(pd.DataFrame())
        assert len(recs) >= 5  # At least 5 base recs

    def test_recommendations_with_data(self):
        """With data, should include device-specific recommendation."""
        latest = pd.DataFrame({
            "device_name": ["Water Heater", "LED Light"],
            "power_w": [1800, 50],
            "location": ["Bathroom", "Hall"],
        })
        recs = generate_recommendations(latest, total_energy_kwh=1.0)
        titles = [r["title"] for r in recs]
        # Should have a "Reduce Water Heater Usage" recommendation
        assert any("Water Heater" in t for t in titles)

    def test_recommendations_high_energy_solar_tip(self):
        """High cumulative energy should trigger solar recommendation."""
        latest = pd.DataFrame({
            "device_name": ["AC"],
            "power_w": [1500],
            "location": ["Room"],
        })
        recs = generate_recommendations(latest, total_energy_kwh=5.0)
        titles = [r["title"] for r in recs]
        assert any("Solar" in t for t in titles)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
