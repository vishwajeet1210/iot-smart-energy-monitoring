"""
Smart Energy Monitoring and Management System — Main Application.

This is the presentation layer built with Streamlit.
It integrates all modules (database, IoT simulator, analytics, alerts)
into a professional monitoring dashboard.

Run with:
    streamlit run app.py
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from config import (
    APP_TITLE,
    APP_ICON,
    PAGE_LAYOUT,
    DEFAULT_TARIFF_RATE,
    HIGH_CONSUMPTION_THRESHOLD_KW,
    DEVICE_SPECS,
)
from database import (
    initialize_database,
    insert_readings_batch,
    get_latest_readings,
    get_readings_for_analytics,
    get_reading_count,
    clear_all_readings,
)
from iot_simulator import generate_all_readings, generate_historical_data
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
# Page Configuration
# ═════════════════════════════════════════════

st.set_page_config(
    page_title="Smart Energy Monitor",
    page_icon=APP_ICON,
    layout=PAGE_LAYOUT,
    initial_sidebar_state="expanded",
)


# ═════════════════════════════════════════════
# Custom CSS for professional dashboard look
# ═════════════════════════════════════════════

st.markdown("""
<style>
    /* ── Import premium font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global styling ── */
    .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #F8FAFC;
        color: #0F172A;
    }
    
    /* Overall text color for markdown */
    .stMarkdown, p, span, div {
        color: #0F172A;
    }

    /* ── Metric cards ── */
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    div[data-testid="stMetric"] label {
        color: #64748B !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #0F172A !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }

    /* ── Section headers ── */
    .section-header {
        color: #0F172A;
        font-size: 1.25rem;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #EFF6FF;
        display: inline-block;
    }

    /* ── Alert boxes ── */
    .alert-critical {
        background: #FEF2F2;
        border: 1px solid #FCA5A5;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 10px;
        color: #991B1B;
        font-size: 0.95rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .alert-high {
        background: #FFFBEB;
        border: 1px solid #FCD34D;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 10px;
        color: #92400E;
        font-size: 0.95rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .alert-title {
        font-weight: 700;
        font-size: 1.05rem;
        margin-bottom: 4px;
    }

    /* ── Recommendation cards ── */
    .rec-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    .rec-title {
        color: #0F172A;
        font-weight: 600;
        font-size: 1.05rem;
        margin-bottom: 6px;
    }
    .rec-detail {
        color: #475569;
        font-size: 0.95rem;
        line-height: 1.6;
    }

    /* ── Status badge ── */
    .status-normal { color: #16A34A; font-weight: 600; }
    .status-warning { color: #D97706; font-weight: 600; }
    .status-high { color: #DC2626; font-weight: 600; }

    /* ── Sidebar styling ── */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: #334155;
    }
    
    /* ── Sidebar Radio buttons (Navigation) ── */
    div.stRadio > div[role="radiogroup"] > label {
        padding: 8px 12px;
        border-radius: 8px;
        transition: background 0.2s;
    }
    div.stRadio > div[role="radiogroup"] > label:hover {
        background: #F1F5F9;
    }
    div.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"] {
        color: #0F172A;
        font-weight: 500;
    }

    /* ── DataFrame styling ── */
    .stDataFrame {
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        overflow: hidden;
    }
    .stDataFrame th {
        background-color: #F8FAFC !important;
        color: #475569 !important;
        font-weight: 600 !important;
        border-bottom: 1px solid #E2E8F0 !important;
    }
    .stDataFrame td {
        border-bottom: 1px solid #F1F5F9 !important;
        color: #334155 !important;
    }

    /* ── Hide Streamlit branding ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ── Button styling ── */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
        transition: all 0.2s ease;
        border: 1px solid #E2E8F0;
        background: #FFFFFF;
        color: #0F172A;
    }
    .stButton > button:hover {
        border-color: #CBD5E1;
        background: #F8FAFC;
    }
    
    /* Primary button */
    .stButton > button[kind="primary"] {
        background: #2563EB;
        color: #FFFFFF;
        border: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: #1D4ED8;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37,99,235,0.2);
    }

    /* ── Divider ── */
    hr {
        border-color: #E2E8F0;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════
# Initialize Database
# ═════════════════════════════════════════════

initialize_database()


# ═════════════════════════════════════════════
# Sidebar
# ═════════════════════════════════════════════

with st.sidebar:
    st.markdown(f"# {APP_TITLE}")
    st.markdown("**IoT-Based Energy Monitoring & Management**")
    st.markdown("---")

    # Navigation
    st.markdown("### 🧭 Navigation")
    page = st.radio(
        "Select View",
        ["📊 Dashboard", "📡 Devices", "📈 Analytics", "⚠️ Alerts", "💡 Recommendations"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Settings
    st.markdown("### ⚙️ Settings")
    tariff_rate = st.number_input(
        "Electricity Tariff (₹/kWh)",
        min_value=1.0,
        max_value=20.0,
        value=DEFAULT_TARIFF_RATE,
        step=0.5,
        help="Set your local electricity rate in INR per kWh",
    )

    alert_threshold = st.number_input(
        "Alert Threshold (kW)",
        min_value=0.1,
        max_value=5.0,
        value=HIGH_CONSUMPTION_THRESHOLD_KW,
        step=0.1,
        help="Devices consuming above this will trigger alerts",
    )

    st.markdown("---")

    # IoT Sensor Actions
    st.markdown("### 🔧 IoT Sensor Controls")

    if st.button("📡 Generate New IoT Reading", use_container_width=True, type="primary"):
        readings = generate_all_readings()
        # Prepare for batch insert (remove non-DB fields)
        db_readings = [
            {k: v for k, v in r.items() if k in ("device_id", "voltage", "current", "power_w", "energy_kwh", "status", "timestamp")}
            for r in readings
        ]
        count = insert_readings_batch(db_readings)
        st.success(f"✅ Generated {count} new sensor readings!")
        st.rerun()

    # Seed historical data if DB is empty
    if get_reading_count() == 0:
        st.info("📭 No data yet. Generating initial readings...")
        hist_readings = generate_historical_data(hours=2, interval_minutes=5)
        db_readings = [
            {k: v for k, v in r.items() if k in ("device_id", "voltage", "current", "power_w", "energy_kwh", "status", "timestamp")}
            for r in hist_readings
        ]
        insert_readings_batch(db_readings)
        st.success(f"📊 Seeded {len(db_readings)} historical readings.")
        st.rerun()

    if st.button("🗑️ Clear All Data", use_container_width=True):
        clear_all_readings()
        st.warning("All readings cleared.")
        st.rerun()

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#94A3B8; font-size:0.8rem;'>"
        "Smart Energy Monitor v1.0<br>"
        "SEP CIAP Micro Project<br>"
        "© 2026"
        "</div>",
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════
# Data Loading
# ═════════════════════════════════════════════

latest_readings = get_latest_readings()
all_readings = get_readings_for_analytics()
summary = get_summary_statistics(latest_readings, all_readings, tariff_rate)


# ═════════════════════════════════════════════
# DASHBOARD PAGE
# ═════════════════════════════════════════════

if page == "📊 Dashboard":
    st.markdown(f"# {APP_TITLE}")
    st.markdown("*Real-time energy monitoring using simulated IoT sensors*")
    st.markdown("---")

    # ── KPI Metric Cards ──
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="⚡ Total Power",
            value=f"{summary['total_power_kw']:.2f} kW",
        )
    with col2:
        st.metric(
            label="🔋 Energy (Recorded Period)",
            value=f"{summary['total_energy_kwh']:.3f} kWh",
            help=f"Accumulated energy over the recorded period ({summary['recording_period']}). Calculated as ΣP×t for each sensor reading.",
        )
    with col3:
        st.metric(
            label="💰 Est. Cost",
            value=f"₹{summary['estimated_cost_inr']:.2f}",
        )
    with col4:
        st.metric(
            label="📡 Devices Online",
            value=f"{summary['online_devices']} / {summary['total_devices']}",
        )
    with col5:
        st.metric(
            label="🏠 System Status",
            value=summary["system_status"],
        )

    st.markdown("---")

    # ── Quick Charts ──
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown('<p class="section-header">⚡ Power Over Time</p>', unsafe_allow_html=True)
        power_ts = get_power_over_time(all_readings)
        if not power_ts.empty:
            fig = px.area(
                power_ts,
                x="timestamp",
                y="total_power_kw",
                labels={"total_power_kw": "Power (kW)", "timestamp": "Time"},
                color_discrete_sequence=["#3b82f6"],
            )
            fig.update_layout(
                template="plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=10, b=20),
                height=320,
                xaxis=dict(showgrid=False, title=""),
                yaxis=dict(showgrid=True, gridcolor="#E2E8F0", title="Power (kW)"),
            )
            fig.update_traces(
                fill="tozeroy",
                fillcolor="rgba(37,99,235,0.1)",
                line=dict(width=2.5, color="#2563EB"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available yet. Generate readings to see charts.")

    with chart_col2:
        st.markdown('<p class="section-header">📊 Device Power Distribution</p>', unsafe_allow_html=True)
        power_dist = get_device_power_distribution(latest_readings)
        if not power_dist.empty:
            fig = px.bar(
                power_dist,
                y="device_name",
                x="power_kw",
                orientation="h",
                labels={"power_kw": "Power (kW)", "device_name": ""},
                color="power_kw",
                color_continuous_scale=["#16A34A", "#D97706", "#DC2626"],
            )
            fig.update_layout(
                template="plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=20, t=10, b=20),
                height=320,
                xaxis=dict(showgrid=True, gridcolor="#E2E8F0", rangemode="tozero", title="Power (kW)"),
                yaxis=dict(showgrid=False, automargin=True, title=""),
                coloraxis_showscale=False,
            )
            # Add threshold line
            fig.add_vline(
                x=alert_threshold,
                line_dash="dash",
                line_color="#EF4444",
                annotation_text=f"Threshold ({alert_threshold} kW)",
                annotation_font_color="#EF4444",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available yet.")

    # ── Active Alerts Preview ──
    alerts = check_high_consumption(latest_readings, alert_threshold)
    if alerts:
        st.markdown('<p class="section-header">⚠️ Active Alerts</p>', unsafe_allow_html=True)
        for alert in alerts[:3]:  # Show top 3 on dashboard
            css_class = "alert-critical" if alert["severity"] == "CRITICAL" else "alert-high"
            icon = "🔴" if alert["severity"] == "CRITICAL" else "🟡"
            st.markdown(
                f'<div class="{css_class}">'
                f'<div class="alert-title">{icon} {alert["severity"]} ENERGY CONSUMPTION</div>'
                f'{alert["message"]}'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Device Quick View ──
    st.markdown('<p class="section-header">📡 Device Status Overview</p>', unsafe_allow_html=True)
    if not latest_readings.empty:
        display_df = latest_readings[["device_name", "location", "voltage", "current", "power_w", "status"]].copy()
        display_df.columns = ["Device", "Location", "Voltage (V)", "Current (A)", "Power (W)", "Status"]
        display_df = display_df.fillna("—")

        # Format values
        for col in ["Voltage (V)", "Current (A)", "Power (W)"]:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x:.1f}" if isinstance(x, (int, float)) else x
            )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn(width="small"),
            },
        )
    else:
        st.info("No device readings available.")

    # ── Simulation notice (Change 4) ──
    st.caption(
        "ℹ️ This prototype uses software-based IoT sensor simulation. "
        "In a real deployment, readings would be collected from smart meters or ESP32-based sensors."
    )


# ═════════════════════════════════════════════
# DEVICES PAGE
# ═════════════════════════════════════════════

elif page == "📡 Devices":
    st.markdown("# 📡 Device Monitoring")
    st.markdown("*Real-time status of all connected IoT energy sensors*")
    st.markdown("---")

    if not latest_readings.empty:
        # Device cards in a grid
        cols = st.columns(3)
        for idx, (_, row) in enumerate(latest_readings.iterrows()):
            with cols[idx % 3]:
                power_w = row.get("power_w")
                status = row.get("status", "—")

                if pd.isna(power_w):
                    power_w = 0
                    status = "Offline"

                power_kw = power_w / 1000

                # Color coding
                if status == "High":
                    status_color = "#991B1B"
                    status_bg = "#FEF2F2"
                    border_color = "#FCA5A5"
                elif status == "Warning":
                    status_color = "#92400E"
                    status_bg = "#FFFBEB"
                    border_color = "#FCD34D"
                else:
                    status_color = "#166534"
                    status_bg = "#F0FDF4"
                    border_color = "#86EFAC"

                st.markdown(
                    f"""
                    <div style="
                        background: #FFFFFF;
                        border: 1px solid #E2E8F0;
                        border-top: 4px solid {border_color};
                        border-radius: 12px;
                        padding: 20px;
                        margin-bottom: 16px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                    ">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                            <span style="color:#0F172A; font-weight:600; font-size:1.1rem;">
                                {row.get('device_name', '—')}
                            </span>
                            <span style="color:{status_color}; font-weight:600; font-size:0.75rem;
                                         background:{status_bg}; padding:4px 10px; border-radius:20px; border:1px solid {border_color};">
                                ● {status}
                            </span>
                        </div>
                        <div style="color:#64748B; font-size:0.85rem; margin-bottom:16px;">
                            📍 {row.get('location', '—')}
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px;">
                            <div style="text-align:center;">
                                <div style="color:#94A3B8; font-size:0.75rem; text-transform:uppercase; font-weight:600;">Voltage</div>
                                <div style="color:#334155; font-weight:600; margin-top:4px;">{row.get('voltage', 0):.1f} V</div>
                            </div>
                            <div style="text-align:center;">
                                <div style="color:#94A3B8; font-size:0.75rem; text-transform:uppercase; font-weight:600;">Current</div>
                                <div style="color:#334155; font-weight:600; margin-top:4px;">{row.get('current', 0):.2f} A</div>
                            </div>
                            <div style="text-align:center;">
                                <div style="color:#94A3B8; font-size:0.75rem; text-transform:uppercase; font-weight:600;">Power</div>
                                <div style="color:#0F172A; font-weight:700; font-size:1.05rem; margin-top:2px;">{power_kw:.2f} kW</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("No device data available. Generate IoT readings from the sidebar.")

    # Device specifications table
    st.markdown("---")
    st.markdown('<p class="section-header">📋 Device Specifications</p>', unsafe_allow_html=True)

    specs_data = []
    for dev_id, spec in DEVICE_SPECS.items():
        specs_data.append({
            "Device ID": dev_id,
            "Name": spec["name"],
            "Location": spec["location"],
            "Category": spec["category"],
            "Power Range": f"{spec['power_range'][0]}–{spec['power_range'][1]} W",
            "Typical Hours/Day": spec["typical_hours"],
        })
    st.dataframe(pd.DataFrame(specs_data), use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════
# ANALYTICS PAGE
# ═════════════════════════════════════════════

elif page == "📈 Analytics":
    st.markdown("# 📈 Energy Analytics")
    st.markdown("*Detailed analysis of energy consumption patterns*")
    st.markdown("---")

    if all_readings.empty:
        st.info("No data available for analytics. Generate IoT readings from the sidebar.")
    else:
        # ── Summary row ──
        s_col1, s_col2, s_col3, s_col4 = st.columns(4)
        with s_col1:
            st.metric("Total Readings", f"{summary['total_readings']:,}")
        with s_col2:
            st.metric(
                "Energy (Recorded Period)",
                f"{summary['total_energy_kwh']:.3f} kWh",
                help=f"Accumulated over {summary['recording_period']}",
            )
        with s_col3:
            st.metric("Electricity Cost", f"₹{summary['estimated_cost_inr']:.2f}")
        with s_col4:
            st.metric("Tariff Rate", f"₹{tariff_rate}/kWh")

        st.markdown("---")

        # ── Chart Row 1 ──
        ch1, ch2 = st.columns(2)

        with ch1:
            st.markdown('<p class="section-header">⚡ Total Power Over Time</p>', unsafe_allow_html=True)
            power_ts = get_power_over_time(all_readings)
            if not power_ts.empty:
                fig = px.line(
                    power_ts,
                    x="timestamp",
                    y="total_power_kw",
                    labels={"total_power_kw": "Total Power (kW)", "timestamp": "Time"},
                    color_discrete_sequence=["#3b82f6"],
                )
                fig.update_layout(
                    template="plotly_white",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=10, b=20),
                    height=350,
                    yaxis=dict(gridcolor="#E2E8F0"),
                    xaxis=dict(showgrid=False),
                )
                fig.update_traces(line=dict(width=2.5, color="#2563EB"))
                st.plotly_chart(fig, use_container_width=True)

        with ch2:
            st.markdown('<p class="section-header">🔋 Cumulative Energy Over Time</p>', unsafe_allow_html=True)
            energy_ts = get_energy_over_time(all_readings)
            if not energy_ts.empty:
                fig = px.area(
                    energy_ts,
                    x="timestamp",
                    y="cumulative_energy_kwh",
                    labels={"cumulative_energy_kwh": "Energy (kWh)", "timestamp": "Time"},
                    color_discrete_sequence=["#8b5cf6"],
                )
                fig.update_layout(
                    template="plotly_white",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=10, b=20),
                    height=350,
                    yaxis=dict(gridcolor="#E2E8F0"),
                    xaxis=dict(showgrid=False),
                )
                fig.update_traces(
                    fill="tozeroy",
                    fillcolor="rgba(139,92,246,0.1)",
                    line=dict(width=2.5, color="#8B5CF6"),
                )
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ── Chart Row 2 ──
        ch3, ch4 = st.columns(2)

        with ch3:
            st.markdown('<p class="section-header">🍩 Device Energy Breakdown</p>', unsafe_allow_html=True)
            energy_bd = get_device_energy_breakdown(all_readings)
            if not energy_bd.empty:
                fig = px.pie(
                    energy_bd,
                    names="device_name",
                    values="total_energy_kwh",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    hole=0.4,
                )
                fig.update_layout(
                    template="plotly_white",
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=10, b=20),
                    height=380,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.2,
                        xanchor="center",
                        x=0.5,
                        font=dict(color="#334155"),
                    ),
                )
                fig.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                    textfont_size=11,
                )
                st.plotly_chart(fig, use_container_width=True)

        with ch4:
            st.markdown('<p class="section-header">📊 Device Power Comparison</p>', unsafe_allow_html=True)
            power_dist = get_device_power_distribution(latest_readings)
            if not power_dist.empty:
                fig = px.bar(
                    power_dist,
                    y="device_name",
                    x="power_kw",
                    orientation="h",
                    labels={"power_kw": "Power (kW)", "device_name": ""},
                    color="power_kw",
                    color_continuous_scale=["#16A34A", "#D97706", "#DC2626"],
                )
                fig.update_layout(
                    template="plotly_white",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=10, b=20),
                    height=380,
                    coloraxis_showscale=False,
                    xaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
                    yaxis=dict(showgrid=False),
                )
                fig.add_vline(
                    x=alert_threshold,
                    line_dash="dash",
                    line_color="#EF4444",
                    annotation_text=f"Threshold",
                    annotation_font_color="#EF4444",
                )
                st.plotly_chart(fig, use_container_width=True)

        # ── Raw Data ──
        st.markdown("---")
        st.markdown('<p class="section-header">🗃️ Raw Sensor Data</p>', unsafe_allow_html=True)
        with st.expander("View raw data table", expanded=False):
            display_all = all_readings.copy()
            display_all = display_all.drop(columns=["id", "device_id"], errors="ignore")
            display_all.columns = [c.replace("_", " ").title() for c in display_all.columns]
            st.dataframe(display_all, use_container_width=True, hide_index=True, height=400)


# ═════════════════════════════════════════════
# ALERTS PAGE
# ═════════════════════════════════════════════

elif page == "⚠️ Alerts":
    st.markdown("# ⚠️ Energy Consumption Alerts")
    st.markdown(f"*Devices exceeding the **{alert_threshold} kW** threshold*")
    st.markdown("---")

    alerts = check_high_consumption(latest_readings, alert_threshold)

    if alerts:
        st.markdown(
            f'<div style="background:#FEF2F2; border:1px solid #FCA5A5; border-radius:12px; '
            f'padding:16px 20px; margin-bottom:20px; color:#991B1B; text-align:center; font-size:1.1rem; font-weight:500;">'
            f'⚠️ <strong>{len(alerts)} device(s)</strong> currently exceed the energy threshold!'
            f'</div>',
            unsafe_allow_html=True,
        )

        for alert in alerts:
            css_class = "alert-critical" if alert["severity"] == "CRITICAL" else "alert-high"
            severity_icon = "🔴" if alert["severity"] == "CRITICAL" else "🟡"
            severity_label = alert["severity"]

            st.markdown(
                f"""
                <div class="{css_class}">
                    <div class="alert-title">{severity_icon} {severity_label} ENERGY CONSUMPTION</div>
                    <div style="margin-top:8px;">{alert['message']}</div>
                    <div style="margin-top:8px; font-size:0.85rem; opacity:0.8;">
                        📍 Location: {alert['location']} &nbsp;|&nbsp;
                        ⚡ Power: {alert['power_kw']:.3f} kW &nbsp;|&nbsp;
                        🎯 Threshold: {alert_threshold} kW
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="background:#F0FDF4; border:1px solid #86EFAC; border-radius:12px; '
            'padding:20px; text-align:center; color:#166534; font-size:1.1rem; font-weight:500;">'
            '✅ All devices are operating within normal energy consumption limits.'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Threshold visualization ──
    st.markdown("---")
    st.markdown('<p class="section-header">📊 Consumption vs Threshold</p>', unsafe_allow_html=True)

    if not latest_readings.empty:
        power_dist = get_device_power_distribution(latest_readings)
        if not power_dist.empty:
            colors = ["#EF4444" if v >= alert_threshold else "#10B981" for v in power_dist["power_kw"]]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=power_dist["device_name"],
                y=power_dist["power_kw"],
                marker_color=colors,
                text=[f"{v:.2f} kW" for v in power_dist["power_kw"]],
                textposition="outside",
            ))
            fig.add_hline(
                y=alert_threshold,
                line_dash="dash",
                line_color="#EF4444",
                line_width=2,
                annotation_text=f"Threshold: {alert_threshold} kW",
                annotation_font_color="#EF4444",
                annotation_font_size=13,
            )
            fig.update_layout(
                template="plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=30, b=20),
                height=400,
                yaxis_title="Power (kW)",
                xaxis_title="",
                yaxis=dict(gridcolor="#E2E8F0", rangemode="tozero"),
                xaxis=dict(showgrid=False, automargin=True),
            )
            st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════
# RECOMMENDATIONS PAGE
# ═════════════════════════════════════════════

elif page == "💡 Recommendations":
    st.markdown("# 💡 Energy-Saving Recommendations")
    st.markdown("*Personalized tips based on your consumption patterns*")
    st.markdown("---")

    recommendations = generate_recommendations(
        latest_readings,
        total_energy_kwh=summary["total_energy_kwh"],
        threshold_kw=alert_threshold,
    )

    for i, rec in enumerate(recommendations):
        st.markdown(
            f"""
            <div class="rec-card">
                <div class="rec-title">{rec['icon']} {rec['title']}</div>
                <div class="rec-detail">{rec['detail']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Cost estimation section ──
    st.markdown("---")
    st.markdown('<p class="section-header">💰 Electricity Cost Estimator</p>', unsafe_allow_html=True)

    est_col1, est_col2 = st.columns(2)
    with est_col1:
        st.markdown(
            f"""
            <div style="background:#FFFFFF;
                        border:1px solid #E2E8F0; border-radius:12px; padding:24px; box-shadow: 0 1px 4px rgba(0,0,0,0.03);">
                <div style="color:#64748B; font-size:0.85rem; font-weight:600; text-transform:uppercase; margin-bottom:8px;">
                    Current Consumption
                </div>
                <div style="color:#0F172A; font-size:2rem; font-weight:700; margin-bottom:12px;">
                    {summary['total_energy_kwh']:.3f} kWh
                </div>
                <div style="color:#64748B; font-size:0.85rem; font-weight:600; text-transform:uppercase; margin-bottom:8px;">
                    Tariff Rate
                </div>
                <div style="color:#2563EB; font-size:1.2rem; font-weight:600;">
                    ₹{tariff_rate}/kWh
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with est_col2:
        st.markdown(
            f"""
            <div style="background:#F0FDF4;
                        border:1px solid #86EFAC; border-radius:12px; padding:24px; box-shadow: 0 1px 4px rgba(0,0,0,0.03);">
                <div style="color:#166534; font-size:0.85rem; font-weight:600; text-transform:uppercase; margin-bottom:8px;">
                    Estimated Cost
                </div>
                <div style="color:#14532D; font-size:2.5rem; font-weight:700; margin-bottom:12px;">
                    ₹{summary['estimated_cost_inr']:.2f}
                </div>
                <div style="color:#16A34A; font-size:0.9rem; font-weight:500;">
                    Based on {summary['total_readings']} sensor readings
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ═════════════════════════════════════════════
# Footer
# ═════════════════════════════════════════════

st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#475569; font-size:0.8rem; padding:1rem;'>"
    "IoT-Based Smart Energy Monitoring & Management System &nbsp;|&nbsp; "
    "SEP CIAP Micro Project &nbsp;|&nbsp; "
    "Built with Python, Streamlit, SQLite, Plotly"
    "</div>",
    unsafe_allow_html=True,
)
