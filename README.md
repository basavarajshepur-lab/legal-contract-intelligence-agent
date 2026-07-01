Contract Intelligence Agent

Multi-agent contract risk triage system - playbook comparison, missing-clause detection, risk scoring, redline drafting, HITL queue, and audit trail for transactional legal review.

Python 3.11+ | License: MIT | Status: Production-Ready Demo | Powered by Claude AI

---

Executive Summary

The Pain Points This Solves

Pain Point 1 - Every Contract Review Starts From Memory

When a lawyer reviews a commercial contract, the comparison against the firm's standard playbook position lives mostly in the reviewer's head or in a senior colleague's institutional knowledge, not in a document the reviewer can check against systematically. Different reviewers flag different things depending on experience and workload. Contract Intelligence Agent compares every clause against a documented playbook position automatically, every time.

Pain Point 2 - Missing Clauses Are the Hardest Gap to Catch

A liability cap that should be there and isn't, a data protection addendum that should exist for a contract processing personal data and doesn't - these are invisible on the page. There is nothing to notice. Contract Intelligence Agent maintains an expected-clause list per contract type and flags what is absent, not just what is present and wrong.

Pain Point 3 - Redline Drafting Starts From a Blank Page

Even an experienced lawyer spends real time drafting replacement language for a flagged clause from scratch. Contract Intelligence Agent drafts a redline memo with proposed language and a rationale the moment a contract is flagged for negotiation, so the reviewing lawyer edits and approves rather than starting cold.

Pain Point 4 - Inconsistent First-Pass Review

The same contract reviewed by two different associates on two different days can get flagged differently depending on fatigue and experience. Contract Intelligence Agent applies the same playbook logic and the same reasoning to every contract, every time.

Pain Point 5 - The Audit Trail Gap

Clients and compliance functions increasingly expect a documented rationale for why a contract was accepted, flagged, or rejected. Contract Intelligence Agent logs every AI assessment and every reviewer decision with a full timestamp and reasoning chain, exportable in seconds.

---

Business Value in Legal and Contract Operations

Cost Reduction

Metric | Before | After
Time to first-pass review one contract | 30-60 minutes | Under 10 minutes (AI pre-work done)
Contracts auto-accepted at high confidence | 0% (all manual) | 40-60% for standard, low-risk agreements
Redline drafting time for a flagged contract | 45-90 minutes | Under 20 minutes
Missing-clause detection | Inconsistent, reviewer-dependent | 100% of expected clauses checked systematically

If a legal team or firm reviews thousands of commercial contracts a year and this halves first-pass review time on standard agreements, that capacity can be redirected to the contracts that genuinely need senior judgment.

Risk Reduction

Missed liability exposure, one-sided indemnification, and unenforceable non-compete clauses are the kind of gaps that surface expensively later, in a dispute or renegotiation, rather than at signature. Systematic playbook comparison and missing-clause detection catch these before signature, not after.

Associate Retention

Contract Intelligence Agent removes the most repetitive part of transactional review - re-deriving the standard playbook position from memory for routine agreements - leaving lawyers to focus on judgment calls: is this deviation acceptable given the commercial context, and how hard should we push in negotiation.

---

The Problem

Large firms and in-house legal teams review a high volume of similar commercial contracts: MSAs, vendor agreements, NDAs, licensing deals, leases, employment agreements. Most of the first pass is not novel legal reasoning - it is playbook comparison. That comparison is done manually, inconsistently, and from memory.

Missing clauses are the hardest gap to catch, because there is nothing on the page to notice.

The problem is not that lawyers cannot spot a bad clause. It is that first-pass review does not scale consistently across reviewers, contract volume, and time pressure.

---

What Contract Intelligence Agent Does

A three-agent pipeline that triages a contract from raw clauses to a documented risk assessment in under 30 seconds:

