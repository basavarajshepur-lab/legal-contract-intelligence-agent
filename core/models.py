"""
Pydantic models for the Contract Intelligence pipeline.
Every field is typed and documented - the audit trail depends on this.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ContractType(str, Enum):
    NDA = "nda"
    MSA = "master_service_agreement"
    VENDOR_AGREEMENT = "vendor_agreement"
    LEASE = "commercial_lease"
    EMPLOYMENT = "employment_agreement"
    LICENSING = "licensing_agreement"
    PARTNERSHIP = "partnership_agreement"
    SALES_CONTRACT = "sales_contract"


class ClauseType(str, Enum):
    INDEMNIFICATION = "indemnification"
    LIABILITY_CAP = "liability_cap"
    TERMINATION = "termination"
    IP_ASSIGNMENT = "ip_assignment"
    GOVERNING_LAW = "governing_law"
    CONFIDENTIALITY = "confidentiality"
    NON_COMPETE = "non_compete"
    ASSIGNMENT = "assignment"
    PAYMENT_TERMS = "payment_terms"
    WARRANTY = "warranty"
    FORCE_MAJEURE = "force_majeure"
    DATA_PROTECTION = "data_protection"
    DISPUTE_RESOLUTION = "dispute_resolution"


class RiskDecision(str, Enum):
    ACCEPT = "ACCEPT"
    FLAG = "FLAG"
    NEGOTIATE = "NEGOTIATE"
    REJECT = "REJECT"


class JurisdictionRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class Clause(BaseModel):
    clause_type: ClauseType
    clause_text: str
    section_reference: str


class Contract(BaseModel):
    contract_id: str
    contract_name: str
    contract_type: ContractType
    counterparty_name: str
    counterparty_jurisdiction: str
    effective_date: str
    contract_value: Optional[float] = None
    currency: Optional[str] = None
    governing_law: str
    contract_summary: str
    clauses: list[Clause]


class PlaybookMatch(BaseModel):
    clause_type: ClauseType
    playbook_position: str
    deviation_type: str  # within_range, below_market, above_market, missing, non_standard
    deviation_score: float  # 0-1, higher = further from standard playbook position


class EnrichedContract(BaseModel):
    original_contract: Contract
    playbook_matches: list[PlaybookMatch] = Field(default_factory=list)
    missing_clauses: list[ClauseType] = Field(default_factory=list)
    jurisdiction_risk: JurisdictionRisk = JurisdictionRisk.LOW
    precedent_notes: list[str] = Field(default_factory=list)
    enrichment_confidence: float = Field(ge=0.0, le=1.0)
    enrichment_notes: str = ""


class RiskAssessment(BaseModel):
    risk_score: int = Field(ge=0, le=100, description="0=fully standard, 100=must not sign as drafted")
    decision: RiskDecision
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: list[str] = Field(description="Factors considered, in order of weight")
    key_deviations: list[str]
    mitigating_factors: list[str]
    recommended_actions: list[str]
    primary_concern_clause: Optional[str] = None


class ProposedRedline(BaseModel):
    clause_type: ClauseType
    current_language: str
    proposed_language: str
    rationale: str


class RedlineMemo(BaseModel):
    contract_overview: str
    flagged_clauses_summary: str
    proposed_redlines: list[ProposedRedline]
    negotiation_priority: str  # HIGH, MEDIUM, LOW
    recommended_reviewer: str  # e.g. "Senior Associate", "Partner", "General Counsel"


class HITLQueueItem(BaseModel):
    queue_id: str
    contract_id: str
    enriched_contract: EnrichedContract
    risk_assessment: RiskAssessment
    redline_memo: Optional[RedlineMemo] = None
    queued_at: datetime = Field(default_factory=datetime.utcnow)
    requires_hitl: bool = True
    priority: str = "NORMAL"  # NORMAL, HIGH, URGENT


class AuditEntry(BaseModel):
    audit_id: str
    contract_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    stage: str  # enrichment, risk_analysis, hitl_review, final
    ai_decision: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_reasoning: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewer_decision: Optional[str] = None
    reviewer_notes: Optional[str] = None
    final_outcome: Optional[str] = None


class PipelineResult(BaseModel):
    contract_id: str
    enriched_contract: EnrichedContract
    risk_assessment: RiskAssessment
    redline_memo: Optional[RedlineMemo] = None
    sent_to_hitl: bool
    audit_id: str
    processing_time_ms: float
