TRACK_ID=PS06

# NexusSentinel AI - Banking Transaction Risk Investigation Assistant

An intelligent, grounded fraud investigation assistant for a bank's fraud desk built for **NexusTiq24 (TRACK_ID=PS06)**.

The system analyzes customer transaction history over several months against standard banking risk rules (unusually large transfers, burst payments to newly added payees, odd-hours high-value activity, and behavioral pattern shifts). It combines a deterministic rule engine with Gemini AI to generate grounded, traceable investigation reports.

## Key Features
- **Deterministic Rule Verification**: Flags specific transactions based on quantifiable risk thresholds.
- **Grounded AI Synthesis**: Uses Gemini 3.5 Flash Lite (`google-genai` SDK) to synthesize findings with mandatory citations to input transaction IDs and rule IDs.
- **Null Case Handling**: Identifies routine customer histories and plainly reports "No suspicious activity detected" with zero false positives.
- **Human-in-the-Loop Safeguards**: Strictly adheres to the rule that system **never declares fraud** — it flags evidence, explains differences from normal behavior, and hands judgment to the investigator.
- **Interactive UI**: Web-based investigation dashboard served on `http://localhost:8000`.

## Quick Start (One Command)

1. Set your Gemini API Key environment variable:
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key"
   # On Windows PowerShell:
   # $env:GEMINI_API_KEY="your-gemini-api-key"
   ```

2. Run the application (installs & starts server):
   ```bash
   pip install -r requirements.txt
   python app.py
   ```

3. Open your browser at `http://localhost:8000`.

## Project Structure
- `app.py`: FastAPI server entrypoint running on port 8000.
- `requirements.txt`: Python package dependencies.
- `src/`: Core Python modules (rules engine, AI investigator, schemas, data loader).
- `data/`: System risk rules and pre-built sample test cases.
- `frontend/`: Single Page Web Dashboard UI.

## Sample Cases Included
1. **Case 01 - Routine Account (Null Case)**: Multi-month standard history with zero risk flags.
2. **Case 02 - New Payee Burst**: Multiple rapid transfers to a newly added payee within 24 hours.
3. **Case 03 - Late-Night Large Wire**: High-value transfer executed between 1:00 AM - 4:00 AM outside normal pattern.
4. **Case 04 - Mixed Behavioral Deviation**: Combination of sudden high velocity and unusual transaction channel shift.
