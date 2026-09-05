let currentCaseData = null;

document.addEventListener("DOMContentLoaded", () => {
    // Automatically load default Case 01 Routine
    loadCase("CASE_01_ROUTINE");
});

async function loadCase(caseId) {
    // Update button states
    document.querySelectorAll(".case-btn").forEach(btn => btn.classList.remove("active"));
    const activeBtn = Array.from(document.querySelectorAll(".case-btn")).find(b => b.getAttribute("onclick").includes(caseId));
    if (activeBtn) activeBtn.classList.add("active");

    document.getElementById("auditStatus").innerText = `Loading ${caseId}...`;
    document.getElementById("reportCard").classList.add("hidden");

    try {
        const response = await fetch(`/api/cases/${caseId}`);
        if (!response.ok) throw new Error("Failed to load case data");
        
        currentCaseData = await response.json();
        renderCase(currentCaseData);
        document.getElementById("auditStatus").innerText = `Case ${caseId} loaded. Ready to run audit.`;
    } catch (err) {
        document.getElementById("auditStatus").innerText = `Error loading case: ${err.message}`;
    }
}

function renderCase(data) {
    // Customer profile
    document.getElementById("custName").innerText = data.customer.name;
    document.getElementById("custId").innerText = data.customer.customer_id;
    document.getElementById("custType").innerText = data.customer.account_type;
    document.getElementById("custTenure").innerText = `${data.customer.established_days} days`;
    document.getElementById("custSpend").innerText = `₹${data.customer.avg_monthly_spend.toLocaleString('en-IN')}/mo`;
    document.getElementById("custChannels").innerText = data.customer.typical_channels.join(", ");

    // Transactions table
    const tbody = document.getElementById("txnTableBody");
    tbody.innerHTML = "";
    document.getElementById("txnCount").innerText = `${data.transactions.length} Transactions`;

    if (data.transactions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center">No transactions found</td></tr>`;
        return;
    }

    data.transactions.forEach(t => {
        const tr = document.createElement("tr");
        tr.id = `row-${t.txn_id}`;
        tr.innerHTML = `
            <td class="mono"><strong>${t.txn_id}</strong></td>
            <td>${t.date}</td>
            <td><strong>${t.payee}</strong></td>
            <td><span class="mono">${t.channel}</span></td>
            <td>${t.description || '-'}</td>
            <td class="text-right mono"><strong>₹${t.amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong></td>
            <td id="tag-${t.txn_id}"><span class="badge" style="background:#30363d; color:#8b949e">Log Recorded</span></td>
        `;
        tbody.appendChild(tr);
    });
}

async function runInvestigation() {
    if (!currentCaseData) {
        alert("Please select or load a case first.");
        return;
    }

    const btn = document.getElementById("runAuditBtn");
    btn.disabled = true;
    btn.innerText = "⏳ Running Grounded Audit...";
    document.getElementById("auditStatus").innerText = "Evaluating risk rules and calling Gemini synthesis engine...";

    try {
        const response = await fetch("/api/investigate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(currentCaseData)
        });

        if (!response.ok) throw new Error("Investigation request failed.");

        const report = await response.json();
        renderReport(report);
        document.getElementById("auditStatus").innerText = "Audit completed successfully.";
    } catch (err) {
        alert(`Error running audit: ${err.message}`);
        document.getElementById("auditStatus").innerText = "Audit failed.";
    } finally {
        btn.disabled = false;
        btn.innerText = "⚡ Run Investigation Audit";
    }
}