```
                    CONTRACT INTELLIGENCE PIPELINE

  Contract                 Enrichment Agent            Risk Analysis Agent
(clauses)     ----->    * Playbook lookup     ---->   * Risk score 0-100
                         * Missing clause check         * ACCEPT/FLAG/
                         * Jurisdiction risk               NEGOTIATE/REJECT
                         * Deal precedent search         * Reasoning chain
                                                          * Confidence 0-1
                                                                |
                                    -----------------------------
                                    |                           |
                              [confidence                  [NEGOTIATE/REJECT]
                               < 0.85 OR                        |
                              NEGOTIATE/REJECT]           Redline Agent
                                    |                     * Proposed language
                                    v                     * Negotiation priority
                             HITL Review Queue            * Recommended reviewer
                            (Lawyer Review UI)     <-----------
                            Agree / Override
                                    |
                                    v
                              Audit Trail (SQLite)
                          Every decision logged.
                          Append-only. Exportable.
```

---

Features

- Enrichment Agent - compares every clause against the firm's playbook using Claude tool use: playbook position lookup, expected-clause check, jurisdiction risk rating, deal precedent search
- Risk Analysis Agent - structured reasoning at low temperature: risk score, decision, confidence, numbered reasoning chain, key deviations, mitigating factors
- Redline Drafting Agent - drafts a redline memo with proposed language and rationale per flagged clause; only runs on NEGOTIATE/REJECT decisions; always requires lawyer review before anything is sent
- HITL Queue - assessments below 0.85 confidence, and all NEGOTIATE/REJECT decisions, route to lawyer review before any action is taken
- Audit Trail - append-only SQLite log: AI recommendation -> reviewer decision -> final outcome. Exportable to CSV
- Streamlit UI - lawyer review interface with playbook comparison panel, reasoning display, decision workflow, and queue dashboard
- Batch processing - process a JSON file of contracts via CLI; download results as CSV
- 10 sample contracts - covering MSAs, vendor agreements, NDAs, employment, licensing, leases, partnerships, and sales contracts, across ACCEPT, FLAG, NEGOTIATE, and REJECT outcomes

---

Quick Start

```bash
git clone https://github.com/basavarajshepur-lab/legal-contract-intelligence-agent
cd legal-contract-intelligence-agent
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
streamlit run app.py
if the above command doesn't work then execute - python -m streamlit run app.py
```

CLI - process a single contract:
```bash
python run_pipeline.py --contract data/sample_contracts.json --id CONTRACT_002
```

CLI - batch process all sample contracts:
```bash
python run_pipeline.py --batch data/sample_contracts.json
```

---

Sample Output

```
Contract ID : CONTRACT_002
Decision    : NEGOTIATE  (risk score: 78/100)
Confidence  : 89%  |  HITL required: True
Audit ID    : 7a1e4f2b-...

Key deviations:
  - Liability cap clause is entirely unlimited, against a playbook expectation of 1x-3x fees paid
  - Vendor may terminate on 10 days' notice while Client requires 60 days plus cure period - notice asymmetry
  - Confidentiality obligation is one-directional, not mutual
  - Warranty clause disclaims all warranties with no reasonable-skill-and-care standard

Reasoning:
  1. Unlimited liability is the single highest-severity deviation - a services agreement of this
     value should never carry unlimited exposure for either party
  2. Termination notice asymmetry compounds the liability risk: Vendor can exit quickly while
     Client remains locked in with an uncapped exposure clock still running
  3. One-directional confidentiality is a lower-severity but real deviation from mutual market standard
  4. No mitigating factors identified given the uncapped liability position

Redline memo generated - Partner review required before sending to counterparty
```

---

Why HITL Design Is the Hard Part

The model is the easy part. Knowing when to trust it is the hard part.

Three principles drive the HITL architecture:

1. Confidence routing, not decision routing
Low-confidence ACCEPT decisions go to lawyer review just as high-risk REJECT decisions do. A wrongly auto-accepted contract is just as costly as an unnecessarily escalated one.

