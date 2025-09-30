import re
import mysql.connector
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import RetrievalQA
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ---------------- Load FAISS Vector Store ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTORSTORE_PATH = os.path.join(BASE_DIR, "..", "vectorstore")

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
vectorstore = FAISS.load_local(
    VECTORSTORE_PATH, embeddings, allow_dangerous_deserialization=True
)
retriever = vectorstore.as_retriever()

# ---------------- LLM ----------------
llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY)

# ---------------- RAG Chain ----------------
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
    return_source_documents=True
)

# ---------------- MYSQL CONNECTION ----------------
def get_mysql_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="$sujCHER2956",
        database="ignitiondb"
    )

# ---------------- DATA RETRIEVAL ----------------
def get_readings(machine_id: int, n: int = None, start_date=None, end_date=None):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM machine_sensor_data WHERE machine_id = %s"
    params = [machine_id]

    if start_date and end_date:
        query += " AND timestamp BETWEEN %s AND %s"
        params.extend([start_date, end_date])

    query += " ORDER BY timestamp DESC"
    if n:
        query += " LIMIT %s"
        params.append(n)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return rows[::-1]  # oldest → newest

# ---------------- HELPER FUNCTIONS ----------------
def compute_trend(values):
    if len(values) < 2:
        return "stable ➖", 0.0
    diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
    slope = sum(diffs) / len(diffs)
    if abs(slope) < 0.01:
        return f"stable ➖ (slope: {slope:.2f})", slope
    elif slope > 0:
        return f"increasing 📈 (slope: {slope:.2f})", slope
    else:
        return f"decreasing 📉 (slope: {slope:.2f})", slope

def format_single_latest(row):
    return (
        f"📊 Latest data (at {row['timestamp']}):\n"
        f"- Temperature: {row['temperature']} °C\n"
        f"- Vibration: {row['vibration']} mm/s\n"
        f"- Pressure: {row['pressure']} bar\n"
        f"- RPM: {row['rpm']}\n"
        f"- Current: {row['current']} A\n"
        f"- Voltage: {row['voltage']} V\n"
    )

def format_multiple_readings(rows):
    answer = f"📈 Last {len(rows)} readings:\n"
    for r in rows:
        answer += (
            f"{r['timestamp']} → Temp: {r['temperature']}, Vib: {r['vibration']}, "
            f"Pres: {r['pressure']}, RPM: {r['rpm']}, Cur: {r['current']}, Volt: {r['voltage']}\n"
        )
    return answer

def parse_number_from_query(query, default=5):
    match = re.search(r"last\s+(\d+)", query.lower())
    return int(match.group(1)) if match else default

def parse_date_range(query):
    match = re.search(r"between (\w+ \d+) and (\w+ \d+)", query.lower())
    if match:
        try:
            start = datetime.strptime(match.group(1), "%b %d")
            end = datetime.strptime(match.group(2), "%b %d")
            year = datetime.now().year
            start = start.replace(year=year)
            end = end.replace(year=year)
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        except:
            return None, None
    return None, None

def extract_machine_id(query: str):
    match = re.search(r"machine\s*(\d+)", query.lower())
    return int(match.group(1)) if match else 1  # default → Machine 1

# ---------------- CLASSIFICATION ----------------
def classify_query(query: str):
    q = query.lower()
    if any(w in q for w in ["predict", "failure", "rul", "remaining useful life", "how long", "when will", "life"]):
        return "prediction"
    if any(w in q for w in ["which machine", "highest risk", "most likely"]):
        return "comparison"
    if any(w in q for w in ["steps", "reduce", "maintenance", "manual", "troubleshooting", "overheating", "guide", "advice"]):
        return "knowledge"
    return "general"

# ---------------- RUL PREDICTION ----------------
def predict_failure(row_values, metric="vibration", threshold=30, window=100, logging_interval_sec=10):
    if len(row_values) < 2:
        return f"⚠️ Cannot predict failure for {metric} — insufficient data."

    recent = row_values[-window:] if len(row_values) > window else row_values
    trend = (recent[-1] - recent[0]) / len(recent)

    if trend <= 0:
        return f"{metric.capitalize()}: ✅ Stable — no failure predicted soon."

    readings_to_failure = (threshold - recent[-1]) / trend
    if readings_to_failure <= 0:
        return f"{metric.capitalize()}: ⚠️ Already near or past failure threshold!"

    total_seconds = readings_to_failure * logging_interval_sec
    hours = total_seconds / 3600
    days = hours / 24

    if readings_to_failure > 5000:
        return f"{metric.capitalize()}: Looks healthy — no failure expected within next 5000 readings (~{int(days)} days)."

    return (
        f"{metric.capitalize()}: Predicted failure in ~{int(readings_to_failure)} readings "
        f"(~{hours:.1f} hrs, ~{days:.1f} days) based on last {len(recent)} readings."
    )

