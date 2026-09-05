from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Transaction(BaseModel):
    txn_id: str
    date: str
    payee: str
    amount: float
    channel: str
    description: Optional[str] = ""


class Payee(BaseModel):
    payee_id: str
    name: str
    added_date: str


class Customer(BaseModel):
    customer_id: str
    name: str
    account_type: str
    established_days: int
    avg_monthly_spend: float
    typical_channels: List[str] = Field(default_factory=list)


class CaseData(BaseModel):
    case_id: str
    customer: Customer
    payees: List[Payee] = Field(default_factory=list)
    transactions: List[Transaction] = Field(default_factory=list)


class RiskRule(BaseModel):
    rule_id: str
    rule_name: str
    description: str
    severity: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class DeterministicFinding(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    triggered: bool
    cited_transaction_ids: List[str] = Field(default_factory=list)
    explanation: str
    baseline_comparison: str


class ReportFinding(BaseModel):
    finding_id: str
    rule_triggered: str
    severity: str
    cited_transaction_ids: List[str]
    summary: str
    difference_from_normal: str
    investigator_action: str


class InvestigationReport(BaseModel):
    case_id: str
    customer_id: str
    customer_name: str
    needs_attention: bool
    risk_score: int = Field(description="Score from 0 (routine) to 100 (high risk)")
    executive_summary: str
    findings: List[ReportFinding] = Field(default_factory=list)
    null_case_reasoning: Optional[str] = None
    investigator_guidance: str
    disclaimer: str = Field(
        default="This report presents evidence and pattern deviations for human investigator review. The system does NOT conclude that fraud has occurred."
    )
    analysis_mode: str = "Grounded Hybrid (Deterministic + Gemini 3.5 Flash Lite)"
