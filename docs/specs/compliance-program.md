# Spec - Compliance Program (AUSTRAC Steps 1, 3-policies, 4)

> **Status:** not built (placeholder). Governance roles are partly captured at
> onboarding. **Grounded in:** *Program overview*, *Step 1 - Governance framework*,
> *Step 3 - AML/CTF policies*, *Step 4 - Review and update your program*.

This section is the **AML/CTF program container**: the governance framework that
owns it, the **AML/CTF policies** (the second component of the program), the
**document-and-approve** workflow, and the **ongoing review/update lifecycle**. The
first component - the risk assessment - lives in Risk Profile.

## 1. AUSTRAC basis

- The program must be "**in place before you start providing a designated
  service**", "**clearly documented in writing**", "**approved by a senior
  manager**", and "**complied with**" (Program overview p.4; Act ss 26C-26G, 26U).
- Policies are "the policies, procedures, systems and controls you'll use to manage
  and mitigate your ML/TF risks [and] ensure you comply with your AML/CTF
  obligations" (Program overview p.3; Act s 26F(1)).
- Policies must be "**targeted, proportionate, ongoing and effective**" and "the
  strength of your AML/CTF policies must match the level of ML/TF risk" (Step 3 p.6).
- Review the entire risk assessment and all policies "**at least once every 3
  years**" and on triggers (Step 4 pp.4, 10, 13).
- Document updates "**within 14 days**"; senior manager approves material updates;
  notify the governing body in writing ASAP (Step 4 pp.8, 11).

## 2. User stories

- As a **compliance officer**, I assemble my firm's AML/CTF program from its risk
  assessment + a set of policies, see which obligations each policy covers, and
  send the program to a senior manager to approve.
- As a **senior manager**, I review and **approve** the program (and later material
  updates) in writing; my name, role, and date are recorded.
- As a **compliance officer**, I get prompted to review the program on a 3-year
  clock and whenever a "significant change" or AUSTRAC communication occurs, and I
  document each update within 14 days.
- As the **governing body**, I'm notified in writing when the risk assessment is
  updated and I receive the program.

## 3. Required policy areas (Step 3)

Each must exist as a policy record the firm can document, tailor, and approve
(Step 3 pp.7, 12-14). These become the **seed catalogue**:

| Policy area | Source |
|---|---|
| Customer due diligence (initial + ongoing) | p.12 -> see [clients-and-matters.md](clients-and-matters.md) |
| Triggers for source-of-funds / source-of-wealth checks | p.7 |
| Enhanced CDD triggers | pp.9-10 |
| PEP detection | p.13 |
| Targeted financial sanctions compliance & screening | pp.7, 13 |
| Transaction monitoring | p.15 |
| Suspicious matter reporting + **tipping-off** avoidance | p.13 -> see [reporting](reporting-and-recordkeeping.md) |
| Threshold transaction reporting (cash >= $10,000) | p.13 |
| Cross-border movement of bearer negotiable instruments | p.13 |
| Annual compliance report | p.13 |
| Record keeping | p.13 |
| Reliance on third parties for CDD (esp. real estate) | p.7 |
| Customer-type onboarding approval | p.7 |
| Employee due diligence + AML/CTF training | p.12 |
| Independent evaluation (frequency, independence, conduct, response) | Step 5 |
| Program review & update | Step 4 |
| Proliferation-financing controls (if PF risk > low) | p.10 |
| Travel rule (only if a relevant designated service) | pp.7, 14 |

> Test for "is this a policy?": something "directly necessary to demonstrate
> compliance" is in scope; ancillary material (e.g. software-licensing SOPs) is not
> (Step 3 p.15).

**Obligation register - statutory authorities (seed `obligation_register.act_reference`).**
Confirmed against Act Pt 1A + Rules Pt 5:

| Obligation | Authority |
|---|---|
| Carry out CDD (collect/verify circumstances + SoF/SoW triggers) | Act s26F(3)(b); **Rules s5-2** |
| Targeted financial sanctions (no assets to/dealing with designated persons) | **Rules s5-3** |
| Review & update policies (incl. on adverse evaluation finding) | Act s26F(3)(c); **Rules s5-4** |
| Policy review **at least every 3 years** | Act s26F(3)(d) |
| Senior-manager approvals (PEP / nested / third-party reliance) | **Rules s5-5** |
| Keep governing body informed | Act s26F(4)(a); **Rules s5-6** |
| Designate compliance officer / senior manager(s) | Act s26F(4)(b),(c) |
| Personnel due diligence | Act s26F(4)(d); **Rules s5-8** |
| AML/CTF training (initial + ongoing) | Act s26F(4)(e); **Rules s5-9** |
| Independent evaluation | Act s26F(4)(f); **Rules s5-10** |
| CO -> governing-body report **>= every 12 months** | **Rules s5-7** |
| Report integrity (s41/43/46/46A complete, accurate, unaltered) | **Rules s5-11** |
| Timely SMR assessment | **Rules s5-12** |
| Tipping-off safeguards | **Rules s5-13** |
| Document program before service; updates within **14 days** | Act s26N; **Rules s5-15** |
| Record keeping | Act **s116** |