function renderReport(report) {
    const reportCard = document.getElementById("reportCard");
    reportCard.classList.remove("hidden");

    // Analysis Mode
    document.getElementById("analysisModeTag").innerText = report.analysis_mode || "Grounded Engine";

    // Risk Meter
    const scoreElem = document.getElementById("riskScore");
    scoreElem.innerText = `${report.risk_score}/100`;
    scoreElem.className = "score-num";
    if (report.risk_score > 70) scoreElem.classList.add("high-risk");
    else if (report.risk_score > 30) scoreElem.classList.add("med-risk");

    // Status Banner
    const banner = document.getElementById("statusBanner");
    const bannerIcon = document.getElementById("bannerIcon");
    const bannerTitle = document.getElementById("bannerTitle");
    const bannerDesc = document.getElementById("bannerDesc");

    if (report.needs_attention) {
        banner.className = "alert-banner flagged";
        bannerIcon.innerText = "🚨";
        bannerTitle.innerText = "ACTION REQUIRED: Suspicious Risk Pattern Flagged";
        bannerDesc.innerText = "Deterministic rules and AI synthesis identified specific transaction anomalies needing human investigator review.";
        
        document.getElementById("findingsSection").classList.remove("hidden");
        document.getElementById("nullCaseSection").classList.add("hidden");
    } else {
        banner.className = "alert-banner routine";
        bannerIcon.innerText = "✅";
        bannerTitle.innerText = "ROUTINE ACCOUNT: Zero Risk Flags Detected (Null Case)";
        bannerDesc.innerText = "All transactions conform to established baseline customer spending patterns.";

        document.getElementById("findingsSection").classList.add("hidden");
        document.getElementById("nullCaseSection").classList.remove("hidden");
        document.getElementById("nullReasoning").innerText = report.null_case_reasoning || "All transactions evaluated match normal customer history.";
    }

    // Exec Summary
    document.getElementById("execSummary").innerText = report.executive_summary;

    // Guidance
    document.getElementById("investigatorGuidance").innerText = report.investigator_guidance;

    // Disclaimer
    if (report.disclaimer) {
        document.getElementById("disclaimerText").innerText = report.disclaimer;
    }

    // Render Findings List & Highlight Rows
    const findingsList = document.getElementById("findingsList");
    findingsList.innerHTML = "";

    // Clear previous row highlights
    document.querySelectorAll("#txnTableBody tr").forEach(row => {
        row.style.backgroundColor = "";
    });

    if (report.findings && report.findings.length > 0) {
        report.findings.forEach(f => {
            const item = document.createElement("div");
            item.className = "finding-item";
            
            const citedTags = f.cited_transaction_ids.map(id => `<span class="cited-tag">TXN #${id}</span>`).join(" ");

            item.innerHTML = `
                <div class="finding-header">
                    <span class="rule-title">${f.rule_triggered}</span>
                    <span class="badge ${f.severity}">${f.severity} SEVERITY</span>
                </div>
                <div class="cited-ids">Cited Evidence: ${citedTags}</div>
                <div class="finding-body">
                    <div><strong>Summary:</strong> ${f.summary}</div>
                    <div><strong>Baseline Deviation:</strong> ${f.difference_from_normal}</div>
                    <div><strong>Recommended Action:</strong> ${f.investigator_action}</div>
                </div>
            `;
            findingsList.appendChild(item);

            // Highlight cited transactions in table
            f.cited_transaction_ids.forEach(tid => {
                const row = document.getElementById(`row-${tid}`);
                if (row) {
                    row.style.backgroundColor = "rgba(248, 81, 73, 0.15)";
                }
                const tag = document.getElementById(`tag-${tid}`);
                if (tag) {
                    tag.innerHTML = `<span class="badge ${f.severity}">FLAGGED IN AUDIT</span>`;
                }
            });
        });
    }

    // Scroll to report card smoothly
    reportCard.scrollIntoView({ behavior: "smooth" });
}

function handleInvestigatorAction(actionText) {
    alert(`Action Recorded: ${actionText}\nCase status updated in Audit Trail.`);
}

function toggleCustomJsonModal() {
    const modal = document.getElementById("jsonModal");
    modal.classList.toggle("hidden");
}

function submitCustomJson() {
    const text = document.getElementById("customJsonInput").value;
    try {
        const json = JSON.parse(text);
        currentCaseData = json;
        renderCase(currentCaseData);
        toggleCustomJsonModal();
        document.getElementById("auditStatus").innerText = "Custom Case Loaded. Click Run Audit.";
    } catch (e) {
        alert("Invalid JSON: " + e.message);
    }
}
