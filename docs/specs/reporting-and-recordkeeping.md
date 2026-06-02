# Spec - Reporting & Record Keeping (AUSTRAC)

> **Status:** not built (only the AUSTRAC enrolment deadline exists). **Now grounded
> in primary law** - refer-outs R6, R7, R8, R9, R12 resolved. Sources: Act
> (C2026C00119, Comp 60) Pt 3 (reporting), Pt 10 (records), Pt 11 (tipping-off);
> Rules (F2026C00274, Comp 1) Pt 9 (report contents), Pt 8 (travel rule); AUSTRAC
> "Suspicious matter reports" and "Record keeping overview".

## 1. The reports - triggers, deadlines, thresholds

| Report | Trigger | Deadline | Authority |
|---|---|---|---|
| **Enrolment** | Commencing a designated service | Enrol from **31 Mar 2026**; **within 28 days** of first providing a designated service (firms operating on day one: by **29 Jul 2026**); obligations commence **1 Jul 2026** | Act **s51B(1)** |
| **SMR** (terrorism financing) | Reasonable grounds to suspect, s41(1)(g)/(h) | **24 hours** after forming the suspicion | Act s41(2)(b) |
| **SMR** (all other) | Reasonable grounds to suspect, s41(1)(d)-(j) | **3 business days** after the day suspicion formed | Act s41(2)(a) |
| **SMR** (partial LPP, non-TF) | as above, but the firm reasonably believes *some but not all* of the information is privileged and the privilege belongs to another person | **5 business days** after the day suspicion formed | **Act s41(2)(aa)** (inserted by Amendment Act 2024 Sch 4, commences 1 Jul 2026); Rules 9-2(1)(d) |
| **TTR** | Designated service involves a threshold transaction (**physical currency >= $10,000**) | **10 business days** after the transaction | Act ss5, 43(2) |
| **IVTS** (formerly IFTI) | International transfer of value, s45 - **only if the firm carries on a remittance/value-transfer business; not a routine law-firm obligation** | **10 business days** after passing on/receiving the transfer message | Act s46(2); s46A(2) for self-hosted wallets |
| **Annual compliance report** | Annual | Period **1 Jul - 30 Jun**; due within **3 months** -> **30 Sep** (first: due 30 Sep 2027) | Act s47; Rules s9-9 |
| **Cross-border movement** | ***Any person*** physically moving **>= $10,000** in currency or bearer negotiable instruments across the border (not tied to providing a designated service) | per **Act s53** | reporting details in AML/CTF Rules Pt 9 (refer-out, lower priority) |

> **Wholly privileged SMR (Act s41(2A)):** where the firm reasonably believes that *all*
> the relevant information is privileged (privilege belonging to another person), it may
> **refuse to lodge** rather than report. The 5-business-day rule above is only for *partial*
> privilege. Terrorism-financing grounds (s41(1)(g)/(h)) stay at 24 hours regardless.

> "Business days" exclude weekends/public holidays; the count starts the **day after**
> the suspicion is formed (AUSTRAC p.8). Store a computed `due_at` + a `deadline_basis`.

## 2. Reporting trigger detail

- **SMR (Act s41):** an obligation arises when the firm provides / is asked to provide
  / is asked whether it would provide a designated service **and suspects on
  *reasonable grounds*** (objective standard) any of s41(1)(d)-(j): person not who they
  claim; info relevant to a tax/Commonwealth/State/Territory offence or proceeds of
  crime; preparatory to or relevant to **terrorism financing** or **money laundering**.
  Applies even if the service is never provided. **A new suspicion = a new SMR.** The
  report must include a **statement of the grounds** (s41(3)).
- **TTR:** the only hard threshold in the regime - **physical currency >= $10,000**
  (Act s5). Structuring below $10k is itself an SMR indicator.
- **Annual compliance report:** report on compliance with the Act/regs/Rules for the
  financial-year period; content is the AUSTRAC approved-form answers; AFSL-only
  entities exempt (s47(5)).

## 3. Data model

