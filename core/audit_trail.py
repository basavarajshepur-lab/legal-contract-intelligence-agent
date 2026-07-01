"""
SQLite-backed audit trail for contract review decisions.

Design principle: every AI recommendation and every reviewer override must be
logged with full context, timestamp, and identity, before the reviewer sees
the AI's recommendation. Append-only, never delete. A general counsel's office
should be able to produce the full history of any contract decision in seconds.
"""

import sqlite3
import json
import uuid
from pathlib import Path
from .models import AuditEntry, EnrichedContract, RiskAssessment


DB_PATH = Path("audit.db")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialise_db() -> None:
    """Create audit table on first run. Idempotent."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_trail (
                audit_id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                stage TEXT NOT NULL,
                ai_decision TEXT,
                ai_confidence REAL,
                ai_reasoning TEXT,
                reviewer_id TEXT,
                reviewer_decision TEXT,
                reviewer_notes TEXT,
                final_outcome TEXT,
                raw_payload TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contract_id ON audit_trail(contract_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_trail(timestamp)")


def log_ai_decision(
    contract_id: str,
    enriched_contract: EnrichedContract,
    risk_assessment: RiskAssessment,
) -> str:
    """Log AI risk assessment. Returns audit_id."""
    initialise_db()
    audit_id = str(uuid.uuid4())
    entry = AuditEntry(
        audit_id=audit_id,
        contract_id=contract_id,
        stage="ai_risk_analysis",
        ai_decision=risk_assessment.decision.value,
        ai_confidence=risk_assessment.confidence,
        ai_reasoning=json.dumps(risk_assessment.reasoning),
    )
    with _get_connection() as conn:
        conn.execute(
            """INSERT INTO audit_trail VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                entry.audit_id,
                entry.contract_id,
                entry.timestamp.isoformat(),
                entry.stage,
                entry.ai_decision,
                entry.ai_confidence,
                entry.ai_reasoning,
                None, None, None, None,
                json.dumps({
                    "enriched_contract": enriched_contract.model_dump(mode="json"),
                    "risk_assessment": risk_assessment.model_dump(mode="json"),
                }),
            ),
        )
    return audit_id


def log_reviewer_decision(
    audit_id: str,
    reviewer_id: str,
    reviewer_decision: str,
    reviewer_notes: str,
    final_outcome: str,
) -> None:
    """Record the lawyer's HITL review decision against the existing AI log entry."""
    initialise_db()
    with _get_connection() as conn:
        conn.execute(
            """UPDATE audit_trail
               SET reviewer_id=?, reviewer_decision=?, reviewer_notes=?, final_outcome=?
               WHERE audit_id=?""",
            (reviewer_id, reviewer_decision, reviewer_notes, final_outcome, audit_id),
        )


def get_audit_trail(contract_id: str) -> list[dict]:
    """Return full audit trail for a contract (for compliance or client audit review)."""
    initialise_db()
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_trail WHERE contract_id=? ORDER BY timestamp",
            (contract_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_dashboard_stats() -> dict:
    """Summary stats for the Streamlit dashboard."""
    initialise_db()
    with _get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM audit_trail WHERE stage='ai_risk_analysis'").fetchone()[0]
        accepted = conn.execute("SELECT COUNT(*) FROM audit_trail WHERE ai_decision='ACCEPT'").fetchone()[0]
        negotiate_or_reject = conn.execute(
            "SELECT COUNT(*) FROM audit_trail WHERE ai_decision IN ('NEGOTIATE','REJECT')"
        ).fetchone()[0]
        pending_hitl = conn.execute(
            "SELECT COUNT(*) FROM audit_trail WHERE stage='ai_risk_analysis' AND reviewer_decision IS NULL"
        ).fetchone()[0]
    return {
        "total_processed": total,
        "auto_accepted": accepted,
        "needs_negotiation": negotiate_or_reject,
        "pending_lawyer_review": pending_hitl,
        "auto_accept_rate_estimate": round(accepted / total * 100, 1) if total else 0,
    }


def export_csv(output_path: str = "audit_export.csv") -> str:
    """Export audit trail to CSV for client audit or compliance submission."""
    import csv
    initialise_db()
    with _get_connection() as conn:
        rows = conn.execute("SELECT * FROM audit_trail ORDER BY timestamp").fetchall()
    with open(output_path, "w", newline="") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=dict(rows[0]).keys())
            writer.writeheader()
            writer.writerows([dict(r) for r in rows])
    return output_path
