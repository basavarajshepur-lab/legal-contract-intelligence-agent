"""
Redline Drafting Agent - drafts proposed redline language for flagged clauses.

Only invoked when the risk assessment decision is NEGOTIATE or REJECT. Produces
a structured memo a reviewing lawyer can act on directly: proposed replacement
language per flagged clause, a negotiation priority, and a recommended reviewer
level.

Design decision: this agent is last in the pipeline and never sends anything to
a counterparty automatically. The HITL queue always shows the redline memo to a
lawyer before any proposed language leaves the firm. The lawyer reviews both the
risk assessment AND the redline draft.

In production: approved redlines would flow into the firm's document assembly
system (e.g. a Word add-in via the Office JS API) for direct insertion into the
countersigned draft. This agent produces the draft only.
"""

from anthropic import Anthropic
from core.models import EnrichedContract, RiskAssessment, RedlineMemo, ProposedRedline, ClauseType

client = Anthropic()

SYSTEM_PROMPT = """You are an experienced transactional lawyer drafting redline language for a
flagged commercial contract. Your redlines must be:

1. Specific - propose actual replacement language, not just a description of the problem
2. Commercially reasonable - propose the firm's standard playbook fallback, not an aggressive opening position
3. Justified - each redline needs a one-line rationale a partner can approve quickly
4. Proportionate - do not redline every clause; focus on the deviations that actually matter

Do NOT include: speculation about the counterparty's motives, unprofessional language,
or redlines for clauses that were not flagged as deviating from the playbook."""


def run(
    enriched_contract: EnrichedContract,
    risk_assessment: RiskAssessment,
) -> RedlineMemo:
    """Draft a redline memo for lawyer review. Never sent to a counterparty automatically."""
    contract = enriched_contract.original_contract

    flagged_clause_types = {m.clause_type for m in enriched_contract.playbook_matches if m.deviation_type != "within_range"}
    flagged_clauses = [c for c in contract.clauses if c.clause_type in flagged_clause_types]

    clause_text = "\n".join(
        f"- {c.clause_type.value} ({c.section_reference}): {c.clause_text}"
        for c in flagged_clauses
    ) or "No specific clause text flagged - see missing clauses below"

    missing_summary = (
        ", ".join(c.value for c in enriched_contract.missing_clauses)
        if enriched_contract.missing_clauses else "None"
    )

    user_message = f"""Draft redline language for the following contract.

CONTRACT: {contract.contract_id} - {contract.contract_name}
Counterparty: {contract.counterparty_name}
Type: {contract.contract_type.value}

FLAGGED CLAUSES AS DRAFTED:
{clause_text}

MISSING CLAUSES (playbook expects, contract omits): {missing_summary}

RISK ASSESSMENT:
Decision: {risk_assessment.decision.value}
Risk score: {risk_assessment.risk_score}/100
Key deviations: {risk_assessment.key_deviations}
Primary concern: {risk_assessment.primary_concern_clause}

Produce a redline memo with these sections:
1. contract_overview: One paragraph on the contract and why it was flagged
2. flagged_clauses_summary: Plain-language summary of what is wrong and why it matters commercially
3. proposed_redlines: For each flagged or missing clause, propose specific replacement or new language and a one-line rationale
4. negotiation_priority: HIGH, MEDIUM, or LOW - how hard to push on this in negotiation
5. recommended_reviewer: Who should review this before it goes out (Senior Associate, Partner, or General Counsel)

Write in clear, professional legal drafting language. This draft will be reviewed by a lawyer before anything is sent to the counterparty."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text

    def extract_section(text: str, section: str) -> str:
        import re
        pattern = rf"{re.escape(section)}[:\s]*(.+?)(?=\n[0-9]\.\s*[a-z_]+:|\n[A-Z][a-z_]+:|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    proposed_redlines = [
        ProposedRedline(
            clause_type=c.clause_type,
            current_language=c.clause_text,
            proposed_language="See redline memo narrative for specific proposed language",
            rationale=f"Deviates from playbook position for {c.clause_type.value}",
        )
        for c in flagged_clauses
    ]

    priority_text = extract_section(text, "negotiation_priority") or "MEDIUM"
    priority = next((p for p in ["HIGH", "MEDIUM", "LOW"] if p in priority_text.upper()), "MEDIUM")

    return RedlineMemo(
        contract_overview=extract_section(text, "contract_overview") or text[:400],
        flagged_clauses_summary=extract_section(text, "flagged_clauses_summary") or "",
        proposed_redlines=proposed_redlines,
        negotiation_priority=priority,
        recommended_reviewer=extract_section(text, "recommended_reviewer") or "Senior Associate",
    )