2. AI recommends, lawyer decides
The AI recommendation is shown to the reviewer before they input their own view. This prevents post-hoc rationalisation of the AI decision. The lawyer is reviewing the AI, not being led by it.

3. Audit trail written before the reviewer sees the recommendation
This means AI quality can be measured independently of reviewer agreement. If reviewers consistently override a particular clause type, the AI's reasoning for that type needs improving.

---

Design Decisions That Matter in Production

Decision | Why
Low temperature (0.1) for risk analysis | The same clause set should produce the same assessment. Inconsistency undermines reviewer trust and complicates explaining a decision to a client later.
Separate enrichment and analysis agents | Enrichment is tool-calling (playbook and precedent lookup); analysis is reasoning (deviation judgment). Separating them makes each testable and replaceable.
Redline memo always requires HITL | No exception. No AI-drafted language should reach a counterparty without a lawyer's review.
Confidence threshold at 0.85 | Calibrated for contract review: the cost of an unreviewed bad clause reaching signature exceeds the cost of unnecessary lawyer review time.
Mock playbook and precedent tools | Real clause libraries and deal-precedent databases (e.g. Kira Systems, Luminance, an internal DMS) require firm-specific integration. The mock tools return realistic data so the full pipeline logic is demonstrable. Swap mock functions for real lookups in production.

---

Project Structure

```
legal-contract-intelligence-agent/
├── app.py                       # Streamlit lawyer review interface
├── run_pipeline.py               # CLI runner
├── agents/
│   ├── enrichment_agent.py       # Playbook and precedent enrichment via Claude tool use
│   ├── risk_analysis_agent.py    # Structured risk scoring
│   └── redline_agent.py          # Redline memo generation
├── core/
│   ├── models.py                 # Pydantic models (Contract, RiskAssessment, AuditEntry...)
│   ├── pipeline.py                # Multi-agent orchestration
│   └── audit_trail.py             # SQLite audit logging
├── data/
│   └── sample_contracts.json      # 10 realistic contracts across 8 contract types
└── docs/
    ├── PRD.md                     # Product Requirements Document
    └── responsible-ai-checklist.md
```

---

Contract Types Covered in Sample Data

Contract | Type | Expected Decision
CONTRACT_001 | MSA, repeat counterparty, standard clauses | ACCEPT
CONTRACT_002 | Vendor agreement, unlimited liability, notice asymmetry | NEGOTIATE
CONTRACT_003 | NDA, standard mutual confidentiality | ACCEPT
CONTRACT_004 | Employment agreement, 36-month UK-wide non-compete | REJECT
CONTRACT_005 | Licensing agreement, ambiguous IP ownership, no residuals clause | NEGOTIATE
CONTRACT_006 | Commercial lease, one-sided termination, no force majeure | NEGOTIATE
CONTRACT_007 | Partnership agreement, one-sided indemnification, high-risk jurisdiction | REJECT
CONTRACT_008 | Sales contract, standard warranty and liability cap, minor payment term deviation | FLAG
CONTRACT_009 | MSA, known counterparty, low value, fully standard | ACCEPT
CONTRACT_010 | Vendor agreement processing personal data, missing data protection clause | NEGOTIATE

---

Production Considerations

This is a production-ready demo. To deploy at a firm or in-house legal team:

1. Replace mock playbook tools with the firm's actual clause library and precedent database (Kira Systems, Luminance, or an internal DMS)
2. Integrate approved redlines with document assembly tooling (e.g. an Office JS add-in) for direct insertion into the countersigned draft
3. Add user authentication and role-based access control (associate vs partner vs GC review tiers)
4. Migrate the audit trail from SQLite to a production database for firm-wide scale
5. Align audit trail retention with the firm's file retention policy and any client-specific confidentiality terms
6. Notify the firm's professional indemnity insurer of AI-assisted review tooling, if required

See docs/responsible-ai-checklist.md for the full governance framework.

---

