Responsible AI Checklist - Contract Intelligence Agent

This checklist maps to the SRA's guidance on AI use in legal services (SRA Risk
Outlook 2024) and the Law Society's principles on the use of AI in legal practice.

---

1. Human Oversight

- [x] HITL mandatory for high-risk decisions - NEGOTIATE and REJECT assessments always require lawyer review
- [x] HITL mandatory for low-confidence decisions - Any AI confidence below 0.85 triggers human review
- [x] AI recommendation presented before reviewer input - prevents anchoring in reverse
- [x] Override is always available - reviewer can select any outcome regardless of AI recommendation
- [x] Override requires documentation - notes field mandatory for any non-agreement decision
- [x] No automatic redline transmission - proposed language is drafted only; a lawyer must review and send

2. Transparency and Explainability

- [x] Structured reasoning chain - every assessment includes numbered reasoning factors
- [x] Explicit key deviations and mitigating factors - not just a score
- [x] Confidence score always shown - reviewers understand AI certainty level
- [x] Playbook source documented - reviewers know which standard position each clause was compared against
- [x] Primary concern clause labelled - connects the overall decision to a specific clause when applicable

3. Audit Trail Integrity

- [x] AI decision logged before reviewer sees it - immutable record of what the AI recommended
- [x] Reviewer decision logged with identity - reviewer_id required
- [x] Final outcome always recorded - what actually happened, regardless of AI recommendation
- [x] Append-only audit trail - no delete or update operations on logged decisions
- [x] CSV export for client audit or file review
- [x] Timestamp precision - UTC timestamps on all entries

4. Data Minimisation and Confidentiality

- [x] No client-identifying commentary generated beyond what is in the contract itself
- [x] Enrichment limited to playbook, jurisdiction, and precedent facts
- [x] Contract data not sent to external services - playbook and precedent lookups are mocked/internal in production
- [ ] Data retention policy - audit trail retention must align with the firm's file retention policy and any client-specific confidentiality terms

5. Model Risk

- [x] Confidence thresholds defined and documented - not arbitrary; tied to HITL routing logic
- [x] Low temperature for risk analysis - temperature 0.1 ensures consistency for the same clause set
- [ ] Alignment tracking - recommend tracking AI vs. reviewer decision alignment rate over time
- [ ] Model drift monitoring - recommend periodic review of override rate and decision distribution by contract type
- [ ] Formal model documentation if deployed as a firm-wide tool, aligned to the firm's professional indemnity insurer's expectations

6. Bias and Fairness

- [x] No party demographic signals used - assessments based on clause text and playbook comparison only
- [x] Reasoning must reference specific clauses and sections - prevents unexplained or proxy-based flags
- [ ] Fairness monitoring - recommend tracking flag rates by counterparty jurisdiction and contract type to detect unintended patterns

7. Production Deployment Checklist (before go-live at a firm or in-house legal team)

- [ ] Partner or General Counsel sign-off on HITL thresholds
- [ ] Professional indemnity insurer notified of AI-assisted review tooling, if required
- [ ] Integration with the firm's clause library and document management system (replace mock playbook tools)
- [ ] Integration with document assembly / redlining tooling (e.g. Office JS add-in) for approved redlines
- [ ] User acceptance testing with a lawyer cohort across contract types
- [ ] Training programme for reviewing lawyers
- [ ] Incident response procedure for AI failure or an incorrect assessment reaching a client
- [ ] Client-facing disclosure of AI-assisted review, if required by engagement terms