```
report
  id, firm_id,
  type enum('smr','ttr','ifti','annual_compliance','cross_border_bni','enrolment'),
  status enum('draft','ready','lodged','not_required'),
  related_client_id null, related_matter_id null, related_alert_id null,
  payload jsonb,                  # per-type schema, section 4
  deadline_basis enum('smr_tf_24h','smr_3bd','smr_lpp_5bd','ttr_10bd','ifti_10bd',
                      'annual_3mo') null,
  lpp_claimed bool default false, lpp_form_ref text null,   # SMR only (Act s242)
  due_at, lodged_at, lodged_by_user_id, reference_number text null,  # AUSTRAC receipt
  content_hash, created_at, updated_at      # integrity: "complete, accurate, free from unauthorised change"

report_decision_log             # why we did / didn't report (Risk insights p.6; Rules s5-12)
  id, firm_id, report_id null, client_id, matter_id,
  reasonable_grounds bool, reasoning text, decided_by_user_id, decided_at

record                          # the retention spine (section 5)
  id, firm_id, category enum(...section 5),
  entity_type, entity_id,
  retention_basis enum('from_creation','from_receipt','from_relationship_end',
                       'from_no_longer_relevant'),   # determines how retention_until is computed
  basis_date date,              # the event the 7 years runs from (per regime)
  retention_until date,         # basis_date + 7 years
  storage_ref, immutable bool, created_at
```

Reuse `ComplianceDeadline` (enrolment + annual report); `AuditLog` as the immutable
trail; `monitoring_alert` (Clients & Matters) as the SMR source. **Amend/withdraw a
lodged SMR/TTR/IFTI only on AUSTRAC-CEO request** (Rules s9-9B; Act s48A) -> append/
version-only.

## 4. `report.payload` field schemas (per type)

Model a shared **`ReportablePerson`** (Rules 9-3 / 9-7): *individual* = full name,
other names, DOB, gender, citizenship[], tax-residence[], addresses, phone, email,
occupation, unique id, verification-data description (+ Digital ID ref; + description/
image-held when identity unestablished); *non-individual* = full name, other names,
country of incorporation/registration, tax-residence[], registered/business/postal
addresses, phone, email, principal activity, legal form, **beneficial_owners[]**,
governance individuals (+ director ID), express-trust block (trustee/settlor/
appointor/guardian/protector/beneficiaries), unique id, verification-data description.

- **`smr`** (Rules 9-2/9-3/9-4): `general` (RE name + AUSTRAC id, dates, `lpp_timeframe_applies`,
  previous-report refs, completed-by, suspicion-contact, prior agency report) -   `subject_person: ReportablePerson` - `involved_persons[]` (role + relationship) -   `matter` (trigger circumstance s41(1)(a)-(c), conditions s41(1)(d)-(j), dates,
  offence, locations, **`grounds_for_suspicion` (mandatory narrative, s41(3))**) -   conditional `account` / `transactions[]` / `property_transfers[]` /
  `virtual_assets[]` (incl. wallet addresses) / `online_activity[]`.
  **Never include:** TFNs; dummy/"N/A"/"unknown"; name abbreviations (AUSTRAC p.24).
- **`ttr`** (Rules 9-6/9-7/9-8): `general` - `persons` (customer, counterparty,
  on-behalf-of, customer agent, unattended/courier statement) - `transaction`
  (datetime, location, roles, designated-service kind, RE ref, **physical-currency
  value AUD**, FX, conditional account/instruments/property/virtual-asset/online).
- **`ifti`** (Act s46; Rules Pt 8 travel rule s8-3/8-4/8-5): `service_kind`
  (item29|item30), `direction` (au_to_foreign|foreign_to_au), `role`
  (ordering|beneficiary|intermediary), `transfer_message_event`, **`payer_information`**,
  **`payee_full_name`**, **`tracing_information`**, value AUD + FX, optional
  `self_hosted_wallet` (s46A), `intermediary_discharge`.
- **`annual_compliance`** (Act s47; Rules 9-9): `reporting_period_start` (first
  2026-07-01), `reporting_period_end` (first 2027-06-30), `approved_form_answers`
  (populated when AUSTRAC publishes the form).

## 5. Record keeping & retention (R6 - the four-regime correction)

Note: Retention is **7 years for everything, but the 7 years runs from a *different
event* per category** - a single `created_at + 7y` default is **wrong** for CDD and
program records. The `record.retention_basis` enum drives the calculation:

| Category | Authority | `retention_basis` | 7 years runs from |
|---|---|---|---|
| **Transaction records** (reconstruct each transaction) | Act s107 | `from_creation` | day the record is made |
| **Customer-provided documents** | Act s108 | `from_receipt` | day the document was given to you |
| **CDD records** (initial + ongoing: info collected, verification steps, risk analysis/decisions) | Act s111 | `from_relationship_end` | the day the **business relationship ends** / occasional transaction completes |
| **Third-party-reliance CDD copy / agreement assessment** | Act s114 / s114A | `from_relationship_end` / `from_creation` | (assessment record: prepared within **10 business days**, then 7 yrs) |
| **AML/CTF program records (Pt 1A)** - RA + versions, policies + versions, approvals, governance, CO appointment + fit-and-proper evidence, training, evaluation reports + remediation, AUSTRAC communications, reporting logs | Act s116 | `from_no_longer_relevant` | when the record is **"no longer relevant"** to Pt 1A compliance (professional judgement - e.g. when a RA/policy version is superseded) |

