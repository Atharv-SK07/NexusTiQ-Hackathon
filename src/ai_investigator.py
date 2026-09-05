import os
import json
import logging
from typing import List, Optional
from src.models import (
    CaseData,
    DeterministicFinding,
    InvestigationReport,
    ReportFinding
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior banking fraud desk investigation assistant.
Your task is to analyze a customer's transaction history against standard risk rules and deterministic findings, and produce a grounded, highly traceable Investigation Report.

CRITICAL CONSTRAINTS & RULES:
1. NULL CASE HANDLING: If zero risk rules were triggered and all transactions fall within normal customer behavior, set `needs_attention` to `false`, set `risk_score` to 5, leave `findings` empty, and provide a clear `null_case_reasoning` explaining that the activity is routine.
2. ADDITIVE RISK SCORING: Calculate `risk_score` deterministically as:
   - Base score: 5 points
   - Each distinct HIGH severity rule triggered: +40 points
   - Each distinct MEDIUM severity rule triggered: +20 points
   - Each distinct LOW severity rule triggered: +10 points
   - Cap `risk_score` at a maximum of 100.
3. GROUNDED CITATIONS: For every finding when `needs_attention` is true, you MUST cite the exact `txn_id`s from the input data. Do not invent transaction IDs.
4. CURRENCY FORMATTING: Format Indian Rupee currency figures clearly as `₹` (e.g. `₹68,000.00` or `₹4,80,000.00`).
5. FRAUD DISCLAIMER: You must NEVER state or imply that fraud has occurred. You present evidence, explain deviations from baseline, and explicitly hand judgment to the human investigator.
6. STRUCTURED RESPONSE: Return only valid JSON conforming strictly to the requested schema.
"""


class AIInvestigator:
    def __init__(self, model_name: str = "gemini-3.5-flash-lite"):
        self.model_name = model_name
        self.api_key = os.environ.get("GEMINI_API_KEY", "")

    def calculate_risk_score(self, deterministic_findings: List[DeterministicFinding]) -> int:
        """Additive risk score calculation: Base 5 + HIGH(40) + MEDIUM(20) + LOW(10), capped at 100."""
        if not deterministic_findings:
            return 5

        score = 5
        seen_rules = set()

        for df in deterministic_findings:
            if df.rule_id in seen_rules:
                continue
            seen_rules.add(df.rule_id)

            if df.severity == "HIGH":
                score += 40
            elif df.severity == "MEDIUM":
                score += 20
            elif df.severity == "LOW":
                score += 10

        return min(100, score)

    def generate_report(
        self, case: CaseData, deterministic_findings: List[DeterministicFinding]
    ) -> InvestigationReport:
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found in environment. Utilizing deterministic fallback synthesis.")
            return self._fallback_synthesis(case, deterministic_findings, "GEMINI_API_KEY not configured in environment.")

        try:
            from google import genai
            from google.genai import types

            client = genai.Client()
            prompt = self._build_prompt(case, deterministic_findings)

            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=InvestigationReport,
                        temperature=0.1,
                    )
                )
                
                if response.text:
                    parsed_json = json.loads(response.text)
                    report = InvestigationReport(**parsed_json)
                    # Enforce exact additive risk score formula
                    report.risk_score = self.calculate_risk_score(deterministic_findings)
                    return report
            except Exception as e:
                logger.warning(f"Attempt with model {self.model_name} failed: {e}. Trying gemini-2.5-flash fallback.")
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=InvestigationReport,
                        temperature=0.1,
                    )
                )
                if response.text:
                    parsed_json = json.loads(response.text)
                    report = InvestigationReport(**parsed_json)
                    report.risk_score = self.calculate_risk_score(deterministic_findings)
                    return report

        except Exception as err:
            logger.error(f"Gemini API call failed: {err}. Falling back to deterministic report builder.")
            return self._fallback_synthesis(case, deterministic_findings, f"API Error: {str(err)}")

        return self._fallback_synthesis(case, deterministic_findings, "Direct synthesis fallback triggered.")

    def _build_prompt(self, case: CaseData, deterministic_findings: List[DeterministicFinding]) -> str:
        prompt_dict = {
            "case_id": case.case_id,
            "customer_profile": case.customer.model_dump(),
            "payee_directory": [p.model_dump() for p in case.payees],
            "transaction_history": [t.model_dump() for t in case.transactions],
            "deterministic_rule_engine_findings": [f.model_dump() for f in deterministic_findings]
        }
        return f"Analyze the following customer transaction case and produce an Investigation Report:\n{json.dumps(prompt_dict, indent=2)}"

    def _fallback_synthesis(
        self, case: CaseData, deterministic_findings: List[DeterministicFinding], reason: str
    ) -> InvestigationReport:
        """Deterministic fallback that constructs a valid InvestigationReport when Gemini API is unavailable."""
        needs_attention = len(deterministic_findings) > 0
        score = self.calculate_risk_score(deterministic_findings)
        
        if not needs_attention:
            return InvestigationReport(
                case_id=case.case_id,
                customer_id=case.customer.customer_id,
                customer_name=case.customer.name,
                needs_attention=False,
                risk_score=score,
                executive_summary=f"Routine transaction history for {case.customer.name}. All {len(case.transactions)} transactions conform to established baseline spending patterns.",
                findings=[],
                null_case_reasoning="No risk rules were triggered. Transaction amounts, velocity, payee dates, and payment channels are consistent with normal account activity.",
                investigator_guidance="No action required. File case as routine audit pass.",
                analysis_mode=f"Deterministic Rule-Based Engine ({reason})"
            )

        report_findings = []
        all_cited_ids = []

        for idx, df in enumerate(deterministic_findings, 1):
            all_cited_ids.extend(df.cited_transaction_ids)

            report_findings.append(ReportFinding(
                finding_id=f"FINDING_{idx:02d}",
                rule_triggered=f"{df.rule_id} ({df.rule_name})",
                severity=df.severity,
                cited_transaction_ids=df.cited_transaction_ids,
                summary=df.explanation,
                difference_from_normal=df.baseline_comparison,
                investigator_action=f"Review transaction(s) {', '.join(df.cited_transaction_ids)} against account history and contact customer if unconfirmed."
            ))

        return InvestigationReport(
            case_id=case.case_id,
            customer_id=case.customer.customer_id,
            customer_name=case.customer.name,
            needs_attention=True,
            risk_score=score,
            executive_summary=f"Investigation flagged {len(deterministic_findings)} risk indicator(s) for customer {case.customer.name}. Computed risk score: {score}/100 based on additive rule severity. Cited transaction(s): {', '.join(set(all_cited_ids))}.",
            findings=report_findings,
            null_case_reasoning=None,
            investigator_guidance="Review cited transactions with priority. Verify whether recent payee additions or high-value transfers were customer-initiated.",
            analysis_mode=f"Deterministic Rule-Based Engine ({reason})"
        )
