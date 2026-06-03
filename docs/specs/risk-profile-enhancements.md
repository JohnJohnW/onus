# Spec - Risk Profile Enhancements (AUSTRAC Step 2)

> **Status:** the Risk Profile is **built** (services / customer types / delivery
> channels / countries, inherent ratings, approval flow). This spec lists the
> **gaps** between what's shipped and what Step 2 actually requires, so the risk
> assessment is defensible. **Grounded in:** *Step 2 - Identify and assess your
> risks* (35 pp).

## 1. AUSTRAC basis

- "You **must conduct a risk assessment** to identify and assess your business's
  money laundering, terrorism financing and proliferation financing risks"
  (Step 2 p.3; Act s 26C).
- "You **must tailor your risk assessment methodology to the nature, size and
  complexity of your business**" (p.3).
- Four mandatory risk categories you "must consider": **designated services,
  customers, delivery channels, countries** (p.4).
- The assessment "**must be clearly documented**" with a rationale per rating
  "based on the data sources consulted" (p.25, p.30).

## 2. Gap analysis (built vs required)

| # | Requirement (Step 2) | Built? | Gap to close |
|---|---|---|---|
| G1 | Four risk categories with inherent rating + explanation | Yes | - |
| G2 | **Country risk** done properly: list every country **incl. Australia**; band via Basel AML Index (< 5.00 = Low); **force High** on AUSTRAC's **two mandated** triggers (FATF high-risk listing, DFAT/UN sanctions) plus **three Onus-enhanced** triggers (prescribed foreign country, tax haven, terrorism support) | Done | Basel score + override flags + auto-band |
| G3 | **Proliferation financing** assessed explicitly; 4-criterion "low PF" check; record that PF was assessed even if low (p.24-25) | No | Add PF assessment sub-flow |
| G4 | **Methodology scales with complexity**: likelihood x impact (3x3 matrix) for medium complexity; **impact-only** for small/low-complexity (p.26-29) | Single implicit rule | Add methodology mode + matrix engine |
| G5 | **Rationale per rating tied to a data source** (national risk assessments, typologies, lawyer/conveyancer quick guides, internal input) (p.30) | Note: Free-text explanation only | Require a `data_source` reference per rating |
| G6 | **AUSTRAC communications register** - log each AUSTRAC communication, why relevant, what changed, dates, reviewer (p.22-23) | No | New table + "consider -> trigger review" |
| G7 | **Planned** services/customers/channels/countries that could raise risk (p.4) | No | `is_planned` flag on factor rows |
| G8 | Higher-risk **customer factor flags** (PEP, non-resident, complex structure, third-party, unexplained wealth, criminal history) feeding per-customer risk (p.12-15) | Only customer *types* | Seed factor catalogue; reused by Clients & Matters |
| G9 | Document audience: usable by governing body, senior managers, compliance officer, relevant staff (p.5) | Note: Single view | Exportable assessment document |

## 3. Data model changes

Extend the existing `risk_assessments` and child tables:

```
risk_assessments
  + methodology        enum('impact_only','likelihood_x_impact')   # G4
  + complexity_tier    enum('low','medium','high')                 # G4
  + pf_assessed        bool default false                          # G3
  + pf_risk_rating     enum('low','medium','high') null            # G3
  + pf_rationale       text null                                   # G3

risk_assessment_services / _customer_types / _delivery_channels    # G4, G5, G7
  + likelihood         enum('not_likely','likely','very_likely') null
  + impact             enum('low','medium','high') null
  + data_source        text null     # e.g. "ML NRA 2024", "lawyers quick guide"
  + is_planned         bool default false

risk_assessment_countries                                          # G2
  + basel_score                numeric(4,2) null  # Basel AML Index (Step 2 banding)
  + fatf_listed                bool default false # FATF high-risk / "called for enhanced CDD"
  + sanctions_listed           bool default false # DFAT Consolidated List / UNSC
  + prescribed_foreign_country bool default false # Prescribed Foreign Countries Regs 2018: Iran, DPRK
  + tax_haven                  bool default false
  + terrorism_support          bool default false # Australian National Security listed terrorist org link
  # inherent_risk_rating = High if ANY override flag, else band from basel_score
```

New tables:

```
austrac_communications        # G6  (the communications register)
  id, firm_id, source_label, communicated_on (date),
  relevance_note, change_made, considered_on (date),
  reviewer_user_id, created_an, review_trigger_id (nullable FK)

customer_risk_factors         # G8  (catalogue, firm-scoped overrides allowed)
  id, firm_id (null = global seed), key, label, default_weight, active
  # seed: pep_foreign, pep_domestic, pep_intl_org, non_resident,
  #       complex_structure, third_party_agent, unexplained_wealth,
  #       criminal_history, high_net_worth
```

## 4. Scoring engine

- **Methodology** follows AUSTRAC's factor-counting "Starter Kit" method (see
  `risk-methodology.md`): each factor is rated L/M/H by inherent risk and the overall
  rating is aggregated by count (below). The likelihood x impact **matrix is a separate,
  optional AUSTRAC method** for medium-complexity firms; it is **not shipped** (its cells
  could not be verified first-hand and nothing fed it) and is specified as Method A in
  `risk-methodology.md`, to be activated with per-factor likelihood/impact capture.
