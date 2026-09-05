import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from src.models import RiskRule, CaseData

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def load_risk_rules() -> List[RiskRule]:
    rules_path = DATA_DIR / "rules.json"
    if not rules_path.exists():
        return []
    
    with open(rules_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return [RiskRule(**r) for r in data.get("rules", [])]


def load_sample_cases() -> Dict[str, CaseData]:
    cases_dir = DATA_DIR / "sample_cases"
    cases = {}
    
    if not cases_dir.exists():
        return cases

    for file_path in cases_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                case = CaseData(**data)
                cases[case.case_id] = case
        except Exception as e:
            print(f"Error loading sample case {file_path}: {e}")

    return cases


def load_sample_case_by_id(case_id: str) -> Optional[CaseData]:
    cases = load_sample_cases()
    return cases.get(case_id)