# ---------------- MACHINE COMPARISON ----------------
def compare_machines():
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT machine_id, vibration FROM machine_sensor_data ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "⚠️ No machine data available."

    trends = {}
    df_by_machine = {}
    for r in rows:
        m_id = r["machine_id"]
        df_by_machine.setdefault(m_id, []).append(r["vibration"])

    for m_id, values in df_by_machine.items():
        if len(values) > 2:
            trend = (values[0] - values[-1]) / len(values)
            trends[m_id] = trend

    if not trends:
        return "⚠️ Not enough data to compare machines."

    worst = max(trends, key=trends.get)
    return f"⚠️ Machine {worst} shows the steepest vibration increase → most likely to fail soon."

# ---------------- TREND ANALYSIS ----------------
def get_trend_analysis(rows, param=None):
    if not rows:
        return "⚠️ No data available for trend analysis."
    latest = rows[-1]
    metrics = ["temperature", "vibration", "pressure", "rpm", "current", "voltage"]
    trends = []
    for metric in metrics:
        if param and metric not in param:
            continue
        values = [r[metric] for r in rows]
        desc, slope = compute_trend(values)
        trends.append(f"{metric.capitalize()}: {desc}, latest = {latest[metric]}")
    return "📊 Trend Analysis:\n" + "\n".join(trends)

