# Spec - Independent Evaluation (AUSTRAC Step 5)

> **Status:** not built (placeholder; a 3-year deadline is created at onboarding).
> **Grounded in:** *Step 5 - Conduct an independent evaluation*.

A periodic, **independent** evaluation of the whole AML/CTF program - separate from
and additional to the firm's own reviews (Step 4). For a sole practitioner / very
small firm this almost always means an **external** evaluator, because the
compliance officer cannot evaluate their own work.

## 1. AUSTRAC basis

- "Your AML/CTF policies **must ensure that independent evaluations are
  conducted**" (Step 5 p.1; Act s 26F(4)(f), Rules s 5-10).
- "must set out the **frequency** ... appropriate to the nature, size and complexity";
  "**at a minimum ... at least once every 3 years**" (p.4; Act s 116).
- **First-evaluation deadline (newly regulated entities, incl. law firms) -   Transitional Rules s17:** staggered by the **last two digits of the firm's AUSTRAC
  enrolment identifier (AAN)**: both odd -> **30 Jun 2029**; second-last odd / last
  even -> **31 Dec 2029**; both even -> **30 Jun 2030**; second-last even / last odd ->
  **31 Dec 2030**. (Legacy path - *previously* regulated entities with a prior Part A
  review - is Transitional Rules s16: later of "4 years after last review" and
  "31 Mar 2027". Edge case; not the law-firm default.)
- The evaluator must do all three (p.3, p.8): evaluate **how the risk assessment was
  undertaken/reviewed** against the Act/Rules; evaluate the **design of the
  policies**; **test whether** the firm identified/assessed/mitigated/managed ML/TF
  risk and **complied** with its policies.
- A **written report** is required and **must go to the governing body and the
  senior manager responsible for approving the program** (p.10).
- The firm **must set out how it will respond**; adverse findings -> review and, if
  required, update the risk assessment and/or policies (pp.11-12); document updates
  **within 14 days** (p.13); keep records demonstrating compliance (p.14).

## 2. Independence & suitability

**Independence - the evaluator must (p.6):** have authority to exercise independent
judgement; be empowered to conduct the evaluation as they see fit; **not** be
responsible for implementing/maintaining the program; **not** have developed the
program/systems/controls; **not** have assessed the ML/TF risks; be independent of
the area evaluated - "**isn't your AML/CTF compliance officer or a member of the
compliance team**." Internal *or* external is allowed (p.6).

**Suitability - no mandatory qualifications, but expect (p.7):** knowledge of the
AML/CTF obligations applying to the business; experience/knowledge of the sector and
its ML/TF risks; (bonus) AML/CTF compliance experience, evaluation experience,
report-writing experience, certifications, professional-body membership.

## 3. Data model

```
independent_evaluation
  id, firm_id, program_id FK,
  scheduled_for, frequency_months, frequency_rationale text,   # p.4-5
  is_first_evaluation bool,        # first one is deadline-driven (Transitional Rules s17)
  statutory_deadline date,         # computed from AAN last-2-digits once enrolment ID known
  status enum('scheduled','in_progress','report_received','remediating','closed'),
  evaluator_id FK, started_at, report_received_at,
  distributed_to_governing_body_at, distributed_to_senior_manager_at,  # p.10
  created_at

evaluator
  id, firm_id, name, kind enum('internal','external'),
  independence_checklist jsonb,   # the 6 negative criteria (p.6)
  independence_confirmed bool,
  suitability_scorecard jsonb,    # sector knowledge, experience, certs (p.7)
  selection_rationale text

evaluation_report               # required sections (p.10)
  id, evaluation_id, summary_of_process, aspects_reviewed,
  method, findings_risk_assessment, findings_policy_design,
  findings_compliance, items_tested, files_sampled, sampling_method,
  document_ref, created_at

evaluation_finding
  id, evaluation_id, area enum('risk_assessment','policy','compliance'),
  is_adverse bool, description,
  owner_user_id,                  # "who's responsible" (p.14)
  remediation_action, status enum('open','in_progress','done','wont_fix'),
  wont_fix_reason text null,      # disagreement allowed but must be recorded (p.13)
  linked_change_id (nullable),    # program_change_log entry
  effectiveness_checked_at        # post-remediation monitoring (p.13)
```

