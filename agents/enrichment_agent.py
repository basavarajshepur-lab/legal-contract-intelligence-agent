"""
Enrichment Agent - playbook and precedent lookup via tool use.

Takes a contract with already-identified clauses and enriches it with:
- Playbook position matching (how does each clause compare to the firm/client's
  standard fallback position?)
- Missing clause detection (does the contract omit a clause the playbook expects
  for this contract type?)
- Governing law / jurisdiction risk rating
- Precedent notes (similar past deals or disputes on record)

In production: playbook lookup connects to the firm's clause library and deal
precedent database (e.g. Kira Systems, Luminance, or an internal DMS). In this
demo: a realistic mock playbook so the full pipeline logic is demonstrable
without a live clause library.

Design decision: separate enrichment (reference-data lookup) from risk analysis
(reasoning over that data), exactly as AML enrichment is separated from AML risk
analysis. Each agent has a single responsibility and can be swapped independently.
"""

import json
import re
from anthropic import Anthropic
from core.models import Contract, EnrichedContract, PlaybookMatch, JurisdictionRisk, ClauseType

client = Anthropic()

# --- Mock playbook and precedent tools (replace with real clause library in production) ---

PLAYBOOK_POSITIONS = {
    ClauseType.INDEMNIFICATION: "Mutual indemnification, capped at 12 months' fees paid under the agreement, carve-out for gross negligence and IP infringement uncapped.",
    ClauseType.LIABILITY_CAP: "Aggregate liability capped at 1x-3x total fees paid in the preceding 12 months. Direct damages only; consequential damages excluded.",
    ClauseType.TERMINATION: "Either party may terminate for convenience with 60-90 days' written notice. Termination for cause requires a 30-day cure period.",
    ClauseType.IP_ASSIGNMENT: "Client owns all deliverables created specifically for the engagement. Vendor retains pre-existing IP and general know-how (residuals clause).",
    ClauseType.GOVERNING_LAW: "England and Wales, with exclusive jurisdiction of the English courts, is the standard fallback for UK-headquartered clients.",
    ClauseType.CONFIDENTIALITY: "Mutual confidentiality obligation surviving 3-5 years post-termination, with standard carve-outs (public domain, independently developed, legally compelled disclosure).",
    ClauseType.NON_COMPETE: "Non-compete restrictions should be limited to 12 months and a defined competitive scope; anything broader is rarely enforceable in England and Wales and invites challenge.",
    ClauseType.ASSIGNMENT: "Assignment permitted to an affiliate or in connection with a merger/sale of substantially all assets, with notice; otherwise requires the other party's consent, not unreasonably withheld.",
    ClauseType.PAYMENT_TERMS: "Net 30 from invoice date is standard; late payment interest at Bank of England base rate plus 8% under the Late Payment of Commercial Debts Act.",
    ClauseType.WARRANTY: "Services performed with reasonable skill and care to industry standard; disclaimers of implied warranties beyond that are standard and acceptable.",
    ClauseType.FORCE_MAJEURE: "Standard force majeure carve-out for events beyond reasonable control, with an obligation to mitigate and a right to terminate if the event exceeds 60-90 days.",
    ClauseType.DATA_PROTECTION: "UK GDPR-compliant data processing terms required whenever personal data is processed, including a data processing addendum with standard contractual clauses for any international transfer.",
    ClauseType.DISPUTE_RESOLUTION: "Good-faith negotiation, escalating to mediation, then litigation or arbitration in the agreed governing law jurisdiction.",
}

JURISDICTION_RISK_MAP = {
    "GB": JurisdictionRisk.LOW, "US": JurisdictionRisk.LOW, "IE": JurisdictionRisk.LOW,
    "DE": JurisdictionRisk.LOW, "FR": JurisdictionRisk.LOW, "SG": JurisdictionRisk.LOW,
    "AE": JurisdictionRisk.MEDIUM, "IN": JurisdictionRisk.MEDIUM, "CN": JurisdictionRisk.MEDIUM,
    "BR": JurisdictionRisk.MEDIUM, "NG": JurisdictionRisk.HIGH, "RU": JurisdictionRisk.VERY_HIGH,
}

