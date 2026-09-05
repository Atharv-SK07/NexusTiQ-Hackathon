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
1. NULL CASE HANDLING: If zero risk rules were triggered and all transactions fall within normal customer behavior, set `needs_attention` to `false`, set `risk_score` to a low value (0 to 15), leave `findings` empty, and provide a clear `null_case_reasoning` explaining that the activity is routine.
2. GROUNDED CITATIONS: For every finding when `needs_attention` is true, you MUST cite the exact `txn_id`s from the input data. Do not invent transaction IDs.
3. FRAUD DISCLAIMER: You must NEVER state or imply that fraud has occurred. You present evidence, explain deviations from baseline, and explicitly hand judgment to the human investigator.
4. STRUCTURED RESPONSE: Return only valid JSON conforming strictly to the requested schema.
"""


class AIInvestigator:
    def __init__(self, model_name: str = "gemini-3.5-flash-lite"):
        self.model_name = model_name
        self.api_key = os.environ.get("GEMINI_API_KEY", "")

    def generate_report(
        self, case: CaseData, deterministic_findings: List[DeterministicFinding]
    ) -> InvestigationReport:
        # Check if API key is available
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found in environment. Utilizing deterministic fallback synthesis.")
            return self._fallback_synthesis(case, deterministic_findings, "GEMINI_API_KEY not configured in environment.")

        try:
            from google import genai
            from google.genai import types

            client = genai.Client()
            prompt = self._build_prompt(case, deterministic_findings)

            # Try generating content with structured schema
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
                    return InvestigationReport(**parsed_json)
            except Exception as e:
                logger.warning(f"Attempt with model {self.model_name} failed: {e}. Trying gemini-2.5-flash fallback.")
                # Fallback model attempt
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
                    return InvestigationReport(**parsed_json)

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
        
        if not needs_attention:
            return InvestigationReport(
                case_id=case.case_id,
                customer_id=case.customer.customer_id,
                customer_name=case.customer.name,
                needs_attention=False,
                risk_score=5,
                executive_summary=f"Routine transaction history for {case.customer.name}. All {len(case.transactions)} transactions conform to established baseline spending patterns.",
                findings=[],
                null_case_reasoning="No risk rules were triggered. Transaction amounts, velocity, payee dates, and payment channels are consistent with normal account activity.",
                investigator_guidance="No action required. File case as routine audit pass.",
                analysis_mode=f"Deterministic Fallback ({reason})"
            )

        report_findings = []
        max_severity = "LOW"
        all_cited_ids = []

        for idx, df in enumerate(deterministic_findings, 1):
            if df.severity == "HIGH":
                max_severity = "HIGH"
            elif df.severity == "MEDIUM" and max_severity != "HIGH":
                max_severity = "MEDIUM"

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

        score = 85 if max_severity == "HIGH" else 55

        return InvestigationReport(
            case_id=case.case_id,
            customer_id=case.customer.customer_id,
            customer_name=case.customer.name,
            needs_attention=True,
            risk_score=score,
            executive_summary=f"Investigation flagged {len(deterministic_findings)} risk indicator(s) for customer {case.customer.name}. Cited transaction(s): {', '.join(set(all_cited_ids))}.",
            findings=report_findings,
            null_case_reasoning=None,
            investigator_guidance="Review cited transactions with priority. Verify whether recent payee additions or high-value transfers were customer-initiated.",
            analysis_mode=f"Deterministic Fallback ({reason})"
        )
