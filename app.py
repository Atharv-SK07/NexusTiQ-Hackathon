import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Auto-load local .env if present (hackathon evaluator supplies GEMINI_API_KEY via env)
load_dotenv()

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.models import CaseData, InvestigationReport
from src.rules_engine import RulesEngine
from src.ai_investigator import AIInvestigator
from src.data_loader import load_risk_rules, load_sample_cases, load_sample_case_by_id

# Initialize FastAPI App
app = FastAPI(
    title="Banking Transaction Risk Investigation Assistant",
    description="NexusTiq24 Hackathon Project (TRACK_ID=PS06)",
    version="1.0.0"
)

# Load startup data
RULES = load_risk_rules()
SAMPLE_CASES = load_sample_cases()
RULES_ENGINE = RulesEngine(RULES)
AI_INVESTIGATOR = AIInvestigator(model_name="gemini-3.5-flash-lite")

# Mount Static Files & Frontend
frontend_dir = BASE_DIR / "frontend"
static_dir = frontend_dir / "static"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def serve_index():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"message": "NexusTiq24 PS06 Backend Active. Frontend index.html missing."})


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "track_id": "PS06",
        "rules_loaded": len(RULES),
        "cases_loaded": len(SAMPLE_CASES),
        "api_key_configured": bool(os.environ.get("GEMINI_API_KEY"))
    }


@app.get("/api/rules")
async def get_rules():
    return [r.model_dump() for r in RULES]


@app.get("/api/cases")
async def list_cases():
    return [
        {
            "case_id": c.case_id,
            "customer_id": c.customer.customer_id,
            "customer_name": c.customer.name,
            "txn_count": len(c.transactions)
        }
        for c in SAMPLE_CASES.values()
    ]


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str):
    case = load_sample_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return case.model_dump()


@app.post("/api/investigate", response_model=InvestigationReport)
async def investigate_case(case: CaseData):
    try:
        # Step 1: Run deterministic rules evaluation engine
        deterministic_findings = RULES_ENGINE.evaluate(case)

        # Step 2: Run Gemini 3.5 Flash Lite grounded synthesis engine
        report = AI_INVESTIGATOR.generate_report(case, deterministic_findings)
        
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Investigation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("\n==================================================================")
    print("🚀 NexusTiq24 Banking Risk Assistant (TRACK_ID=PS06) is Live!")
    print("👉 Open in Browser: http://localhost:8000")
    print("==================================================================\n")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)