# ---------------- MAIN RESPONSE LOGIC ----------------
# ---------------- MAIN RESPONSE LOGIC ----------------
# ---------------- MAIN RESPONSE LOGIC ----------------
# ---------------- MAIN RESPONSE LOGIC ----------------
def get_rag_response(query: str, machine_id: int = None):
    q_lower = query.lower().strip()

    # ---------------- Dashboard Shortcut ----------------
    if any(word in q_lower for word in ["dashboard", "show me the dashboard", "open dashboard"]):
        machine_id_int = extract_machine_id(query if machine_id is None else str(machine_id))
        rows = get_readings(machine_id_int, n=5)
        alerts = []
        mini_summary = ""
        if rows:
            latest = rows[-1]
            if any(r["vibration"] > 30 for r in rows):
                alerts.append(f"⚠️ Vibration exceeded 30 at {latest['timestamp']}")
            if any(r["temperature"] > 120 for r in rows):
                alerts.append(f"⚠️ Temperature exceeded 120°C at {latest['timestamp']}")
            mini_summary = (
                f"📊 Latest readings for Machine {machine_id_int}:\n"
                f"- Temp: {latest['temperature']} °C, Vib: {latest['vibration']}, "
                f"Pres: {latest['pressure']}, RPM: {latest['rpm']}, "
                f"Cur: {latest['current']} A, Volt: {latest['voltage']} V"
            )
        return {
            "answer": f"{mini_summary}\n\n📊 View full interactive dashboard: http://localhost:8501",
            "alerts": alerts,
            "sources": []
        }

    # ---------------- List Available Tasks ----------------
    if any(phrase in q_lower for phrase in ["what tasks can you do", "what can you do", "help", "capabilities"]):
        return {
            "answer": (
                "🤖 I can help you with:\n"
                "1. Show latest or past sensor readings 📊\n"
                "2. Analyze trends (temperature, vibration, etc.) 📈\n"
                "3. Predict failures and estimate remaining useful life ⏳\n"
                "4. Compare machines to identify risks ⚖️\n"
                "5. Provide machine details and manuals 🏭\n"
                "6. Answer maintenance and troubleshooting questions 📘\n"
                "7. Open the interactive dashboard with live charts 📊"
            ),
            "alerts": [],
            "sources": []
        }

    # ---------------- Machine Details (via RAG) ----------------
    if ("details" in q_lower and "machine" in q_lower) or \
       any(phrase in q_lower for phrase in ["tell me about machine", "info on machine"]):
        try:
            result = qa_chain.invoke(query)
            answer = result["result"]
            sources = [doc.metadata.get("source", "Unknown") for doc in result["source_documents"]]
            return {"answer": answer, "alerts": [], "sources": sources}
        except Exception:
            return {"answer": llm.predict(f"Answer this machine details query: {query}"), "alerts": [], "sources": []}

    # ---------------- Specific Machine Field Query (via RAG) ----------------
    if any(word in q_lower for word in ["manufacturer", "location", "name", "type", "install date"]):
        try:
            result = qa_chain.invoke(query)
            answer = result["result"]
            sources = [doc.metadata.get("source", "Unknown") for doc in result["source_documents"]]
            return {"answer": answer, "alerts": [], "sources": sources}
        except Exception:
            return {"answer": llm.predict(f"Answer this machine details query: {query}"), "alerts": [], "sources": []}

    # ---------------- Conversational ----------------
    if any(re.search(rf"\b{word}\b", q_lower) for word in ["hi", "hello", "hey"]):
        return {"answer": "👋 Hello! How can I help you with your machines today?", "alerts": [], "sources": []}
    if any(re.search(rf"\b{word}\b", q_lower) for word in ["thanks", "thank you", "thx"]):
        return {"answer": "😊 You're welcome! Happy to help.", "alerts": [], "sources": []}

    # ---------------- Query classification ----------------
    query_type = classify_query(query)
    machine_id_int = extract_machine_id(query if machine_id is None else str(machine_id))
    n = parse_number_from_query(query, default=None)
    start_date, end_date = parse_date_range(query)

    rows = get_readings(machine_id_int, n=n, start_date=start_date, end_date=end_date)
    alerts = []
    if rows:
        if any(r["vibration"] > 30 for r in rows):
            alerts.append("⚠️ Vibration exceeded 30!")
        if any(r["temperature"] > 120 for r in rows):
            alerts.append("⚠️ Temperature exceeded 120°C!")

    # ---------------- Prediction ----------------
    if query_type == "prediction":
        if not rows:
            return {"answer": f"⚠️ No data for Machine {machine_id_int}", "alerts": [], "sources": []}
        thresholds = {"temperature": 120, "vibration": 30, "pressure": 10}
        results = []
        for metric, threshold in thresholds.items():
            values = [r[metric] for r in rows]
            if values:
                results.append(predict_failure(values, metric, threshold))
        results.append(get_trend_analysis(rows))
        return {"answer": "\n".join(results), "alerts": alerts, "sources": ["MySQL: machine_sensor_data"]}

    # ---------------- Comparison ----------------
    elif query_type == "comparison":
        return {"answer": compare_machines(), "alerts": alerts, "sources": ["MySQL: machine_sensor_data"]}

    # ---------------- Knowledge (maintenance, troubleshooting, manuals) ----------------
    elif query_type == "knowledge":
        try:
            result = qa_chain.invoke(query)
            answer = result["result"]
            sources = [doc.metadata.get("source", "Unknown") for doc in result["source_documents"]]
            return {"answer": answer, "alerts": alerts, "sources": sources}
        except Exception:
            return {"answer": llm.predict(f"Answer this machine-related question: {query}"), "alerts": alerts, "sources": []}

    # ---------------- Latest readings ----------------
    if "latest" in q_lower or "current" in q_lower:
        return {"answer": format_single_latest(rows[-1]), "alerts": alerts, "sources": ["MySQL: machine_sensor_data"]}
    if "last" in q_lower and "reading" in q_lower:
        return {"answer": format_multiple_readings(rows), "alerts": alerts, "sources": ["MySQL: machine_sensor_data"]}

    # ---------------- Trend queries ----------------
    trend_params = []
    for metric in ["temperature", "vibration", "pressure", "rpm", "current", "voltage"]:
        if metric in q_lower:
            trend_params.append(metric)
    if "trend" in q_lower or trend_params:
        param_list = trend_params if trend_params else None
        return {"answer": get_trend_analysis(rows, param=param_list), "alerts": alerts, "sources": ["MySQL: machine_sensor_data"]}

    # ---------------- Default fallback ----------------
    return {"answer": "🤖 I can answer about sensor data, machine details, failure prediction, trends, and maintenance advice.", "alerts": alerts, "sources": []}
