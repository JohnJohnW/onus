# Onus - Feature Specifications (Regulated Sections)

> **Status: specifications, not yet built.** These documents spec the AML/CTF
> functionality that the Onus UI currently exposes as "coming soon" placeholders:
> **Clients & Matters, Compliance Program, Reporting, and Independent Evaluation** - > plus the enhancements needed to make the already-built **Risk Profile** match
> AUSTRAC's risk-assessment requirements.

Every obligation in these specs is grounded in the AUSTRAC guidance the firm
supplied (the "develop your AML/CTF program" series, Record keeping, and the
legal-sector risk-insights page). Each spec cites the source page and the
underlying legislative provision. **Where AUSTRAC's guidance refers out to the
Act or Rules for the operative detail, we say so and do not invent it** - see
[section 6 Refer-outs](#6-refer-outs--what-must-be-sourced-before-building) below.

---

## 1. The reformed regime, in one picture

Australia's "Tranche 2" reforms bring legal practitioners under the
*Anti-Money Laundering and Counter-Terrorism Financing Act 2006* (the **Act**)
and the *AML/CTF Rules 2025* (the **Rules**). **Commencement for the legal
profession is 1 July 2026** (Program overview p.3; Risk insights p.2).

Under the reformed regime an **AML/CTF program** has **two components** - *not*
the old "Part A / Part B" split (Program overview p.3):

```
                         AML/CTF PROGRAM
                (documented - senior-manager approved)
        +---------------------------+---------------------------+
        v                           v
  1. ML/TF RISK ASSESSMENT     2. AML/CTF POLICIES
  identify + assess ML/TF/PF   policies, procedures, systems
  risk across 4 categories     & controls that manage/mitigate
  (Step 2)                     those risks and ensure compliance
                               (Step 3)
        +--------------+------------+---------------+
                       v
        ongoing: REVIEW & UPDATE (Step 4, >= every 3 yrs + triggers)
                 INDEPENDENT EVALUATION (Step 5, >= every 3 yrs)
                 RECORD KEEPING (full, accurate, secure)
                 REPORTING (SMR / TTR / IFTI / annual report)
```

> Note: **Do not use "Part A / Part B" language in the product.** The supplied
> guidance deliberately frames the program as *risk assessment + policies*
> (Program overview p.3).

"ML/TF risk" in AUSTRAC's usage **includes proliferation financing (PF)** - money laundering + terrorism financing + proliferation financing (Step 2 p.3).

---

## 2. How AUSTRAC maps to Onus sections

| AUSTRAC obligation (source) | Onus section | Build status | Spec |
|---|---|---|---|
| Establish governance framework (Step 1) | Compliance Program -> Governance | Partly built (roles captured at onboarding) | [compliance-program.md](compliance-program.md) |
| Identify & assess ML/TF/PF risk (Step 2) | **Risk Profile** | Built; **incomplete vs AUSTRAC** | [risk-profile-enhancements.md](risk-profile-enhancements.md) |
| AML/CTF policies (Step 3, policy half) | Compliance Program -> Policies | Not built | [compliance-program.md](compliance-program.md) |
| Customer due diligence (Step 3, CDD half) | **Clients & Matters** | Not built | [clients-and-matters.md](clients-and-matters.md) |
| Suspicious-activity indicators (Risk insights) | Clients & Matters -> Monitoring | Not built | [clients-and-matters.md](clients-and-matters.md) |
| Review & update the program (Step 4) | Compliance Program -> Program lifecycle | Partly modelled (`ReviewTrigger`) | [compliance-program.md](compliance-program.md) |
| Reporting: SMR / TTR / IFTI / annual report / enrolment | **Reporting** | Not built (enrolment deadline only) | [reporting-and-recordkeeping.md](reporting-and-recordkeeping.md) |
| Record keeping & retention (Record keeping) | Reporting -> Records (cross-cutting) | Audit Trail built | [reporting-and-recordkeeping.md](reporting-and-recordkeeping.md) |
| Independent evaluation (Step 5) | **Evaluation** | Not built | [independent-evaluation.md](independent-evaluation.md) |

Already shipped and **not** re-specced here: Dashboard (agent feed), Audit Trail,
Settings, Auth, the onboarding wizard.

---

## 3. Shared conventions

These specs assume the existing stack and patterns (see
[../architecture/README.md](../architecture/README.md)):

- **Engine (FastAPI)** owns the data model, Alembic migrations, and all
  compliance logic. New tables extend the existing schema in `engine/models.py`;
  every schema change is **one Alembic migration**, never `create_all`.
- **Web (Next.js App Router)** renders server components that call the engine
  through **server-side proxies** (`web/app/api/**`) so the JWT never reaches the
  client - the established pattern (`/api/firm`, `/api/onboarding`, etc.).
- **Multi-tenant isolation** via the existing row-level-security GUC
  (`app.current_firm_id`); every new table is firm-scoped with a `firm_id`.
- **Dark theme + shadcn/ui** components, matching the built pages.
- **Every spec lists**: AUSTRAC basis -> user stories -> data model -> API -> UI ->
  Onus (AI) role -> compliance gates -> acceptance criteria -> refer-outs.

---

## 4. Cross-cutting compliance mechanics

These appear in multiple sections; specs reference this section rather than
repeat it.

### 4.1 Roles (Step 1; Step 4 p.8; Step 5 p.6)
Onus must model four distinct AML/CTF roles (extend the existing
`GovernanceRole`):

| Role | Responsibility | Notes |
|---|---|---|
| **Governing body** | Oversees the program; *receives* the risk assessment, program-update notifications, and the independent-evaluation report. | "governance and executive decisions" (Step 1 p.2) |
| **Senior manager** | **Approves** the program and any material update, in writing (name, role, date). | Approval must exist *before* a designated service is provided (Step 3 p.16) |
| **AML/CTF compliance officer** | Day-to-day compliance; conducts reviews; drives remediation. | Eligibility detail is in the Act/Rules - see section 6 |
| **Independent evaluator** | Performs Step 5. **Cannot** be the compliance officer / compliance team or anyone who built or maintains the program. | Internal *or* external (Step 5 p.6) - for a sole practitioner, effectively external |

### 4.2 Approval gate + the 14-day rule
- A program (risk assessment + policies) and every **material** update **must be
  approved by a senior manager in writing** - capture **name, role, date**
  (Step 3 p.16; Step 4 p.8).
- Updates to the risk assessment or policies **must be documented within 14 days**
  of making the update (Step 3 p.14; Step 4 pp.8, 11; Step 5 p.13). -> A 14-day
  timer is a first-class, reusable mechanic.
- Risk-assessment updates **must be notified to the governing body in writing as
  soon as practicable** (Step 4 p.8).
- **Material vs administrative**: material changes need approval; routine ones
  (e.g. a software update, reordering a workflow) do not (Step 4 p.17).
- Reuse the existing `GovernanceApproval` table for approvals and surface them as
  Dashboard "Action required" items (already wired with `href`).

### 4.3 Deadlines, triggers & cadence
- Reuse `ComplianceDeadline` for fixed/periodic obligations (enrolment, annual
  report, 3-yearly reviews, independent evaluation) and `ReviewTrigger` for
  event-driven reviews.
- **Mandatory cadences (all "at least every 3 years")**: risk-assessment review
  (Step 4 p.4), policy review (Step 4 p.10), independent evaluation (Step 5 p.4).
- The **14-day documentation timer** and **3-year clocks** are the two scheduling
  primitives.

### 4.4 Record keeping & retention (cross-cutting)
- Obligation: **"create full and accurate records along with securely storing and
  managing them"** (Record keeping p.2).
- Independent-evaluation records must be "reasonably necessary to demonstrate
  compliance" (Step 5 p.14, Act s 116).
- **Retention *period* is not stated in the supplied guidance.** The AML/CTF
  regime's standard is commonly **7 years**, but this sits in the Act/Rules -   build a configurable `retention_until` and default to 7 years **flagged for
  confirmation** (see section 6).
- The existing **Audit Trail** (`audit_log`) is the spine of "demonstrate
  compliance"; every regulated action writes an `AuditLog` row.

### 4.5 Human-in-the-loop (the Onus AI principle)
Onus is an *AI GRC officer*: it **drafts, screens, monitors, schedules, and
explains**, but a human holds the regulated decision. Concretely - Onus may draft
a risk assessment, a policy, or an SMR narrative and flag suspicious activity, but
a **senior manager approves** the program and a **person** decides to lodge a
report. Never auto-submit to AUSTRAC or auto-approve. Generated artefacts carry
the AUSTRAC disclaimer posture (section 5).

### 4.6 Disclaimer posture
AUSTRAC guidance "isn't a substitute for legal advice" and "Australian courts are
ultimately responsible for interpreting these laws" (Program overview p.8; every
source's footer). Onus's generated documents and risk outputs must carry an
equivalent disclaimer and cite their AUSTRAC basis.

---

## 5. Recommended build sequence

Driven by dependency and by the **1 July 2026** commencement:

1. **Risk Profile enhancements** ([spec](risk-profile-enhancements.md)) - closes
   live gaps in a shipped feature; the risk assessment is the input to everything
   else.
2. **Compliance Program** ([spec](compliance-program.md)) - the program container,
   governance roles, policies, document-and-approve gate, review lifecycle. Makes
   the firm's program demonstrable.
3. **Clients & Matters** ([spec](clients-and-matters.md)) - CDD execution + ongoing
   monitoring; the highest-volume day-to-day workflow. Largest refer-out surface
   (KYC field schema), so sequence after the Act/Rules detail is sourced.
4. **Reporting & Record keeping** ([spec](reporting-and-recordkeeping.md)) - SMR /
   TTR / IFTI / annual report; depends on Clients & Matters for the data.
5. **Independent Evaluation** ([spec](independent-evaluation.md)) - periodic;
   lowest day-to-day frequency; depends on a documented program to evaluate.

---

## 6. Refer-outs - now resolved from primary law

These were the operative details AUSTRAC guidance delegated to the Act/Rules. They
have now been sourced from primary law (Act = *AML/CTF Act 2006* Compilation No. 60,
in force 31 Mar 2026, C2026C00119; Rules = *AML/CTF Rules 2025* Compilation No. 1,
F2026C00274; Transitional Rules = *AML/CTF Transitional Rules 2026*, F2026L00393).
Every section spec now carries the citation inline.

| # | Detail | Status | Authority |
|---|---|---|---|
| R1 | Designated services for lawyers | Resolved - **in force** in Comp 60 (Endnote 4 confirms the Act 110/2024 s6 amendment is commenced, not uncommenced) | Act s6 **Table 5** (real estate) + **Table 6** (professional services, items T6-1...T6-9); carve-outs ss6(5C)/(5E)/(6B) |
| R2 | KYC field schema per customer type | Resolved | **Rules ss6-1...6-5**; Act s28(2)/(3) |
| R3 | Simplified / standard / enhanced CDD + triggers | Resolved | Act ss28, **31, 32**; Rules ss6-16...6-22 |
| R4 | PEP definitions + required steps | Resolved | **Rules s1-5** (domestic offices), ss6-23/6-24; Act s32(c) |
| R5 | Beneficial-ownership threshold + control test | Resolved - **25% ownership OR control** | AUSTRAC Initial-CDD p.9; Rules ss6-7/6-8/6-18 |
| R6 | Record retention period + categories | Resolved - **7 years**, but from **four different start events** | Act ss107/108/111/114/116 (see reporting spec section 5) |
| R7 | SMR deadlines + field schema | Resolved - **24 hrs (TF) / 3 business days (other)**; 5 bd LPP flag | Act s41(2); Rules ss9-2/9-3/9-4 |
| R8 | TTR / IFTI mechanics | Resolved - TTR **$10k**, due **10 business days**; IFTI 10 bd | Act ss43, 45/46/46A; Rules ss9-6...9-8, Part 8 |
| R9 | Tipping-off + LPP | Resolved - offence **s123** (2 yrs/120 units); **good-faith dissuasion exception s123(4) is available to lawyers**; LPP preserved s242 | Act ss123, 242; Rules s5-13 |
| R10 | First independent-evaluation deadlines | Resolved - **staggered by last 2 digits of the AUSTRAC enrolment ID**: 30 Jun 2029 / 31 Dec 2029 / 30 Jun 2030 / 31 Dec 2030 | Transitional Rules **s17** (s16 for previously-regulated) |
| R11 | Senior-manager / compliance-officer eligibility | Resolved | Act s5 (senior manager), **s26J** (CO: management level + AU residency + fit & proper); **Rules s5-14** (7 fit-and-proper criteria) |
| R12 | Annual compliance report content + due date | Resolved - period **1 Jul-30 Jun**, due **30 Sep** | Act s47; Rules s9-9 |

**Residual items (do not block the build; track separately):**
- **5-business-day LPP SMR timeframe** - AUSTRAC states it (SMR p.8) and Rules s9-2(1)(d) references **Act s41(2)(aa)**, but that paragraph is *not* in the body of Comp 60. Ship behind a **feature flag**; confirm against the in-force s41.
- **s116 "no longer relevant" retention start** is judgement-based (not a fixed `created_at + 7y`) - the retention engine needs a per-record "superseded/closed" date input.
- **Screening data provider** (sanctions / PEP / adverse-media; e.g. OpenSanctions) - integration + licensing decision, not a legal gap.
- **Law Council "National Legal Profession AML/CTF Guidance" (Dec 2025)** - optional; refines the LPP/tipping-off UX. Act s123(4)/s242 already give the rule.
- **AUSTRAC approved forms** (SMR/TTR/IFTI/enrolment) - exact field layouts finalise when AUSTRAC publishes the forms; our payload schemas follow the Rules.

---

## 7. Legislative reference index (verified against Comp 60 / Rules Comp 1)

**Act - Anti-Money Laundering and Counter-Terrorism Financing Act 2006** (C2026C00119):
- **s5** - definitions (*senior manager*, *politically exposed person*, *threshold transaction* ["physical currency ... not less than $10,000"], *proliferation financing*)
- **s6** - designated services; **Table 5** real estate, **Table 6** professional services (legal practitioners); geographic link s6(6); carve-outs (5C)/(5E); barrister-on-solicitor's-instructions exemption (6B)
- **Pt 1A** programs: **s26C** risk assessment (PF in scope), **s26D/26E** review/up-to-date-before-service, **s26F** policies, **s26G** comply, **s26H** governing body, **s26J-26M** compliance officer (designate <=28 days s26K; notify AUSTRAC <=14 days s26M; *there is no s26O*), **s26N/26P** document & approve, **s26Q/26R** AUSTRAC-CEO production/direction, **s26T** AFSL carve-out
- **Pt 2** CDD: **s28** initial CDD (7 matters), **s29** delayed verification, **s30** ongoing CDD, **s31** simplified, **s32** enhanced, **ss35A-35F** identity verification + retention, **ss37/37A/37B/38** reliance, **s39/39E** exemptions, **ss39A-39D** keep-open notices
- **Pt 3** reporting: **s41** SMR (deadlines s41(2)), **s43** TTR, **ss45/46/46A** IVTS/IFTI, **s47** annual compliance report, **s48A** amend/withdraw
- **Pt 3A** **s51B** enrol
- **Pt 10** records: **s107** transactions, **s108** customer-provided docs, **s111** CDD, **s114/114A** reliance, **s116** program (Pt 1A) records
- **Pt 11** **s123** tipping-off offence (exceptions s123(4) dissuasion, s123(5) info-sharing); **s242** legal professional privilege preserved

**Rules - AML/CTF Rules 2025** (F2026C00274): **s1-5** domestic PEP offices; **Pt 3** ss3-2...3-5 enrolment fields; **Pt 5** ss5-1...5-16 program/policy content (incl. **s5-5** SM approvals, **s5-7** CO->governing-body >=12-monthly, **s5-10** independent evaluation, **s5-11** report integrity, **s5-12** SMR assessment, **s5-13** tipping-off safeguards, **s5-14** fit-and-proper, **s5-15** 14-day documentation); **Pt 6** ss6-1...6-35 CDD (field schemas, BO, PEP, simplified/enhanced, ongoing); **Pt 8** ss8-3...8-5 travel rule; **Pt 9** ss9-2...9-13 report contents.

**Transitional Rules - AML/CTF Transitional Rules 2026** (F2026L00393): **ss7-8** ACIP relief (ends 31 Mar 2029); **ss16-17** first-evaluation deadlines; **s19** CO-notification (later of enrol+14 days or 29 Jul 2026).

*Confirm s41(2)(aa) (LPP 5-day) against the in-force Act before relying on it.*

---

*Source documents (all "Last updated" Mar 2026): Your AML/CTF program overview;
Step 1 Establish your governance framework; Step 2 Identify and assess your risks;
Step 3 Manage and mitigate your risks - AML/CTF policies; Step 4 Review and update
your AML/CTF program; Step 5 Conduct an independent evaluation; Record keeping;
Risk insights and indicators of suspicious activity for legal professionals.*
