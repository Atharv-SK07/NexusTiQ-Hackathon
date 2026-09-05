from datetime import datetime, timedelta
from typing import List, Dict
from src.models import CaseData, RiskRule, DeterministicFinding, Transaction


class RulesEngine:
    def __init__(self, rules: List[RiskRule]):
        self.rules = {r.rule_id: r for r in rules}

    def evaluate(self, case: CaseData) -> List[DeterministicFinding]:
        findings = []

        txns = case.transactions
        customer = case.customer
        total_txns = len(txns)

        if total_txns == 0:
            return findings

        amounts = [t.amount for t in txns]
        avg_txn_amount = sum(amounts) / total_txns if total_txns > 0 else 0.0

        # -------------------------------------------------------------
        # Rule 1: Unusually Large Transfer (HIGH)
        # -------------------------------------------------------------
        rule_1 = self.rules.get("RULE_01_LARGE_TRANSFER")
        if rule_1:
            abs_thresh = rule_1.parameters.get("absolute_threshold", 150000.0)
            mult_thresh = rule_1.parameters.get("multiplier_threshold", 3.5)
            
            flagged_txns = []
            explanations = []
            for t in txns:
                is_abs_large = t.amount >= abs_thresh
                is_mult_large = avg_txn_amount > 0 and (t.amount >= mult_thresh * avg_txn_amount)
                
                if is_abs_large or is_mult_large:
                    flagged_txns.append(t.txn_id)
                    reason = f"₹{t.amount:,.2f} to {t.payee}"
                    if is_abs_large:
                        reason += f" exceeds absolute threshold of ₹{abs_thresh:,.2f}"
                    if is_mult_large:
                        reason += f" is {t.amount / avg_txn_amount:.1f}x higher than customer baseline average (₹{avg_txn_amount:,.2f})"
                    explanations.append(reason)

            if flagged_txns:
                findings.append(DeterministicFinding(
                    rule_id=rule_1.rule_id,
                    rule_name=rule_1.rule_name,
                    severity=rule_1.severity,
                    triggered=True,
                    cited_transaction_ids=flagged_txns,
                    explanation="; ".join(explanations),
                    baseline_comparison=f"Customer typical single transaction average is ₹{avg_txn_amount:,.2f} across history."
                ))

        # -------------------------------------------------------------
        # Rule 2: Rapid Payments to New Payee (HIGH)
        # -------------------------------------------------------------
        rule_2 = self.rules.get("RULE_02_NEW_PAYEE_BURST")
        if rule_2:
            payee_age_days = rule_2.parameters.get("payee_age_days", 7)
            burst_count_thresh = rule_2.parameters.get("burst_count_threshold", 3)
            window_hours = rule_2.parameters.get("window_hours", 24)

            payee_added_map = {p.name.lower(): p.added_date for p in case.payees}
            
            payee_txns: Dict[str, List[Transaction]] = {}
            for t in txns:
                payee_name = t.payee
                payee_txns.setdefault(payee_name, []).append(t)

            flagged_txns_r2 = []
            r2_explanations = []

            for payee_name, p_txns in payee_txns.items():
                added_date_str = payee_added_map.get(payee_name.lower())
                if not added_date_str:
                    continue
                
                try:
                    added_date = datetime.strptime(added_date_str, "%Y-%m-%d")
                except ValueError:
                    continue

                recent_txns = []
                for t in p_txns:
                    try:
                        t_date = datetime.strptime(t.date, "%Y-%m-%d %H:%M:%S")
                        days_since_added = (t_date - added_date).days
                        if 0 <= days_since_added <= payee_age_days:
                            recent_txns.append((t, t_date))
                    except ValueError:
                        continue

                if len(recent_txns) >= burst_count_thresh:
                    recent_txns.sort(key=lambda x: x[1])
                    for i in range(len(recent_txns)):
                        window_txns = [recent_txns[i]]
                        for j in range(i + 1, len(recent_txns)):
                            if (recent_txns[j][1] - recent_txns[i][1]).total_seconds() <= window_hours * 3600:
                                window_txns.append(recent_txns[j])
                        
                        if len(window_txns) >= burst_count_thresh:
                            ids = [x[0].txn_id for x in window_txns]
                            for tid in ids:
                                if tid not in flagged_txns_r2:
                                    flagged_txns_r2.append(tid)
                            
                            total_burst_val = sum(x[0].amount for x in window_txns)
                            r2_explanations.append(
                                f"{len(window_txns)} transactions totaling ₹{total_burst_val:,.2f} sent to '{payee_name}' "
                                f"(registered on {added_date_str}) within a {window_hours}-hour period."
                            )
                            break

            if flagged_txns_r2:
                findings.append(DeterministicFinding(
                    rule_id=rule_2.rule_id,
                    rule_name=rule_2.rule_name,
                    severity=rule_2.severity,
                    triggered=True,
                    cited_transaction_ids=flagged_txns_r2,
                    explanation="; ".join(r2_explanations),
                    baseline_comparison=f"Normal pattern shows long-standing registered payees with spread out payments."
                ))

        # -------------------------------------------------------------
        # Rule 3: Odd-Hours High-Value Activity (MEDIUM)
        # -------------------------------------------------------------
        rule_3 = self.rules.get("RULE_03_ODD_HOURS_ACTIVITY")
        if rule_3:
            start_h = rule_3.parameters.get("start_hour", 1)
            end_h = rule_3.parameters.get("end_hour", 4)
            min_amt = rule_3.parameters.get("min_amount", 50000.0)

            flagged_txns_r3 = []
            r3_explanations = []

            for t in txns:
                try:
                    t_time = datetime.strptime(t.date, "%Y-%m-%d %H:%M:%S")
                    if start_h <= t_time.hour <= end_h and t.amount >= min_amt:
                        flagged_txns_r3.append(t.txn_id)
                        r3_explanations.append(
                            f"Transaction {t.txn_id} of ₹{t.amount:,.2f} occurred at {t_time.strftime('%H:%M:%S')} (between {start_h:02d}:00 and {end_h:02d}:50 IST)."
                        )
                except ValueError:
                    continue

            if flagged_txns_r3:
                findings.append(DeterministicFinding(
                    rule_id=rule_3.rule_id,
                    rule_name=rule_3.rule_name,
                    severity=rule_3.severity,
                    triggered=True,
                    cited_transaction_ids=flagged_txns_r3,
                    explanation="; ".join(r3_explanations),
                    baseline_comparison="Customer regular transaction hours are daytime/evening business hours."
                ))

        # -------------------------------------------------------------
        # Rule 4: Behavioral Pattern Break (MEDIUM)
        # -------------------------------------------------------------
        rule_4 = self.rules.get("RULE_04_PATTERN_SHIFT")
        if rule_4:
            typical_ch = [c.lower() for c in customer.typical_channels]
            flagged_txns_r4 = []
            r4_explanations = []

            for t in txns:
                if typical_ch and t.channel.lower() not in typical_ch:
                    flagged_txns_r4.append(t.txn_id)
                    r4_explanations.append(
                        f"Transaction {t.txn_id} used uncharacteristic channel '{t.channel}' (customer typical channels: {', '.join(customer.typical_channels)})."
                    )

            if flagged_txns_r4:
                findings.append(DeterministicFinding(
                    rule_id=rule_4.rule_id,
                    rule_name=rule_4.rule_name,
                    severity=rule_4.severity,
                    triggered=True,
                    cited_transaction_ids=flagged_txns_r4,
                    explanation="; ".join(r4_explanations),
                    baseline_comparison=f"Customer established channel preferences: {', '.join(customer.typical_channels)}."
                ))

        # -------------------------------------------------------------
        # Rule 5: Minor Spend Variance (LOW)
        # -------------------------------------------------------------
        rule_5 = self.rules.get("RULE_05_MINOR_SPEND_VARIANCE")
        if rule_5 and not rule_1_triggered(findings):
            min_m = rule_5.parameters.get("min_multiplier", 2.0)
            max_m = rule_5.parameters.get("max_multiplier", 3.4)
            flagged_txns_r5 = []
            r5_explanations = []

            for t in txns:
                if avg_txn_amount > 0 and (min_m * avg_txn_amount <= t.amount <= max_m * avg_txn_amount):
                    flagged_txns_r5.append(t.txn_id)
                    r5_explanations.append(
                        f"Transaction {t.txn_id} of ₹{t.amount:,.2f} is {t.amount / avg_txn_amount:.1f}x customer average (between 2.0x and 3.4x)."
                    )

            if flagged_txns_r5:
                findings.append(DeterministicFinding(
                    rule_id=rule_5.rule_id,
                    rule_name=rule_5.rule_name,
                    severity=rule_5.severity,
                    triggered=True,
                    cited_transaction_ids=flagged_txns_r5,
                    explanation="; ".join(r5_explanations),
                    baseline_comparison=f"Customer typical transaction size is ₹{avg_txn_amount:,.2f}."
                ))

        return findings


def rule_1_triggered(findings: List[DeterministicFinding]) -> bool:
    return any(f.rule_id == "RULE_01_LARGE_TRANSFER" for f in findings)
