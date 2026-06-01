# Spec - Clients & Matters / CDD (AUSTRAC Step 3 + Risk insights)

> **Status:** not built (placeholder). **Now grounded in primary law** - refer-outs
> R1-R5 and R9 are resolved. Sources: Act *AML/CTF Act 2006* (C2026C00119, Comp 60);
> Rules *AML/CTF Rules 2025* (F2026C00274, Comp 1); Transitional Rules (F2026L00393);
> AUSTRAC "Overview of initial CDD", "Assigning customer risk ratings", "High-risk
> countries", "Risk insights for legal professionals".

For each **client** and **matter**: run **customer due diligence (CDD)** before
acting, screen for PEP/sanctions, capture beneficial ownership and source of funds
where triggered, monitor for suspicious activity, and keep the record. CDD risk
ratings flow from the Risk Profile.

## 1. AUSTRAC / statutory basis

The seven matters every initial CDD must establish **on reasonable grounds before
commencing the service** (**Act s28(1),(2)**):
(a) the customer's identity; (b) any person **on whose behalf** the service is
received; (c) any person **acting on behalf** of the customer **and their
authority**; (d) **beneficial owners** (if customer is not an individual);
(e) whether the customer / BO / (b) / (c) is a **PEP** or **designated for targeted
financial sanctions**; (f) the **nature and purpose** of the relationship;
(g) any matter in the Rules. To establish them the entity must **identify the
customer's ML/TF risk, collect KYC appropriate to that risk, and verify** KYC using
reliable & independent data (**s28(3)**) - verifying **at least one item per matter**
(Initial-CDD p.13). Ongoing CDD: **Act s30**. Simplified: **s31**. Enhanced: **s32**.

## 2. User stories

- As a **fee-earner**, before I open a matter I complete a guided CDD check; I can't
  provide the designated service until it passes (s28(1)).
- As a **compliance officer**, I see each client's risk rating, PEP/sanctions status,
  beneficial owners, source of funds/wealth, and any open red-flag alerts.
- As **Onus**, I screen every client + associated person, score risk, and raise an
  alert (and a draft SMR) when indicators fire - **without tipping off** the client.

## 3. Designated-services catalogue (R1 - Act s6, in force in Comp 60)

A law firm has obligations only when it provides a **designated service**. Seed
`matter.designated_service_key` from Act s6 **Table 5** (real estate) and **Table 6**
(professional services). Each carries its **"customer"** (drives who CDD is run on):

| Key | Designated service (condensed) | Customer |
|---|---|---|
| `T5_1` | **Brokering** sale/purchase/transfer of real estate | both seller/transferor **and** buyer/transferee |
| `T5_2` | Selling/transferring real estate not brokered by an independent agent | buyer/transferee |
| `T6_1` | Assisting/acting in a transaction to **buy/sell/transfer real estate** (not court-ordered) | the person |
| `T6_2` | Assisting/acting in a transaction to **buy/sell/transfer a body corporate or legal arrangement** | the person |
| `T6_3` | **Receiving, holding, controlling or managing** a person's money/accounts/securities/virtual assets/other property as part of assisting a transaction | the person |
| `T6_4` | Assisting/acting in **equity or debt financing** of a body corporate or legal arrangement | the person |
| `T6_5` | **Selling/transferring a shelf company** | buyer/transferee |
| `T6_6` | Assisting/acting in **creating or restructuring** a body corporate or legal arrangement | the person **+** (company -> its beneficial owners & directors; express trust -> trustee, settlor, beneficiaries) |
| `T6_7` | **Acting as / arranging** a nominee **director, secretary, power of attorney, partner, or trustee** | the nominator |
| `T6_8` | **Acting as / arranging a nominee shareholder** | the nominator |
| `T6_9` | Providing a **registered office / principal place of business address** | the person served |

**Scope flags to encode:**
- **Barrister exemption (s6(6B)):** a service provided by a barrister **on a
  solicitor's instructions** (given in connection with a designated service) is **not**
  a designated service.
- **T6-3 carve-outs (s6(5C)):** payment for the firm's own goods/services; payments
  reasonably incidental to a non-designated service; property under a **court/tribunal
  order**; payments under s6(5D) (gov body / court / insurer / public international org).
- **T6-7 carve-outs (s6(5E)):** acting under a court/tribunal order; bankruptcy trustee.
- **Geographic link (s6(6)):** applies only at/through an **Australian permanent
  establishment** (or AU-resident / AU-subsidiary at a foreign establishment).

