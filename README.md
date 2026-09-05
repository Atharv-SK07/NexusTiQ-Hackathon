TRACK_ID=PS06

# NexusSentinel AI - Banking Transaction Risk Investigation Assistant

An intelligent, grounded fraud investigation assistant for a bank's fraud desk built for **NexusTiq24 (TRACK_ID=PS06)**.

The system analyzes customer transaction history over several months against standard banking risk rules (unusually large transfers, rapid payments to newly registered payees, odd-hours high-value transfers, and behavioral channel breaks). It combines a deterministic rule engine with Gemini 3.5 Flash Lite (`google-genai` SDK) to generate grounded, traceable investigation reports.

## Demo Video Link
- **Demo Video**: [Insert Your 5-Minute YouTube / Loom Demo Link Here]

## Key Features
- **Deterministic Rule Verification**: Flags specific transactions based on quantifiable risk thresholds.
- **Additive Risk Score Engine**: Calculates auditable risk scores (Base 5 + High: 40 + Medium: 20 + Low: 10, capped at 100) that scale dynamically with rule severity.
- **Grounded AI Synthesis**: Uses Gemini 3.5 Flash Lite (`google-genai` SDK) to synthesize findings with mandatory citations to input transaction IDs and baseline deviations in INR (₹).
- **Null Case & Borderline Handling**: Identifies routine customer histories (0 false positives on Case 01) and handles mild/ambiguous cases (Case 05) proportionately.
- **Human-in-the-Loop Safeguards**: Strictly adheres to the rule that the system **never declares fraud** — it flags evidence, explains differences from normal behavior, and hands judgment to the human investigator.
- **Interactive UI**: Single-page web dashboard served on `http://localhost:8000`.

## Quick Start (One Command)

1. **Run the application** (installs dependencies & starts server on port 8000):
   ```bash
   pip install -r requirements.txt
   python app.py
   ```

2. **Open your browser** at **`http://localhost:8000`**.

> **Note on API Keys:** The evaluation harness automatically injects `GEMINI_API_KEY` when testing your app. For local testing on your machine, you can optionally set `GEMINI_API_KEY` in your environment or create a `.env` file (see `.env.example`). If no API key is provided, the application runs via deterministic fallback mode without crashing.

## Project Structure
```text
c:\NexusTiQ Hackathon\
├── README.md                 # Line 1: TRACK_ID=PS06
├── requirements.txt          # Dependencies: fastapi, uvicorn, google-genai, pydantic, python-dotenv
├── .env.example              # Environment variable template
├── .gitignore                # Prevents committing .env or virtual environments
├── app.py                    # Entry point: starts FastAPI server on port 8000
├── src/
│   ├── models.py             # Pydantic schemas (Transaction, RiskRule, InvestigationReport)
│   ├── rules_engine.py       # Deterministic rule evaluation logic (INR thresholds)
│   ├── ai_investigator.py    # Gemini 3.5 Flash Lite synthesis engine & additive scoring
│   └── data_loader.py        # Pre-computed dataset and rules loader
├── data/
│   ├── rules.json            # System risk rules definitions
│   └── sample_cases/         # Pre-built test cases (Case 01 to Case 05)
└── frontend/
    ├── index.html            # Web dashboard layout
    └── static/
        ├── app.js            # Frontend interactivity & report rendering
        └── styles.css        # Responsive dark-mode styling
```

## Sample Cases Included
1. **Case 01 - Priya Sharma (Null Case)**: Multi-month routine spending (`₹45,000/mo` baseline) → **Score: 5/100** (Zero Risk Flags).
2. **Case 02 - Aarav Mehta (Payee Burst)**: Rapid transfers totaling `₹2,60,000` to newly registered payee *ZebPay Crypto Exchange* within 24h → **Score: 45/100** (1 High Rule).
3. **Case 03 - Ananya Iyer (Odd-Hours Wire)**: High-value `₹4,80,000` RTGS transfer executed at 02:45 AM → **Score: 85/100** (1 High + 2 Medium Rules).
4. **Case 04 - Rohan Verma (Edge Case Overlap)**: Multiple high-value outbound API transfers totaling `₹11,60,000` → **Score: 100/100** (2 High + 2 Medium Rules).
5. **Case 05 - Vikram Malhotra (Ambiguous Stress Test)**: One-off `₹68,000` laptop purchase via NetBanking → **Score: 35/100** (1 Medium + 1 Low Rule).