**Form/accessibility (Act ss111(2)(b), 116(1)(b)):** **English** (or readily
convertible to English in writing); kept in original/usual format (don't convert in a
way that changes structure - keep a spreadsheet as a spreadsheet); hard-copy or
electronic; on/offsite or via a provider; **sensitive records (IDs, SMRs) stored
securely with restricted access**; Privacy Act applies. Must be **producible on
AUSTRAC-CEO written notice** (Act s26Q) -> reuse the Audit Trail + record vault; nothing
hard-deletes (aligns with the platform no-permanent-delete rule).

## 6. UI - Onus role

- **UI `/reporting`:** reports dashboard (by type + status, with due dates; SMRs from
  alerts appear here); **SMR builder** (payload pre-filled by Onus, review -> ready ->
  record AUSTRAC reference; tipping-off banner throughout); annual-compliance schedule;
  **records register** with per-regime retention countdowns; enrolment status (moves
  here from Settings).
- **Onus:** drafts SMR narratives from alert + matter context; flags TTR when cash >=
  $10k; tracks report due-dates + retention timers and warns before lapse. **Never
  auto-lodges; never tips off.**

## 7. Compliance gates & automations

- Cash transaction **>= $10,000** -> auto-draft a **TTR** (timer: 10 business days).
- Alert escalated with reasonable grounds -> auto-draft an **SMR** + `report_decision_log`
  (timer: 24h TF / 3 bd other / 5 bd LPP-flag).
- Reports are **append/version-only**; `content_hash` mismatch flagged (Rules s5-11).
- Per-regime **retention timers** on every `record`; lapse warnings -> Dashboard.
- Enrolment + annual-report deadlines -> `ComplianceDeadline` -> Dashboard.

## 8. Tipping-off guardrail (R9 - Act s123)

Hard invariants: **no client-facing surface** may reveal that an SMR exists/was made/
is required, the suspicion's existence, or the SMR's contents (s123(2)). The only safe
disclosure target is **AUSTRAC**. Narrow, logged, role-restricted exceptions: good-faith
**dissuasion** of a client from offending (**s123(4)** - available to legal
practitioners); reporting-entity **info-sharing** to detect/deter/disrupt crime where
regs are met (s123(5)). **LPP** is preserved (s242) and handled as `lpp_claimed` on the
SMR - it does not weaken s123. Isolate the `report`/`monitoring_alert`/`report_decision_log`
data from any client-visible channel; suppress from notifications, matter timelines, exports.

## 9. Acceptance criteria

- [ ] An escalated alert produces a draft SMR linked to its client/matter, with a
      decision log and the correct deadline basis, and **no** client-facing notification.
- [ ] A cash transaction >= $10,000 drafts a TTR with a 10-business-day due date.
- [ ] Every report carries a content hash + audit trail; edits version; amend/withdraw
      only on recorded AUSTRAC-CEO request.
- [ ] Records compute `retention_until` from the correct per-regime basis date; nothing
      hard-deletes; CDD records survive until 7 yrs after relationship end.
- [ ] Enrolment + annual-report deadlines surface on the Dashboard.

## 10. Refer-outs - resolved

| Ref | Status |
|---|---|
| R6 retention | Act ss107/108/111/114/116 - four-regime model (section 5) |
| R7 SMR deadlines + schema | Act s41(2); Rules 9-2/9-3/9-4 |
| R8 TTR/IFTI | Act ss43, 45/46/46A; Rules 9-6...9-8, Pt 8 |
| R9 tipping-off + LPP | Act ss123, 242; Rules s5-13 |
| R12 annual report | Act s47; Rules s9-9 (1 Jul-30 Jun, due 30 Sep) |

**Residual (not blocking):** the **5-business-day LPP SMR timeframe** rests on
s41(2)(aa), which is *not* in the Comp 60 body - ship behind a **feature flag**;
confirm against the in-force s41. **Cross-border BNI** (s53 / Rules 9-12-9-13) is
lower-priority and not yet detailed. AUSTRAC **approved-form** field layouts finalise
when published; our payload schemas follow the Rules.