EXPECTED_CLAUSES_BY_TYPE = {
    "master_service_agreement": [
        ClauseType.INDEMNIFICATION, ClauseType.LIABILITY_CAP, ClauseType.TERMINATION,
        ClauseType.IP_ASSIGNMENT, ClauseType.GOVERNING_LAW, ClauseType.CONFIDENTIALITY,
        ClauseType.PAYMENT_TERMS, ClauseType.DATA_PROTECTION,
    ],
    "vendor_agreement": [
        ClauseType.LIABILITY_CAP, ClauseType.TERMINATION, ClauseType.PAYMENT_TERMS,
        ClauseType.CONFIDENTIALITY, ClauseType.WARRANTY, ClauseType.GOVERNING_LAW,
    ],
    "nda": [ClauseType.CONFIDENTIALITY, ClauseType.GOVERNING_LAW, ClauseType.TERMINATION],
    "employment_agreement": [
        ClauseType.NON_COMPETE, ClauseType.CONFIDENTIALITY, ClauseType.IP_ASSIGNMENT,
        ClauseType.TERMINATION, ClauseType.GOVERNING_LAW,
    ],
    "licensing_agreement": [
        ClauseType.IP_ASSIGNMENT, ClauseType.LIABILITY_CAP, ClauseType.PAYMENT_TERMS,
        ClauseType.TERMINATION, ClauseType.GOVERNING_LAW, ClauseType.WARRANTY,
    ],
    "commercial_lease": [
        ClauseType.TERMINATION, ClauseType.PAYMENT_TERMS, ClauseType.FORCE_MAJEURE,
        ClauseType.GOVERNING_LAW, ClauseType.DISPUTE_RESOLUTION,
    ],
    "partnership_agreement": [
        ClauseType.INDEMNIFICATION, ClauseType.TERMINATION, ClauseType.IP_ASSIGNMENT,
        ClauseType.GOVERNING_LAW, ClauseType.DISPUTE_RESOLUTION,
    ],
    "sales_contract": [
        ClauseType.WARRANTY, ClauseType.LIABILITY_CAP, ClauseType.PAYMENT_TERMS,
        ClauseType.GOVERNING_LAW, ClauseType.FORCE_MAJEURE,
    ],
}


def get_playbook_position(clause_type: str) -> dict:
    """Look up the firm/client's standard fallback position for a clause type."""
    try:
        ct = ClauseType(clause_type)
    except ValueError:
        return {"position": "No playbook entry for this clause type", "found": False}
    return {"position": PLAYBOOK_POSITIONS.get(ct, "No playbook entry"), "found": ct in PLAYBOOK_POSITIONS}


def get_jurisdiction_risk(jurisdiction_code: str) -> dict:
    """Return the firm's risk rating for a governing law / counterparty jurisdiction."""
    risk = JURISDICTION_RISK_MAP.get(jurisdiction_code.upper(), JurisdictionRisk.MEDIUM)
    return {
        "jurisdiction_code": jurisdiction_code,
        "risk_rating": risk.value,
        "enforcement_note": "Reciprocal enforcement of judgments is well established"
        if risk == JurisdictionRisk.LOW else "Enforcement of English judgments may require local counsel review",
    }


def search_deal_precedent(counterparty_name: str, contract_type: str) -> dict:
    """Search internal precedent database for prior deals or disputes with this counterparty. Mock implementation."""
    findings = []
    name_lower = counterparty_name.lower()
    if "veltrix" in name_lower or "northbridge" in name_lower:
        findings.append(f"Prior {contract_type} with {counterparty_name} required two rounds of liability-cap negotiation before signature")
    if "atlas" in name_lower:
        findings.append(f"{counterparty_name} has a recorded payment dispute on a prior engagement (resolved, no litigation)")
    return {"findings": findings, "source": "Internal deal precedent database (mock)"}


def get_expected_clauses(contract_type: str) -> dict:
    """Return the list of clauses the playbook expects for this contract type."""
    expected = EXPECTED_CLAUSES_BY_TYPE.get(contract_type, [])
    return {"expected_clause_types": [c.value for c in expected]}


TOOLS = [
    {
        "name": "get_playbook_position",
        "description": "Look up the firm or client's standard fallback position for a given clause type",
        "input_schema": {
            "type": "object",
            "properties": {"clause_type": {"type": "string", "description": "The clause type, e.g. liability_cap"}},
            "required": ["clause_type"],
        },
    },
    {
        "name": "get_jurisdiction_risk",
        "description": "Get the firm's risk rating for a governing law or counterparty jurisdiction",
        "input_schema": {
            "type": "object",
            "properties": {"jurisdiction_code": {"type": "string", "description": "ISO 2-letter country code"}},
            "required": ["jurisdiction_code"],
        },
    },
    {
        "name": "search_deal_precedent",
        "description": "Search the internal precedent database for prior deals or disputes with a counterparty",
        "input_schema": {
            "type": "object",
            "properties": {
                "counterparty_name": {"type": "string"},
                "contract_type": {"type": "string"},
            },
            "required": ["counterparty_name", "contract_type"],
        },
    },
    {
        "name": "get_expected_clauses",
        "description": "Get the list of clauses the playbook expects to see for a given contract type",
        "input_schema": {
            "type": "object",
            "properties": {"contract_type": {"type": "string"}},
            "required": ["contract_type"],
        },
    },
]

