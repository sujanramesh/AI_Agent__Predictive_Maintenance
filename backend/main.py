from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from rag_agent import get_rag_response
import os

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Serve static plots ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_plot_dir = os.path.join(BASE_DIR, "static", "plots")
os.makedirs(static_plot_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# ---------------- Input Model ----------------
class Query(BaseModel):
    question: str
    machine_id: str = "1"

# ---------------- API Endpoints ----------------
@app.post("/ask")
async def ask_agent(query: Query):
    try:
        # Pass machine_id exactly as provided
        response = get_rag_response(query.question, machine_id=query.machine_id)
        return {
            "answer": response.get("answer", ""),
            "sources": response.get("sources", []),
            "alerts": response.get("alerts", []),
            "chart_url": response.get("chart", None)
        }
    except Exception as e:
        return {
            "answer": f"⚠️ Error processing your request: {e}",
            "sources": [],
            "alerts": [],
            "chart_url": None
        }

@app.get("/")
async def root():
    return {"status": "AI chatbot with live MySQL + PDF + Graph + Alerts integration ✅"}