- `impact_only` mode: inherent rating = the factor's inherent band.
- **Country override**: `inherent = High` if ANY of `fatf_listed`, `sanctions_listed`, `prescribed_foreign_country`, `tax_haven`, `terrorism_support`; else band from `basel_score`. Always include Australia. AUSTRAC mandates automatic-High on **two** triggers - a FATF high-risk listing or a DFAT/UN sanctions listing (Law Society p21) - and a sanctions hit is an absolute "must not deal" prohibition above the rating. The other three are **Onus enhanced** factors (good practice, not mandated), labelled as such. Basel `< 5.00 = Low` is verbatim (Law Society p21); there is **no** published medium/high Basel boundary, so the 5-6 / > 6 split is an Onus choice.
- **Mandatory enhanced CDD (not just a rating):** where a customer, beneficial owner, person on whose behalf, agent, or body corporate is **present in or formed in a jurisdiction FATF has called to apply enhanced CDD**, EDD is mandatory under Act s32(d) -> drives `cdd_check.level='enhanced'` in Clients & Matters. A **sanctions hit is an absolute prohibition** (must not deal) sitting above the score - route to screening, not the rating.
- **Overall rating**: AUSTRAC / Law Society combined method - High if any factor is
  High; else Medium if two or more factors are Medium; else Low (Law Society Annexure 4
  p53). Replaced the earlier "highest factor wins", which over-rated.
- **PF sub-flow**: 4 yes/no questions (Australia-only ops; no high-risk-jurisdiction
  customers; no movement of money/sensitive/dual-use goods; no PF-relevant service).
  All "yes" + low -> store `pf_risk_rating='low'`, surface "no separate PF policies
  required" with rationale (p.24-25).

## 5. API (engine)

- Extend `POST /risk-assessment/services|customer-types|delivery-channels` to accept
  `likelihood`, `impact`, `data_source`, `is_planned`.
- `PUT /risk-assessment/countries` - country rows with `basel_score`, `fatf_listed`,
  `sanctions_listed`; engine computes the rating.
- `POST /risk-assessment/pf` - PF 4-question payload -> rating + rationale.
- `GET/POST /risk-assessment/communications` - the register (also creates a
  `ReviewTrigger` when a new entry is logged).
- `GET /risk-assessment/current` - extend serializer with the new fields.
- `GET /risk-assessment/export` - generate the assessment document (see section 6).

## 6. UI (web)

- Risk Profile page: add a **Country risk** editor (score + two override toggles,
  showing the computed band), a **PF assessment** card (4 toggles + result), and
  per-factor **likelihood/impact** selectors when methodology is
  `likelihood_x_impact`.
- **Methodology** chosen from firm size at onboarding (sole practitioner ->
  `impact_only`; up to ~20 staff -> `likelihood_x_impact`), editable in the profile.
- **AUSTRAC communications register** tab: table with the six columns (p.22-23) +
  "Log communication" -> opens a review.
- **Export**: "Download risk assessment" -> a document written for the four
  audiences, with per-rating rationale + data source + AUSTRAC citations + the
  disclaimer.

## 7. Onus (AI) role

- Pre-fill inherent ratings and **draft the rationale** for each factor from
  AUSTRAC's "why it's risky" text + the lawyers/conveyancers quick guides.
- Watch FATF and DFAT sanctions lists; when a listed country matches a country in
  the register, **auto-raise a `ReviewTrigger`** (Step 4 out-of-control trigger).
- Summarise new AUSTRAC communications into a register entry draft.

## 8. Compliance gates & automations

- Block "complete/approve" until every factor has a rating **and** a rationale with
  a data source (p.30).
- Logging an AUSTRAC communication or a sanctions-list change -> `ReviewTrigger`
  (feeds Step 4).
- On approval, set `next_review_due_at` at a cadence that depends on the overall rating
  (High yearly / Medium 2-yearly / Low 3-yearly; Law Society Annexure 4 p53) and schedule
  the next review deadline; keep the version history.

## 9. Acceptance criteria

- [ ] A medium-complexity firm can rate each factor by likelihood x impact and the
      overall rating follows the p.28 matrix exactly.
- [ ] A sole practitioner sees impact-only rating.
- [ ] Adding a FATF/sanctioned country forces a High rating regardless of Basel score.
- [ ] PF is recorded as assessed (low/med/high) with rationale on every assessment.
- [ ] Every rating has a data-source reference; export produces a cited document.
- [ ] Logging an AUSTRAC communication creates a review trigger.

## 10. Refer-outs

- **R1** designated-services list for lawyers (service catalogue seed).
- Country-risk data feeds to integrate + refresh: **FATF** statements (high-risk / called-for-EDD jurisdictions); **DFAT Consolidated List** (sanctions); **AML/CTF (Prescribed Foreign Countries) Regulations 2018** (Iran, DPRK); **Australian National Security** listed terrorist organisations; plus the Basel AML Index (Step 2 banding) - licensing + refresh cadence TBD.

> **Statutory grounding confirmed:** the four risk categories are mandated by **Act s26C(3)** (services, customers, delivery channels, countries), and **PF must be assessed** per **s26C(1)** (G3). The Rules add *no* extra mandatory content fields to the assessment, so the enhancements here (Basel scoring, likelihoodximpact matrix, data-source-per-rating) are **defensibility/good-practice, not Rules-mandated** - keep them, but don't label them as legal requirements. s26C(3)(a)/(c) explicitly require regard to **new or emerging technologies** in services and delivery channels - add that prompt (relates to G4/G7).
