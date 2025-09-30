# dashboard.py

import streamlit as st
import pandas as pd
from datetime import datetime
from backend.rag_agent import (
    get_readings,
    get_trend_analysis,
    predict_failure,
    compare_machines,
    get_rag_response
)
from backend.db_utils import get_machine_details

from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go

# ------------------- Auto Refresh -------------------
st_autorefresh(interval=30_000, key="refresh1")  # refresh every 30s

st.set_page_config(page_title="AI-Powered Machine Dashboard", layout="wide")
st.title("🤖 Machine Monitoring & Analysis Dashboard")

# ------------------- Sidebar Filters -------------------
st.sidebar.header("Filters")
machine_id = st.sidebar.selectbox("Select Machine", [1, 2, 3])

# Fetch all data to determine available date range
all_rows = get_readings(machine_id, n=None)
if all_rows:
    earliest = min(r["timestamp"] for r in all_rows).date()
    latest = max(r["timestamp"] for r in all_rows).date()
else:
    earliest = latest = datetime.today().date()

start_date = st.sidebar.date_input("Start Date", earliest, min_value=earliest, max_value=latest)
end_date = st.sidebar.date_input("End Date", latest, min_value=earliest, max_value=latest)

n_readings = st.sidebar.slider("Number of readings", 5, 500, 50)

metrics_options = ["temperature", "vibration", "pressure", "rpm", "current", "voltage"]
selected_metrics = st.sidebar.multiselect(
    "Metrics to display", metrics_options, default=metrics_options
)

# ------------------- Fetch Data -------------------
rows = get_readings(
    machine_id,
    n=n_readings,
    start_date=start_date.strftime("%Y-%m-%d"),
    end_date=end_date.strftime("%Y-%m-%d")
)

if not rows:
    st.warning(f"⚠️ No data available for Machine {machine_id} in the selected range.")
    st.stop()

# ------------------- Machine Details -------------------
st.subheader("🏭 Machine Details")
machine_info = get_machine_details(machine_id)
st.markdown(machine_info, unsafe_allow_html=True)

# ------------------- KPI Summary -------------------
st.subheader("📊 Machine KPI Summary")

# Count alerts
alert_count = sum(
    r["vibration"] > 30 or r["temperature"] > 120 or r["pressure"] > 10
    for r in rows
)

# Latest RUL predictions
rul_predictions = {}
for metric in ["temperature", "vibration", "pressure"]:
    values = [r[metric] for r in rows]
    rul_predictions[metric] = predict_failure(values, metric)

# Overall health status
if alert_count == 0:
    health_status = "✅ Healthy"
elif alert_count < 5:
    health_status = "⚠️ Warning"
else:
    health_status = "❌ Critical"

# Display KPIs in columns
col1, col2, col3 = st.columns(3)
col1.metric("Total Alerts", alert_count)
col2.text("Latest RUL Predictions")
col2.write(rul_predictions)
col3.metric("Overall Health", health_status)

# ------------------- Alerts -------------------
st.subheader("⚠️ Alerts")
alerts = []
for r in rows:
    if r["vibration"] > 30:
        alerts.append(f"Vibration exceeded 30 at {r['timestamp']}")
    if r["temperature"] > 120:
        alerts.append(f"Temperature exceeded 120°C at {r['timestamp']}")

if alerts:
    for alert in alerts:
        st.error(alert)
else:
    st.success("No critical alerts.")

# ------------------- Latest Readings -------------------
st.subheader("📊 Latest Readings")
latest = rows[-1]
st.table(pd.DataFrame([latest]))

# ------------------- Interactive Trend Graphs with Threshold Highlights -------------------
st.subheader("📈 Trend Analysis (Interactive with Threshold Highlights)")
thresholds = {"temperature": 120, "vibration": 30, "pressure": 10}

for metric in selected_metrics:
    df = pd.DataFrame({
        "timestamp": [r["timestamp"] for r in rows],
        metric: [r[metric] for r in rows]
    })
    
    exceed_idx = df[metric] > thresholds.get(metric, float('inf'))
    
    fig = go.Figure()
    
    # Metric line
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df[metric],
        mode="lines+markers",
        name=metric,
        line=dict(color="blue")
    ))
    
    # Highlight points exceeding threshold
    if metric in thresholds:
        fig.add_trace(go.Scatter(
            x=df["timestamp"][exceed_idx],
            y=df[metric][exceed_idx],
            mode="markers",
            name=f"{metric} exceeded",
            marker=dict(color="red", size=10, symbol="circle-open")
        ))
        # Threshold line
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=[thresholds[metric]]*len(df),
            mode="lines",
            name=f"{metric} threshold",
            line=dict(color="red", dash="dash")
        ))
    
    fig.update_layout(
        title=f"{metric.capitalize()} Trend",
        xaxis_title="Timestamp",
        yaxis_title=metric.capitalize(),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ------------------- Failure Predictions -------------------
st.subheader("⚠️ Failure Predictions (RUL)")
for metric in ["temperature", "vibration", "pressure"]:
    values = [r[metric] for r in rows]
    st.write(predict_failure(values, metric))

# ------------------- Machine Comparison -------------------
st.subheader("🔍 Machine Comparison")
st.write(compare_machines())

# ------------------- Trend Analysis Table -------------------
st.subheader("📊 Detailed Trend Analysis")
st.text(get_trend_analysis(rows, param=selected_metrics))

# ------------------- Knowledge / Maintenance (RAG) -------------------
st.subheader("📖 Maintenance & Troubleshooting")
user_query = st.text_input("Ask a machine-related question:")

if user_query:
    response = get_rag_response(user_query, machine_id)
    st.write("**Answer:**", response["answer"])
    if response["sources"]:
        # Make sources clickable if they are URLs
        st.write("**Sources:**", ", ".join(
            [f"[{src}]({src})" if src.startswith("http") else src for src in response["sources"]]
        ))

# ------------------- Data Export -------------------
st.subheader("💾 Export Data")
export_df = pd.DataFrame(rows)
st.download_button(
    label="Download Data as CSV",
    data=export_df.to_csv(index=False).encode("utf-8"),
    file_name=f"machine_{machine_id}_data.csv",
    mime="text/csv"
)