Reuse `ComplianceDeadline` (`independent_evaluation`, created at onboarding) and the
`program_change_log` / `GovernanceApproval` from
[compliance-program.md](compliance-program.md) for remediation + approvals.

## 4. Workflow

```
schedule (<= 3 yrs; document frequency rationale) -> select evaluator
   |- independence gate: block compliance officer / compliance team (p.6)
   +- suitability scorecard + selection rationale (p.7)
        |
        v  evaluation conducted (evaluator given access to docs/people/systems, p.9)
        |
   written report received -> DISTRIBUTE to governing body + approving senior manager (p.10)
        |
   triage findings:
     |- adverse re risk assessment -> review (+ update) RA, then policies (p.12)
     |- adverse re policies -> review (+ update) policies (p.12)
     |- disagree? allowed, but record wont_fix_reason (p.13)
     +- document updates within 14 days; communicate to staff; MONITOR effectiveness (p.13)
        |
   close when findings resolved / effectiveness confirmed
```

## 5. API (engine)

- `GET/POST /evaluations` - schedule (frequency + rationale).
- `POST /evaluations/{id}/evaluator` - assign; **independence gate** rejects the
  compliance officer / compliance-team members.
- `POST /evaluations/{id}/report` - capture the report's required sections.
- `POST /evaluations/{id}/findings` + `PATCH /findings/{id}` - remediation tracker
  (owner, status, wont_fix_reason, effectiveness check).
- `POST /evaluations/{id}/distribute` - record distribution to governing body +
  senior manager (timestamps).
- Adverse findings auto-create `ReviewTrigger`s for the RA/policies (Step 4 linkage).

## 6. UI (web) - `/evaluation`

- **Schedule**: next-due countdown (<=3 yrs), frequency + rationale, transitional
  first-evaluation note (R10).
- **Evaluator**: register with the **independence checklist** (6 criteria) and a
  **suitability scorecard**; the conflict gate visibly blocks the compliance officer.
- **Evidence pack**: assemble what evaluators request (RA + policy docs, current RA,
  policies, CDD & transaction records, prior monitoring/review outputs, previous
  evaluation reports) (p.9).
- **Report intake**: form enforcing the required sections (p.10).
- **Findings tracker**: each finding with owner, remediation, status, links to the
  change/approval, and effectiveness check; "won't fix" requires a reason.

## 7. Onus (AI) role

- Schedule and remind; **assemble the evidence pack** automatically from program +
  Clients & Matters data.
- Run the **independence check** and flag conflicts; help score suitability.
- Map each adverse finding to the affected RA factor / policy and **draft the
  remediation + the review trigger**; track the 14-day documentation timer and
  effectiveness re-check. Onus does **not** perform the evaluation (independence).

## 8. Compliance gates & automations

- **Independence gate**: cannot assign an evaluator who is the compliance officer /
  compliance team or who built/maintains the program or assessed the risks (p.6).
- **Distribution gate**: report must be marked distributed to governing body +
  approving senior manager (p.10).
- Adverse finding -> `ReviewTrigger` (RA and/or policy) + 14-day documentation timer
  on the resulting update (p.13).
- **Effectiveness loop**: if an issue persists after remediation, auto-open a
  further review (p.13).

## 9. Acceptance criteria

- [ ] Scheduling captures a frequency <= 3 years with a documented rationale.
- [ ] Assigning the compliance officer as evaluator is blocked with an explanation.
- [ ] A received report records all required sections and is distributed to the
      governing body + approving senior manager (timestamps stored).
- [ ] An adverse finding opens the matching RA/policy review trigger and a 14-day
      documentation timer.
- [ ] A "won't fix" finding requires and stores a reason.

## 10. Refer-outs - resolved

- **R10 ** first-evaluation deadlines - **Transitional Rules s17** (AAN-staggered:
  30 Jun 2029 / 31 Dec 2029 / 30 Jun 2030 / 31 Dec 2030); s16 for previously-regulated.
  Until the firm's AAN is known, default the schedule to the **earliest bucket
  (30 Jun 2029)** and recompute on enrolment.
- **R6 ** retention of evaluation records - **Act s116** (7 years from when the
  record is "no longer relevant" - see reporting spec section 5).
- Optional (not a compliance gap): a **directory of qualified external evaluators** -   product decision; for a sole practitioner the evaluator must be external (the
  compliance officer cannot self-evaluate, Step 5 p.6).