TOOL_MAP = {
    "get_playbook_position": get_playbook_position,
    "get_jurisdiction_risk": get_jurisdiction_risk,
    "search_deal_precedent": search_deal_precedent,
    "get_expected_clauses": get_expected_clauses,
}


def run(contract: Contract) -> EnrichedContract:
    """
    Run enrichment agent: compare each extracted clause against the playbook,
    check jurisdiction risk, and search deal precedent. Returns EnrichedContract.
    """
    system = """You are a senior contracts specialist at a large law firm's transactional practice.
Your job is to use the available tools to compare this contract's clauses against
the firm's standard playbook positions, check jurisdiction risk, and search deal
precedent with this counterparty.
Look up the playbook position for every clause present in the contract. Always check
which clauses the playbook expects for this contract type, so missing clauses are caught.
Always check jurisdiction risk. Be thorough - a missed liability exposure is worse
than a false positive at this stage."""

    clause_summary = "\n".join(
        f"- {c.clause_type.value} ({c.section_reference}): {c.clause_text}"
        for c in contract.clauses
    )

    user_message = f"""Please enrich this contract with playbook and precedent data:

Contract ID: {contract.contract_id}
Contract type: {contract.contract_type.value}
Counterparty: {contract.counterparty_name} ({contract.counterparty_jurisdiction})
Governing law: {contract.governing_law}
Contract value: {contract.contract_value} {contract.currency or ''}

Clauses present:
{clause_summary}

Use the available tools to:
1. Look up the playbook position for every clause type present in the contract
2. Get the expected clause list for this contract type, and identify any missing
3. Get jurisdiction risk for the counterparty's jurisdiction
4. Search deal precedent for this counterparty

Then provide a JSON summary of your findings with keys:
playbook_matches (list of clause_type, deviation_type, deviation_score),
missing_clause_types, jurisdiction_risk, precedent_notes,
enrichment_confidence (0-1), enrichment_notes"""

    messages = [{"role": "user", "content": user_message}]
    playbook_matches: list[PlaybookMatch] = []
    missing_clauses: list[ClauseType] = []
    precedent_notes: list[str] = []
    jurisdiction_risk = JurisdictionRisk.MEDIUM
    expected_types: list[str] = []
    present_types = {c.clause_type.value for c in contract.clauses}

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_fn = TOOL_MAP.get(block.name)
                    result = tool_fn(**block.input) if tool_fn else {"error": "unknown tool"}

                    if block.name == "get_playbook_position":
                        clause_type_str = block.input.get("clause_type")
                        try:
                            ct = ClauseType(clause_type_str)
                            matched_clause = next((c for c in contract.clauses if c.clause_type == ct), None)
                            deviation_type = "within_range" if matched_clause else "missing"
                            playbook_matches.append(PlaybookMatch(
                                clause_type=ct,
                                playbook_position=result.get("position", ""),
                                deviation_type=deviation_type,
                                deviation_score=0.2 if deviation_type == "within_range" else 0.9,
                            ))
                        except ValueError:
                            pass
                    elif block.name == "get_expected_clauses":
                        expected_types = result.get("expected_clause_types", [])
                        for et in expected_types:
                            if et not in present_types:
                                try:
                                    missing_clauses.append(ClauseType(et))
                                except ValueError:
                                    pass
                    elif block.name == "get_jurisdiction_risk":
                        risk_str = result.get("risk_rating", "MEDIUM")
                        jurisdiction_risk = JurisdictionRisk(risk_str)
                    elif block.name == "search_deal_precedent":
                        precedent_notes.extend(result.get("findings", []))

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        else:
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            confidence = 0.8
            conf_match = re.search(r"enrichment_confidence[\"']?\s*:\s*([0-9.]+)", final_text)
            if conf_match:
                confidence = float(conf_match.group(1))

            break

    return EnrichedContract(
        original_contract=contract,
        playbook_matches=playbook_matches,
        missing_clauses=list(set(missing_clauses)),
        jurisdiction_risk=jurisdiction_risk,
        precedent_notes=precedent_notes,
        enrichment_confidence=confidence,
        enrichment_notes=f"Screened via multi-tool playbook enrichment. {len(missing_clauses)} missing clause(s) vs playbook expectation.",
    )
