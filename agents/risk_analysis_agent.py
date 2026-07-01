"""
Risk Analysis Agent - contract clause risk assessment via structured reasoning.

Takes an enriched contract and produces a risk assessment with:
- Risk score (0-100)
- Decision: ACCEPT / FLAG / NEGOTIATE / REJECT
- Confidence score
- Explicit reasoning chain (required for the audit trail)
- Key deviations and mitigating factors

Design decision: low temperature (0.1) for consistency. The same contract clause
set should produce the same risk assessment - reproducibility matters when a
client asks "why did this get flagged." We use structured output via tool use
to guarantee parseable, auditable output every time.

Confidence threshold drives HITL routing: below HITL_THRESHOLD, the assessment
goes to a lawyer's review queue regardless of the AI's recommendation.
"""

import os
from anthropic import Anthropic
from core.models import EnrichedContract, RiskAssessment, RiskDecision

client = Anthropic()

HITL_THRESHOLD = float(os.getenv("HITL_THRESHOLD", "0.85"))

SYSTEM_PROMPT = """You are a senior contracts counsel at a large law firm's transactional practice
with 15 years of experience reviewing commercial agreements for clients.

Your assessments carry real commercial and legal weight. Every conclusion must be:
1. Evidence-based - cite specific clauses and specific playbook deviations
2. Proportionate - do not over-flag; unnecessary escalation wastes partner time
3. Documented - your reasoning will be reviewed by the assigned lawyer before anything is sent to the counterparty

Deviation categories you assess:
- Liability exposure: uncapped or excessively high liability, missing consequential damages exclusion
- Indemnification imbalance: one-sided indemnification, no carve-outs, uncapped exposure
- Termination risk: no cure period, unilateral termination rights, excessive notice asymmetry
- IP leakage: assignment of pre-existing IP, no residuals clause, ambiguous ownership of deliverables
- Missing protections: playbook-expected clauses absent entirely (e.g. no liability cap, no data protection terms)
- Jurisdiction and enforcement risk: governing law or dispute forum that increases enforcement difficulty
- Non-compete overreach: restrictions broader than what is enforceable in the governing jurisdiction"""


def _build_analysis_tool() -> dict:
    """Structured output schema for the risk assessment."""
    return {
        "name": "record_risk_assessment",
        "description": "Record the structured contract risk assessment for the audit trail",
        "input_schema": {
            "type": "object",
            "properties": {
                "risk_score": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "0=fully matches playbook, 100=must not sign as drafted",
                },
                "decision": {
                    "type": "string",
                    "enum": ["ACCEPT", "FLAG", "NEGOTIATE", "REJECT"],
                    "description": "ACCEPT=matches playbook, FLAG=minor deviation worth noting, NEGOTIATE=redline required before signature, REJECT=unacceptable as drafted",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence in the assessment. Below 0.85 triggers mandatory lawyer review.",
                },
                "reasoning": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Factors considered, in descending order of weight. Be specific about which clause and which deviation.",
                },
                "key_deviations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific deviations from the playbook position, referencing clause type and section",
                },
                "mitigating_factors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Factors that reduce the concern level (e.g. low contract value, short term, known reliable counterparty)",
                },
                "recommended_actions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific next steps for the reviewing lawyer",
                },
                "primary_concern_clause": {
                    "type": "string",
                    "description": "The single clause type driving the overall decision, if any",
                },
            },
            "required": ["risk_score", "decision", "confidence", "reasoning",
                        "key_deviations", "mitigating_factors", "recommended_actions"],
        },
    }


def run(enriched_contract: EnrichedContract) -> RiskAssessment:
    """
    Analyse enriched contract and produce a structured risk assessment.
    Returns RiskAssessment with a routing instruction for the HITL queue.
    """
    contract = enriched_contract.original_contract

    playbook_summary = "\n".join(
        f"- {m.clause_type.value}: playbook expects '{m.playbook_position}' "
        f"(deviation: {m.deviation_type}, score {m.deviation_score:.2f})"
        for m in enriched_contract.playbook_matches
    ) or "No playbook matches recorded"

    missing_summary = (
        ", ".join(c.value for c in enriched_contract.missing_clauses)
        if enriched_contract.missing_clauses else "None"
    )

    clause_text_summary = "\n".join(
        f"- {c.clause_type.value} ({c.section_reference}): {c.clause_text}"
        for c in contract.clauses
    )

    user_message = f"""Review this contract and provide your risk assessment.

=== CONTRACT DETAILS ===
Contract ID: {contract.contract_id}
Type: {contract.contract_type.value}
Counterparty: {contract.counterparty_name} ({contract.counterparty_jurisdiction})
Governing law: {contract.governing_law}
Value: {contract.contract_value} {contract.currency or ''}
Summary: {contract.contract_summary}

=== CLAUSES AS DRAFTED ===
{clause_text_summary}

=== PLAYBOOK COMPARISON ===
{playbook_summary}

Missing clauses vs playbook expectation: {missing_summary}
Jurisdiction risk: {enriched_contract.jurisdiction_risk.value}
Deal precedent notes: {'; '.join(enriched_contract.precedent_notes) if enriched_contract.precedent_notes else 'None on record'}
Enrichment confidence: {enriched_contract.enrichment_confidence:.0%}

Use the record_risk_assessment tool to provide your structured assessment."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        temperature=0.1,
        system=SYSTEM_PROMPT,
        tools=[_build_analysis_tool()],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_message}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_risk_assessment":
            data = block.input
            return RiskAssessment(
                risk_score=data.get("risk_score", 50),
                decision=RiskDecision(data.get("decision", "NEGOTIATE")),
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning") or ["Model did not return a reasoning chain"],
                key_deviations=data.get("key_deviations") or [],
                mitigating_factors=data.get("mitigating_factors") or [],
                recommended_actions=data.get("recommended_actions") or ["Manual review recommended - assessment incomplete"],
                primary_concern_clause=data.get("primary_concern_clause"),
            )

    # Fallback: if structured output not returned, default to NEGOTIATE for safety
    return RiskAssessment(
        risk_score=50,
        decision=RiskDecision.NEGOTIATE,
        confidence=0.3,
        reasoning=["Structured analysis could not be completed - routing to lawyer for safety"],
        key_deviations=["Analysis error"],
        mitigating_factors=[],
        recommended_actions=["Manual review required"],
    )
