# ⚡ IoT-Based Smart Energy Monitoring and Management System

> **SEP CIAP Micro Project** — Requirements Analysis of an IoT-Based Smart Energy Monitoring System

A web-based Smart Energy Monitoring and Management System that simulates an IoT-enabled smart energy monitoring environment. The system demonstrates the complete IoT data pipeline from sensor simulation through analytics to actionable alerts and recommendations.

---

## 🏗️ System Architecture

```
┌─────────────────────────────┐
│   IoT Sensor Simulation     │  ← iot_simulator.py
│   (6 Smart Energy Devices)  │
└─────────────┬───────────────┘
              │ Voltage / Current / Power Data
              ▼
┌─────────────────────────────┐
│   Data Processing Layer     │  ← analytics.py
│   (Pandas / Aggregation)    │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Database Layer (SQLite)   │  ← database.py
│   devices & readings tables │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Alert & Analytics Engine  │  ← alerts.py + analytics.py
│   Threshold Detection       │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Presentation Layer        │  ← app.py (Streamlit)
│   Dashboard + Charts + UI   │
└─────────────────────────────┘
```

---

## 📁 Project Structure

```
smart-energy-monitor/
│
├── app.py               # Main Streamlit dashboard (Presentation Layer)
├── config.py            # Centralized configuration (device specs, tariffs, thresholds)
├── database.py          # SQLite database layer (Repository pattern)
├── iot_simulator.py     # IoT sensor simulation engine
├── analytics.py         # Energy analytics computations
├── alerts.py            # Alert detection & recommendation engine
├── requirements.txt     # Python dependencies
├── README.md            # This file
│
├── data/
│   └── energy.db        # SQLite database (auto-created at runtime)
│
└── tests/
    └── test_system.py   # Comprehensive automated test suite (pytest)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher

### Installation

```bash
# Navigate to the project directory
cd smart-energy-monitor

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`.

### Running Tests

```bash
pytest tests/test_system.py -v
```

---

## ✨ Features

### 1. Professional Dashboard
- Real-time KPI metric cards (Power, Energy, Cost, Devices, Status)
- Power trend chart with area fill
- Device power distribution bar chart with threshold line
- Active alerts preview
- Device status table

### 2. IoT Sensor Simulation
Simulates 6 household IoT energy sensors:

| Device | Location | Power Range |
|--------|----------|-------------|
| Air Conditioner | Living Room | 1100–1800 W |
| Refrigerator | Kitchen | 150–350 W |
| Washing Machine | Utility Room | 400–1000 W |
| Desktop Computer | Study Room | 200–600 W |
| LED Lighting | Hall | 20–100 W |
| Water Heater | Bathroom | 1500–2000 W |

Uses Gaussian noise around operating midpoints for realistic values.

### 3. Device Monitoring
- Card-based device display with status indicators
- Color-coded borders (green/amber/red)
- Voltage, current, and power readings per device
- Device specification reference table

### 4. Energy Analytics
- Total Power Over Time (line chart)
- Cumulative Energy Over Time (area chart)
- Device Energy Breakdown (donut chart)
- Device Power Comparison (horizontal bar chart)
- Raw sensor data explorer

### 5. Electricity Cost Estimation
- Configurable tariff rate (₹/kWh) via sidebar
- Real-time cost calculation
- Visual cost display card

### 6. High-Consumption Alerts
- Configurable threshold (default: 1.20 kW)
- Two severity levels: HIGH and CRITICAL
- Visual alert cards with device details
- Consumption vs threshold chart

### 7. Energy-Saving Recommendations
- Dynamic recommendations based on highest consumer
- Multi-device threshold warnings
- Low-usage device suggestions
- Solar energy recommendations for high consumers
- 5 general best-practice tips

### 8. Persistent Database
- SQLite with foreign key relationships
- Auto-seeded historical data (2 hours)
- Batch reading insertion
- WAL mode for performance

---

## 🧪 Testing

The test suite (`tests/test_system.py`) covers 7 categories with 30+ test cases:

| Category | Tests | Description |
|----------|-------|-------------|
| IoT Simulator | 10 | Reading structure, value ranges, timestamps |
| Energy Calculation | 5 | Power-to-energy conversion, aggregation |
| Electricity Cost | 4 | Tariff multiplication, precision, edge cases |
| Alert Detection | 6 | Threshold logic, severity levels, messages |
| Database CRUD | 5 | Insert, retrieve, batch, clear, schema |
| Analytics | 5 | Time-series, breakdowns, summaries |
| Recommendations | 3 | Dynamic tips, solar trigger, base tips |

---

## 🔧 Configuration

Key parameters in `config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DEFAULT_TARIFF_RATE` | ₹8/kWh | Electricity price |
| `HIGH_CONSUMPTION_THRESHOLD_KW` | 1.20 kW | Alert threshold |
| `READING_INTERVAL_SECONDS` | 5 s | Simulated sampling interval |

All values are also adjustable through the sidebar UI at runtime.

---

## 📐 Software Engineering Practices Demonstrated

1. **Requirements Analysis** — Structured requirements → modular implementation
2. **Modular Design** — 6 separate modules with clear responsibilities
3. **Separation of Concerns** — Presentation, business logic, and data layers
4. **Database Design** — Normalized schema with foreign keys and indexes
5. **Automated Testing** — 30+ pytest test cases across all layers
6. **Error Handling** — Graceful handling of empty data, invalid IDs, missing values
7. **Maintainability** — Docstrings, type hints, configuration externalization
8. **Usability** — Professional dark-theme dashboard with intuitive navigation

---

## 📝 Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.9+ |
| Web Framework | Streamlit |
| Database | SQLite |
| Data Processing | Pandas |
| Visualization | Plotly |
| Testing | pytest |

---

## ⚠️ Limitations

- Sensor data is simulated (no real IoT hardware)
- Data is stored locally (no cloud sync)
- Single-user application (no authentication)
- Cost estimation is approximate (single-rate tariff)

---

*Built for SEP CIAP Micro Project Assessment — IoT-Based Smart Energy Monitoring System*
