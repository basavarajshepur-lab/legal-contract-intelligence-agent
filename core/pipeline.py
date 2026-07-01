"""
Contract Intelligence Pipeline - orchestrates the full multi-agent review workflow.

Flow:
  Contract -> Enrichment Agent -> Risk Analysis Agent -> [NEGOTIATE/REJECT?] Redline Agent
           -> HITL Queue (if confidence < threshold) -> Audit Trail -> Result

Design decisions:
- Enrichment always runs first; risk analysis never sees raw clauses without playbook context
- Redline agent only runs for NEGOTIATE/REJECT decisions (cost control + proportionality)
- Every result is logged to the audit trail before being returned
- Low-confidence assessments always go to HITL regardless of the decision itself
"""

import os
import time
from agents import enrichment_agent, risk_analysis_agent, redline_agent
from core.models import Contract, PipelineResult, RiskDecision
from core.audit_trail import log_ai_decision

HITL_THRESHOLD = float(os.getenv("HITL_THRESHOLD", "0.85"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))


def process_contract(contract: Contract) -> PipelineResult:
    """
    Run a single contract through the full contract intelligence pipeline.
    Returns PipelineResult with risk assessment, optional redline memo, and audit ID.
    """
    start_ms = time.time() * 1000

    # Stage 1: Playbook and precedent enrichment via tool use
    enriched = enrichment_agent.run(contract)

    # Stage 2: Risk analysis with structured reasoning
    assessment = risk_analysis_agent.run(enriched)

    # Stage 3: Redline drafting (only if NEGOTIATE or REJECT)
    redline_memo = None
    if assessment.decision in [RiskDecision.NEGOTIATE, RiskDecision.REJECT]:
        redline_memo = redline_agent.run(enriched, assessment)

    # Stage 4: Log to audit trail (always, before returning)
    audit_id = log_ai_decision(contract.contract_id, enriched, assessment)

    # Stage 5: Determine if HITL review is needed
    # HITL triggered if: confidence below threshold OR decision is NEGOTIATE/REJECT
    requires_hitl = (
        assessment.confidence < HITL_THRESHOLD
        or assessment.decision in [RiskDecision.NEGOTIATE, RiskDecision.REJECT]
    )

    elapsed_ms = (time.time() * 1000) - start_ms

    return PipelineResult(
        contract_id=contract.contract_id,
        enriched_contract=enriched,
        risk_assessment=assessment,
        redline_memo=redline_memo,
        sent_to_hitl=requires_hitl,
        audit_id=audit_id,
        processing_time_ms=round(elapsed_ms, 1),
    )