## 4. Data model

```
aml_program
  id, firm_id, status enum('draft','approved','under_review'),
  version int, documented_at, created_at, updated_at,
  risk_assessment_id FK,                 # links the two components
  approved_by_user_id, approved_by_name, approved_by_role, approved_at,
  next_review_due_at                      # approved_at + 3 years

policy
  id, firm_id, program_id FK, area_key, title, body (text/markdown),
  status enum('draft','approved'), version int,
  risk_links jsonb,        # which ML/TF risks it mitigates
  obligation_links jsonb,  # which obligations it satisfies (coverage)
  created_at, updated_at

obligation_register        # seeded from section 2 of README + Step 3 checklist
  id, firm_id (null=global), key, description, act_reference,
  covered_by_policy_id (nullable), status enum('covered','gap')

program_change_log         # Step 4 section C
  id, firm_id, program_id, entity_type enum('risk_assessment','policy'),
  entity_id, change_summary, trigger ('3_year'|'significant_change'|
  'austrac_communication'|'evaluation_adverse_finding'|'other'),
  is_material bool, changed_by_user_id, changed_at,
  documented_within_14d bool, approval_id (nullable FK),
  governing_body_notified_at (nullable)
```

Extend existing:
- **`governance_roles`** - adopt four CHECK-constrained role keys: `governing_body`,
  `senior_manager`, `compliance_officer`, `independent_evaluator` (Act ss26H, 26J;
  s5; Step 5 p.6). **One user may hold several** (sole practitioner case) and
  **multiple `senior_manager` rows are valid** (Act s5; Senior-manager p.3) - so no
  uniqueness on `user_id`. Add an eligibility sibling:
  ```
  governance_role_eligibility
    role_id FK, qualifies_reason text,        # s5 SM decision test / CO management-level basis
    is_australian_resident bool,              # CO hard rule when firm has an AU permanent establishment (s26J(3)(a))
    fit_and_proper_completed_at,              # CO, s26J(3)(b)
    fit_and_proper_considered jsonb,          # the 7 Rules s5-14 factors weighed
    fit_and_proper_evidence jsonb,            # checks considered (police/credit/reference/open-source) - s116
    last_reassessed_at, austrac_notified_at   # CO notification, s26M
  ```
- **`GovernanceApproval`** - today it stores only `title, rationale, status, due_at`
  and **cannot record who approved or when**. Add, to satisfy the name/role/date rule
  (Act s26P; Senior-manager p.8):
  ```
  + approved_by_user_id, approver_name, approver_role
  + decided_at, decision enum('approved','not_approved'), decision_reason
  + subject_type enum('program','policy','risk_assessment',
                      'pep_relationship','third_party_cdd','nested_services','other')
  + subject_id, escalation_reason
  ```
  Beyond program approval (s26P), a senior manager must also approve, per **Rules
  s5-5**: foreign-PEP relationships; domestic/intl-org PEPs where risk is high;
  nested-services relationships; entering a third-party-CDD reliance agreement.
- Reuse `ComplianceDeadline` for: the **3-year** review clock; **CO designation <=28
  days** of first service (s26K); and **AUSTRAC CO-notification <=14 days** of
  designation (s26M; transitional default = later of enrol+14 days or 29 Jul 2026,
  Transitional Rules s19). Use `ReviewTrigger` for event-driven reviews.

**Governance roles - eligibility rules (resolves R11):**

| Role | Hard rule (block) | Soft / "consider" (warn) |
|---|---|---|
| **Governing body** (s26H) | must exist; oversees RA + compliance; **receives** RA-update notice (s26P(2)) + the >=12-monthly CO report (Rules s5-7) | - |
| **Senior manager** (s5) | makes/participates in decisions affecting "the whole or a substantial part" of the business; **approves** the program + material updates (s26P) - non-delegable | capture `qualifies_reason` |
| **Compliance officer** (s26J) | **management level** (s26J(2)(a)); **AU resident** if firm has an AU permanent establishment (s26J(3)(a)); a **fit-and-proper determination must exist** (s26J(3)(b)) | the 7 fit-and-proper factors (Rules s5-14) are "consider, **not pass/fail**"; flag conflicts of interest (esp. ties to an AML/CTF software vendor - relevant to Onus itself) |
| **Independent evaluator** (Step 5) | **cannot** be the compliance officer / compliance team or anyone who built/maintains the program | internal vs external; suitability scorecard |

