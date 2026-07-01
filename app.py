"""
Contract Intelligence Agent - Lawyer Review Interface

Streamlit app for lawyers to review AI risk assessments on commercial contracts,
override where needed, and maintain the audit trail.

Run: streamlit run app.py
"""

from dotenv import load_dotenv
load_dotenv()

import json
import time
import streamlit as st
import pandas as pd
from pathlib import Path
from core.models import Contract
from core.pipeline import process_contract
from core.audit_trail import get_dashboard_stats, get_audit_trail, log_reviewer_decision, export_csv

st.set_page_config(
    page_title="Contract Intelligence Agent",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Sidebar ---
st.sidebar.title("📄 Contract Intelligence Agent")
st.sidebar.caption("Multi-agent contract risk triage - v1.0")
st.sidebar.divider()

stats = get_dashboard_stats()
st.sidebar.metric("Total Processed", stats["total_processed"])
st.sidebar.metric("Auto-Accepted", stats["auto_accepted"])
st.sidebar.metric("Needs Negotiation", stats["needs_negotiation"])
st.sidebar.metric("Pending Lawyer Review", stats["pending_lawyer_review"])
if stats["total_processed"] > 0:
    st.sidebar.metric(
        "Est. Auto-Accept Rate",
        f"{stats['auto_accept_rate_estimate']}%",
        help="Contracts auto-accepted vs total processed",
    )

st.sidebar.divider()
if st.sidebar.button("Export Audit Trail CSV"):
    path = export_csv()
    st.sidebar.success(f"Exported to {path}")

# --- Main tabs ---
tab_process, tab_batch, tab_audit = st.tabs(["Review Contract", "Batch Process", "Audit Trail"])

DECISION_COLORS = {
    "ACCEPT": "🟢",
    "FLAG": "🟡",
    "NEGOTIATE": "🟠",
    "REJECT": "🔴",
}

# --- Tab 1: Process single contract ---
with tab_process:
    st.header("Review Contract")
    col1, col2 = st.columns([1, 1])

    with col1:
        sample_path = Path("data/sample_contracts.json")
        sample_contracts = json.loads(sample_path.read_text()) if sample_path.exists() else []
        contract_ids = [c["contract_id"] for c in sample_contracts]

        selected_id = st.selectbox("Select sample contract", contract_ids)
        contract_data = next((c for c in sample_contracts if c["contract_id"] == selected_id), None)

        if contract_data:
            with st.expander("Contract details", expanded=True):
                st.write(f"**Name:** {contract_data['contract_name']}")
                st.write(f"**Type:** {contract_data['contract_type']}")
                st.write(f"**Counterparty:** {contract_data['counterparty_name']} ({contract_data['counterparty_jurisdiction']})")
                st.write(f"**Governing law:** {contract_data['governing_law']}")
                if contract_data.get("contract_value"):
                    st.write(f"**Value:** {contract_data['contract_value']:,.2f} {contract_data.get('currency', '')}")
                st.write(f"**Summary:** {contract_data['contract_summary']}")
                st.write(f"**Clauses in contract:** {len(contract_data['clauses'])}")

    with col2:
        if st.button("Run AI Risk Assessment", type="primary", use_container_width=True):
            if contract_data:
                contract = Contract(**contract_data)
                with st.spinner("Running playbook enrichment + risk analysis..."):
                    start = time.time()
                    result = process_contract(contract)
                    elapsed = time.time() - start

                assessment = result.risk_assessment
                emoji = DECISION_COLORS.get(assessment.decision.value, "⚪")

                st.success(f"Processed in {elapsed:.1f}s")

                st.subheader(f"{emoji} Decision: {assessment.decision.value}")
                col_score, col_conf = st.columns(2)
                col_score.metric("Risk Score", f"{assessment.risk_score}/100")
                col_conf.metric("AI Confidence", f"{assessment.confidence:.0%}")

                if assessment.confidence < 0.85:
                    st.warning("Low confidence - mandatory lawyer review required")

                with st.expander("Playbook comparison", expanded=True):
                    enriched = result.enriched_contract
                    if enriched.missing_clauses:
                        st.error(f"Missing {len(enriched.missing_clauses)} clause(s) the playbook expects: "
                                 + ", ".join(c.value for c in enriched.missing_clauses))
                    else:
                        st.success("No missing clauses vs playbook expectation")
                    st.write(f"**Jurisdiction risk:** {enriched.jurisdiction_risk.value}")
                    if enriched.precedent_notes:
                        st.warning("Deal precedent: " + "; ".join(enriched.precedent_notes))
                    for m in enriched.playbook_matches:
                        st.write(f"- **{m.clause_type.value}**: {m.deviation_type} (deviation score {m.deviation_score:.2f}) - {m.playbook_position}")

                with st.expander("AI Reasoning", expanded=True):
                    st.write("**Key deviations:**")
                    for dev in assessment.key_deviations:
                        st.write(f"- {dev}")
                    st.write("**Mitigating factors:**")
                    for factor in assessment.mitigating_factors:
                        st.write(f"- {factor}")
                    st.write("**Reasoning chain:**")
                    for i, reason in enumerate(assessment.reasoning, 1):
                        st.write(f"{i}. {reason}")
                    st.write("**Recommended actions:**")
                    for action in assessment.recommended_actions:
                        st.write(f"- {action}")

                if result.redline_memo:
                    with st.expander("Redline Memo (lawyer review required)", expanded=True):
                        memo = result.redline_memo
                        st.write(f"**Overview:** {memo.contract_overview}")
                        st.write(f"**Flagged clauses:** {memo.flagged_clauses_summary}")
                        st.write(f"**Negotiation priority:** {memo.negotiation_priority}")
                        st.write(f"**Recommended reviewer:** {memo.recommended_reviewer}")
                        for r in memo.proposed_redlines:
                            st.write(f"- **{r.clause_type.value}**: {r.rationale}")

                if result.sent_to_hitl:
                    st.divider()
                    st.subheader("Lawyer Review")
                    reviewer_id = st.text_input("Reviewer ID", value="LAWYER_01")
                    reviewer_decision = st.radio(
                        "Your decision",
                        ["AGREE WITH AI", "ACCEPT", "FLAG", "NEGOTIATE", "REJECT"],
                        horizontal=True,
                    )
                    reviewer_notes = st.text_area("Notes (required for overrides)")
                    if st.button("Submit Review", type="primary"):
                        final = reviewer_decision if reviewer_decision != "AGREE WITH AI" else assessment.decision.value
                        log_reviewer_decision(
                            audit_id=result.audit_id,
                            reviewer_id=reviewer_id,
                            reviewer_decision=reviewer_decision,
                            reviewer_notes=reviewer_notes,
                            final_outcome=final,
                        )
                        st.success(f"Decision logged. Final outcome: {final}")

# --- Tab 2: Batch process ---
with tab_batch:
    st.header("Batch Process Contracts")
    st.info("Upload a JSON file of contracts (same format as sample_contracts.json) to process in bulk.")

    uploaded = st.file_uploader("Upload contracts JSON", type=["json"])
    if uploaded:
        contracts_data = json.load(uploaded)
        st.write(f"Found {len(contracts_data)} contracts")
        if st.button("Process All", type="primary"):
            results = []
            progress = st.progress(0)
            for i, c in enumerate(contracts_data):
                contract = Contract(**c)
                result = process_contract(contract)
                results.append({
                    "Contract ID": result.contract_id,
                    "Decision": result.risk_assessment.decision.value,
                    "Risk Score": result.risk_assessment.risk_score,
                    "Confidence": f"{result.risk_assessment.confidence:.0%}",
                    "HITL Required": "Yes" if result.sent_to_hitl else "No",
                    "Processing (ms)": result.processing_time_ms,
                })
                progress.progress((i + 1) / len(contracts_data))
            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False)
            st.download_button("Download results CSV", csv, "batch_results.csv", "text/csv")

# --- Tab 3: Audit trail ---
with tab_audit:
    st.header("Audit Trail")
    contract_id_search = st.text_input("Search by Contract ID")
    if contract_id_search:
        trail = get_audit_trail(contract_id_search)
        if trail:
            for entry in trail:
                with st.expander(f"Stage: {entry['stage']} - {entry['timestamp']}"):
                    st.json(entry)
        else:
            st.info("No audit entries found for this contract ID")
