🤖 AI Agent for Predictive Maintenance

This project is an AI-powered predictive maintenance system that integrates real-time machine monitoring, failure prediction, and a RAG (Retrieval-Augmented Generation) knowledge assistant for maintenance and troubleshooting.

It includes:
📊 Interactive Dashboard for monitoring machine health
⚡ Failure Predictions using predictive models
🧠 AI Chatbot with RAG to answer maintenance & troubleshooting questions from manuals
🗄️ Database Integration (MySQL) for machine readings & metadata
🌐 Frontend (HTML/JS) for chatbot interaction

📂 Project Structure

Predictive_Maintenance/
│── backend/                 # AI & backend logic
│   ├── ingest.py             # PDF ingestion & vectorstore creation
│   ├── rag_agent.py          # RAG agent for Q&A
│   ├── main.py               # API entry point
│   ├── db_utils.py           # MySQL utilities
│
│── data/
│   └── User_Manual.pdf       # Knowledge base for RAG
│
│── vectorstore/              # FAISS vector DB for retrieval
│
│── frontend/                 # Frontend (chatbot UI)
│   ├── index.html
│   ├── style.css
│   └── script.js
│
│── dashboard.py              # Streamlit machine monitoring dashboard
│── requirements.txt          # Python dependencies
│── .gitignore                # Ignoring secrets like .env
│── .env.example              # Example env file (without secrets)
│── README.md                 # Project documentation
⚙️ Installation

1️⃣ Clone the Repository
git clone https://github.com/sujanramesh/AI_Agent__Predictive_Maintenance.git
cd AI_Agent__Predictive_Maintenance

2️⃣ Create Virtual Environment
conda create -n predictive_maintain python=3.10 -y
conda activate predictive_maintain
Or using venv:
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Setup Environment Variables
Create a .env file in the project root:
OPENAI_API_KEY=your_api_key_here
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password_here
DB_NAME=ignitiondb

⚠️ Never commit .env. Share .env.example instead.

🚀 Running the Project
1️⃣ Start Backend API
python backend/main.py
2️⃣ Ingest Knowledge Base (PDF → Vectorstore)
python backend/ingest.py
3️⃣ Run Streamlit Dashboard
streamlit run dashboard.py
4️⃣ Open Frontend (Chatbot)
Open frontend/index.html in your browser.

✨ Features
📊 Dashboard:
Real-time machine monitoring
Alerts & thresholds visualization
RUL (Remaining Useful Life) predictions
Machine comparison

🧠 AI Chatbot (RAG):
Answers machine-specific queries
Troubleshooting guidance from manuals
Maintenance procedures

🔒 Safe Development:
.env for secrets
.gitignore included

📖 Example Queries
"Give me the details of machine 1"
"How do I reduce vibration in machine 2?"
"What maintenance steps are needed for a compressor?"
"Show me temperature trend of machine 3"