> The reform's *substantive obligations* for law firms switch on **1 July 2026**
> (Transitional Rules s15 maps these to item-54 treatment until 30 Jun 2026); the
> service **definitions** are already in force (Comp 60, Endnote 4).

## 4. KYC field schema per customer type (R2 - Rules Pt 6 Div 1)

`cdd_check.kyc_fields` JSON shape, keyed by `client.type`. "Collect" = the field
list; "Verify" = at least one item per s28(2) matter, risk-based (s28(3)(d)).

- **`individual`** - name, DOB, residential address, other names; occupation +
  citizenship(s) when risk/requests are unusual. Verify name+address+DOB via the
  credit-reporting-body / electronic / document path (**Act ss35A-35B**). *(The Rules
  give no explicit field list for a plain individual; this is the s28(3)(a) + s35A
  anchor trio.)*
- **`sole_trader`** (**Rules s6-1**) - full name, business name, other names, unique
  identifier, principal place of business, nature of business.
- **`company_domestic` / `company_foreign` / `partnership` / `partnership_limited` /
  `incorporated_association` / `unincorporated_association` / `cooperative`**
  (**Rules s6-2** - one schema) - full name, business names, other names, unique
  identifier (ACN/ABN/ARBN/ARSN/LEI), principal place of business, registered office,
  evidence of existence, governing document, **governing individuals** (+ director ID),
  **ownership & control structure (-> beneficial owners)**, nature of business.
- **`trust_*`** (discretionary/unit/hybrid/bare/testamentary/charitable + foreign
  equivalents) (**Rules s6-3**) - name, kind of trust, business/other names, unique
  identifier, principal place of business, evidence of existence, governing document,
  governing individuals, **beneficiaries (each, or by class)**, **trustees**, **control
  structure**, **settlor/appointor/guardian/protector**, nature of business.
- **`government_body`** (**Rules s6-4**) - name, other names, country established,
  unique identifier, principal place of business, evidence of existence, governing
  individuals, nature of business. *(BO deemed established - Rules s6-7(1A).)*
- **Non-individual associated parties** (a (b) or (c) person that isn't an
  individual): collect its identity fields as if it were a customer (**Rules s6-5**).

## 5. Beneficial ownership (R5), PEPs (R4), CDD tiers (R3)

**Beneficial owner** = an **individual** who directly/indirectly **owns >= 25%** OR
**otherwise controls** the customer (Initial-CDD p.9). Look through intermediate
entities to the ultimate individual(s). Capture per `client_party` (below).
- **Deemed established (no individual BO needed):** listed public company / its
  controlled entities (Rules s6-7(1),(1B)); government body (s6-7(1A)); simplified-CDD
  prudentially-regulated or strata-title customers (s6-18).
- **Fallback (Rules s6-8):** all-reasonable-steps fail -> record the steps + collect &
  verify the **CEO (or equivalent)**; if there are **no** BOs -> the CEO-equivalent is
  the specified matter.

**PEP** test runs over the **whole subject set** (customer + BOs + on-whose-behalf +
acting-on-behalf - s28(2)(e)):
- **Domestic PEP** offices enumerated in **Rules s1-5** (G-G, governors, **judges of
  High/Federal/State Supreme courts**, agency heads, local-council heads, defence
  chiefs, heads of diplomatic posts, governing members of parliamentary parties, ...).
  **Foreign** & **international-organisation** PEPs per Act s5. Family members / close
  associates count.
- **Foreign PEP -> always high risk -> enhanced CDD mandatory** (Act s32(c)) +
  **source of wealth AND source of funds** (Rules s6-23). Domestic / intl-org PEP ->
  SoW/SoF only **where risk is high** (Rules s6-23). Senior-manager approval for
  PEP relationships lives in the **program policies** (Rules s5-5) - see
  [compliance-program.md](compliance-program.md), not a Part-6 CDD field.

**CDD level decision (`cdd_check.level`):**
```
ENHANCED (Act s32) - MANDATORY if ANY:
  risk == high                                   # s32(a)
  | SMR obligation arisen & relationship continuing  # s32(b)
  | any subject is a FOREIGN PEP                  # s32(c)
  | any subject present-in/formed-in a FATF "called-for-EDD" jurisdiction  # s32(d)
  | nested-services relationship                 # s32(e)
  | kind specified in Rules 6-20/6-22 (no economic purpose; unusually complex/large;
    unusual pattern; physical-currency for virtual-asset services)        # s32(f)
  -> establish source of wealth + source of funds (Rules s6-21); record edd_reason

SIMPLIFIED (Act s31) - PERMITTED (never mandatory) only if:
  risk == low  &  not enhanced  &  policies cover simplified  (Rules 6-16..6-19)
  -> still collect all required KYC; Rules deem matters established

STANDARD (Act s28) - otherwise
```