## 5. The review/update lifecycle (Step 4)

**Significant-change triggers** (review required; p.4-7) - a change to any of:
1. designated services, 2. how services are delivered, 3. customer types,
4. countries dealt with, 5. new/emerging technologies. Plus: AUSTRAC communicates
risk info; an evaluation report has adverse findings.

**Timing** (p.6-7):

| Trigger | Review timing |
|---|---|
| Significant change **within** control | **Before** the change occurs |
| Significant change **outside** control (e.g. sanctions) | ASAP **after** |
| AUSTRAC communication | ASAP after it's received |
| Governing body receives adverse evaluation finding | ASAP after receipt |

A change with no ML/TF-risk impact (e.g. a cosmetic website update) is **not** a
trigger (p.6).

## 6. API (engine)

- `GET /program` - program + policies + obligation coverage + next review date.
- `POST /program/policies`, `PATCH /program/policies/{id}` - author/edit a policy.
- `POST /program/submit-for-approval` -> creates a `GovernanceApproval`.
- `POST /program/approve` - senior-manager approval (records name/role/date; gates
  go-live; sets `next_review_due_at`).
- `POST /program/changes` - log a change (starts the 14-day timer; flags material ->
  requires approval; queues governing-body notification).
- `POST /program/triggers` - register a significant-change/AUSTRAC trigger ->
  `ReviewTrigger`.
- `GET /program/obligations` - the obligation register with coverage status.

## 7. UI (web) - `/compliance-program`

- **Overview**: status banner (draft / approved / under review), program version,
  next review due, the approval record, and a **document-and-approve** call to
  action gated on the risk assessment being complete.
- **Policies**: list by area (seed catalogue), each showing coverage of obligations
  and the risks it mitigates; editor with Onus-drafted starting content.
- **Obligation register**: coverage map - green where a policy covers an obligation,
  amber where there's a **gap**.
- **Governance**: the four roles, who holds each, appointment dates (read/edit ties
  to Settings).
- **Program lifecycle**: 3-year review countdown, active review triggers, and a
  change log with the 14-day documentation status per entry.

## 8. Onus (AI) role

- **Draft each policy** from the firm's risk assessment + the Step 3 requirements,
  tailored to firm size ("simpler measures" for small firms - Step 3 p.6).
- Maintain the **obligation register** and surface coverage **gaps**.
- Detect significant changes (new service/customer/country in Clients & Matters,
  sanctions-list changes) and **raise review triggers** with the correct timing.
- Draft governing-body notifications and approval summaries. **A senior manager
  still approves**; Onus never self-approves.

## 9. Compliance gates & automations

- **Go-live gate**: a firm cannot mark a designated service as provided until the
  program is `documented` **and** `senior_manager_approved` (Program overview p.4).
- **14-day timer** auto-starts on any change-log entry; overdue -> Dashboard action.
- **Material change** -> requires `GovernanceApproval` before it takes effect.
- **Risk-assessment update** -> auto-create governing-body notification task.
- **3-year clock** -> `ComplianceDeadline` (`risk_assessment_review`); already
  created at onboarding.

## 10. Acceptance criteria

- [ ] A firm can assemble a program (RA + policies), submit it, and a senior manager
      approval is recorded with name/role/date before go-live.
- [ ] The obligation register shows coverage and flags gaps.
- [ ] Logging a significant change starts a 14-day timer and, if material, blocks
      until approved.
- [ ] A review trigger appears on the Dashboard with the correct "before vs after"
      timing.
- [ ] 3-year review countdown is visible and drives a deadline.

## 11. Refer-outs - resolved

- **R11 ** eligibility - senior manager = Act **s5** decision test; compliance
  officer = **s26J** (management level + AU residency + fit & proper) with the 7
  fit-and-proper factors in **Rules s5-14**; designation/notification timing
  ss26K/26M (+ Transitional Rules s19). Encoded in section 4.
- **Obligation `act_reference`s ** - confirmed against Act Pt 1A + Rules Pt 5 (the
  section 3 authorities table).
- **Residual:** AUSTRAC has signalled it may later recognise existing fit-and-proper
  checks (guidance "late 2026") - keep the fit-and-proper factors as a non-blocking
  "consider" checklist, not a hard pass/fail. The "AFSL-only" entity carve-out
  (s26T: s26H, s26P(2), Div 5 don't apply) is unlikely to bind a law firm - one-line
  guard only.