Competitive Advantages

1. Explainability First - Not a Black Box

Many AI contract review tools give a risk score without explaining why. Contract Intelligence Agent shows its working every time: a numbered reasoning chain, the specific clauses that deviate, the mitigating factors considered, and a confidence score. No assessment is unexplained.

2. Missing-Clause Detection, Not Just Present-Clause Review

Most contract review tools analyse the clauses that are on the page. Contract Intelligence Agent maintains an expected-clause list per contract type and flags what should be there and is not - the gap that is easiest for a human reviewer to miss precisely because there is nothing to notice.

3. Human-in-the-Loop by Design, Not as an Afterthought

The system routes uncertainty to lawyers. Any assessment where the AI is less than 85% confident goes to review - even if the AI recommends acceptance. All NEGOTIATE and REJECT decisions require human review without exception. No AI in this system sends anything to a counterparty. The lawyer remains in control at all times.

4. Consistency at Scale

Contract Intelligence Agent applies identical playbook logic to every contract. The same clause reviewed on a Monday morning and a Friday afternoon gets the same risk score, the same reasoning, and the same routing decision.

5. Full Audit Chain, Built In

Before a reviewer sees the AI recommendation, it is already written to the audit log. If a reviewer overrides the AI, both decisions are recorded - creating a complete record that can be exported in minutes for client or compliance review.

6. Covers the Deviation Categories That Actually Matter Commercially

Category | Description
Liability exposure | Uncapped or excessively high liability, missing consequential damages exclusion
Indemnification imbalance | One-sided indemnification, no carve-outs, uncapped exposure
Termination risk | No cure period, unilateral termination rights, notice asymmetry
IP leakage | Assignment of pre-existing IP, no residuals clause, ambiguous ownership
Missing protections | Playbook-expected clauses absent entirely
Jurisdiction and enforcement risk | Governing law or forum that increases enforcement difficulty
Non-compete overreach | Restrictions broader than enforceable in the governing jurisdiction

---

Future Growth Opportunities

Real-Time Redlining During Negotiation

The current version analyses a completed draft. The natural next step is analysing each round of a redline exchange in real time, tracking which deviations have been resolved and which remain open across negotiation rounds.

Counterparty Risk Profile

Contract Intelligence Agent currently analyses individual contracts. The next evolution is a continuous risk profile per counterparty, combining deal history, negotiation patterns, and dispute precedent to flag counterparties who consistently push for aggressive terms before the next deal even starts.

Portfolio-Level Analysis

A law firm or in-house team holds hundreds of similar agreements. A future version would analyse the full portfolio together - identifying which counterparties hold outlier terms relative to the rest of the book, and where systemic renegotiation would create the most value.

Clause Library Auto-Update

Beyond fixed playbook positions, the system could learn from approved redlines over time, proposing playbook updates when a negotiated fallback position is consistently accepted across multiple deals.

Expansion Into Adjacent Legal Domains

The same multi-agent architecture applies directly to:
- Regulatory change triage - reading new legislation and flagging affected contract templates
- Due diligence - screening a data room of contracts for change-of-control and assignment risk ahead of an M&A transaction
- Compliance attestation - checking existing contract portfolios against a new regulatory requirement (e.g. new data protection rules)

LegalTech SaaS Platform

Contract Intelligence Agent can evolve from an internal tool into a platform offered to in-house legal teams and smaller firms that cannot justify a dedicated contract-review headcount but face the same first-pass review burden.

---

Background

Built by Basavaraj Shepur - Senior AI Product Manager with 19 years in financial services, including delivering AI-driven enterprise data and workflow automation in production for regulated environments (Deutsche Bank Chief Data Office) and building transactional applications embedded directly in professional users' workflows (JPMorgan Asset Management). This system applies the same responsible AI pattern used in those environments - confidence thresholds, human-in-the-loop gates, full audit chains, explainability-first design - to legal contract review.

---

License

MIT