## 6. Ongoing CDD, timing & transitional relief

- **Ongoing CDD (Act s30):** monitor for **unusual transactions/behaviours** (s30(5):
  unusually large/complex, unusual pattern, no apparent economic/lawful purpose,
  inconsistent with what's known) against the **27 offence categories in Rules s6-35**;
  re-assess risk on a **significant change** (s30(2)(b)); **re-verify** KYC at a
  frequency appropriate to risk (s30(2)(c)). Explicit cadences: **nested-services ->
  re-verify every 2 years** (Rules s6-26); **PEP-status change -> immediate** (s6-24);
  **doubt about KYC -> immediate**.
- **Timing (Act s28(1)):** initial CDD complete **before** providing the service.
  **Delayed-verification branch (Act s29):** may start first only if Rules
  circumstances apply, it's essential to avoid interrupting ordinary business,
  residual risk is **low**, and policies require completion ASAP. Sets
  `cdd_gate_passed` provisionally + a mandatory "complete ASAP" task.
- **Transitional ACIP relief (Transitional Rules ss7-8):** until **31 Mar 2029**, a
  firm may keep using its 30-Mar-2026-compliant **applicable customer identification
  procedures** for **nominated customer classes** instead of new initial CDD -   provided that **by 1 July 2026** its policies list those classes + a stop-date per
  class. **Ongoing CDD applies from 31 Mar 2026 regardless.** Each class sits under
  ACIP **or** initial CDD, never both.

## 7. Suspicious-activity indicators (Risk insights)

Seed `monitoring_alert.indicator_key` across the 9 groups (Risk insights section 4) - signals,
not auto-triggers ("on their own ... may not suggest suspicious activity", p.6).
High-value for law firms: **trust-account layering** (p.12); **back-to-back property
deals** with rising values (p.11); **wholesale company/trust creation**,
**shelf/shell/aged-company** purchases (pp.11-12); **source-of-funds/wealth
inconsistencies** (pp.10-11); **nominee** arrangements (p.10); **foreign-jurisdiction**
transfers with no connection (pp.13-14). Lists are explicitly non-exhaustive - firms
can add their own.

## 8. Data model

```
client
  id, firm_id, type enum(individual|sole_trader|company_domestic|company_foreign|
    partnership|partnership_limited|trust_discretionary|trust_unit|trust_hybrid|
    trust_bare|trust_testamentary|trust_charitable|incorporated_association|
    unincorporated_association|cooperative|government_body),
  display_name, status,
  risk_rating enum('low','medium','high') null,
  cdd_status enum('not_started','in_progress','complete','blocked'),
  is_pep bool, pep_kind enum('foreign','domestic','intl_org') null,
  sanctions_hit bool, adverse_media_hit bool,
  source_of_funds text null, source_of_wealth text null,
  created_at, updated_at

client_party                 # BOs / controllers / agents / trust roles (s28(2)(b)-(d))
  id, firm_id, client_id,
  role enum('beneficial_owner','controller','agent','director','nominee','trustee',
    'beneficiary','settlor','appointor','guardian','protector','ceo_equivalent'),
  bo_basis enum('ownership_25pct','control','both','none','deemed_listed_co',
    'deemed_govt','deemed_controlled','ceo_fallback') null,
  ownership_pct numeric null, is_individual bool, details jsonb,   # section 4 schema if non-individual
  is_pep bool, pep_kind, sanctions_hit bool, verified bool,
  verification_method enum('document','electronic','credit_reporting_body_match') null,
  steps_recorded text null     # s6-8(1)(c) all-reasonable-steps log

matter
  id, firm_id, client_id, designated_service_key,   # section 3 catalogue
  description, status, opened_at, closed_at,
  cdd_gate_passed bool, cdd_gate_basis enum('initial_cdd','delayed_s29','acip_transitional'),
  risk_rating, created_at

cdd_check
  id, firm_id, client_id, matter_id null,
  level enum('simplified','standard','enhanced'),
  kyc_fields jsonb,            # section 4 per-type schema
  edd_reason text null,        # which s32 limb fired
  outcome enum('pass','fail','pending'), verified_at, verified_by_user_id, created_at

screening_result
  id, firm_id, subject_type enum('client','client_party'), subject_id,
  provider, list_type enum('sanctions','pep','adverse_media'),
  matched bool, match_details jsonb, screened_at, cleared_by_user_id null

monitoring_alert
  id, firm_id, client_id, matter_id null, indicator_key, indicator_group,
  severity, narrative,
  status enum('open','reviewing','escalated_to_smr','dismissed'),
  decision_log_id null, created_at

cdd_decision_log             # "reasonable grounds" reasoning (Risk insights p.6)
  id, firm_id, client_id, matter_id, decision_type, reasoning text,
  edd_applied bool, decided_by_user_id, decided_at
```

Verification records & CDD records are retained **7 years after the relationship ends**
(Act s111; ss35E/35F) - see [reporting-and-recordkeeping.md](reporting-and-recordkeeping.md) section 5.

## 9. API - UI - Onus role

- **API:** `POST/GET /clients`, `/clients/{id}/parties`, `/matters`, `/clients/{id}/cdd`,
  `/clients/{id}/screen`, `/clients/{id}/alerts`, `/alerts/{id}/decision`. `cdd_gate_passed`
  computed. All writes -> `AuditLog`.
- **UI `/clients`:** client list (risk rating, CDD status, open-alert count); client
  detail (KYC, beneficial-ownership tree, screening, SoF/SoW, matters, alerts); matter
  intake wizard with the **CDD gate**; alerts inbox grouped by the 9 indicator groups;
  **tipping-off guardrail** suppresses all client-facing notification for alerts/SMRs.
- **Onus:** drives the CDD wizard, builds the BO graph, screens on create + schedule
  (**foreign PEP -> auto High**), monitors against the indicator catalogue, drafts alert
  narratives and **draft SMRs** for human review. Never tips off; never auto-lodges.

## 10. Compliance gates & automations

- **Hard gate:** `matter.cdd_gate_passed` true before a designated service is provided
  (s28(1)) - unless the s29 delayed-verification or ACIP-transitional path is recorded.
- **Mandatory EDD** auto-set for any s32 trigger (foreign PEP, high risk, FATF
  called-for-EDD country connection, nested services, SMR-arisen).
- **Sanctions hit = absolute block** (must not deal) - sits above the risk score.
- **Re-screening / re-verification** on schedule and trigger (new party, risk change,
  PEP-status change, nested 2-year).
- New client type / country not in the Risk Profile -> **significant-change trigger** to
  Compliance Program (Step 4).
- Every CDD decision, screening result, alert disposition -> `AuditLog`.

## 11. Tipping-off (R9 - Act s123)

Disclosing that an SMR was/will be made, the suspicion's existence, or the SMR's
contents to anyone other than AUSTRAC is an **offence (s123; 2 yrs / 120 penalty
units)**. Product invariant: **no client-facing surface** (notification, status,
matter timeline, export, termination reason) may reveal an alert/SMR. **Exceptions a
law firm may use, narrowly and logged:** good-faith **dissuasion** of a client from
committing an offence (**s123(4)** - expressly available to legal practitioners);
sharing with another reporting entity to detect/deter/disrupt crime where regs are met
(s123(5)). **Legal professional privilege is preserved (s242)** and handled as an
`lpp_claimed` flag on the SMR - see reporting spec section 5; it does not weaken s123.

## 12. Refer-outs - resolved

| Ref | Status |
|---|---|
| R1 designated services | Act s6 Tables 5 & 6 (section 3) - in force in Comp 60 |
| R2 KYC field schema | Rules ss6-1...6-5 (section 4) |
| R3 simplified/standard/enhanced | Act ss28/31/32; Rules 6-16...6-22 (section 5) |
| R4 PEP | Rules s1-5, 6-23/6-24; Act s32(c) (section 5) |
| R5 beneficial ownership | 25% or control; Rules 6-7/6-8 (section 5) |
| R9 tipping-off + LPP | Act ss123, 242 (section 11) |

**Residual (not blocking):** a **screening data provider** (sanctions/PEP/adverse-media - e.g. OpenSanctions) - integration/licensing; the plain-**individual** minimum field set
is anchored on s28(3)(a)+s35A (Rules give no explicit list); optional Law Council
guidance refines the LPP/dissuasion UX.
