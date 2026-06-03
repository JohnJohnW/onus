# Spec - ML/TF Risk Methodology (authority, operative method, GRC option)

> Purpose: state exactly how Onus rates ML/TF risk, which authority each rule comes
> from, what is verified vs an Onus choice, and the option to extend this into a
> firm-wide GRC risk methodology. Written to anchor the GRC-scope decision.
>
> Verification note: the aggregation rule, the review cadence, the Basel band, and the
> country override below were read **first-hand** from the Law Society guide. The
> likelihood x impact matrix (section 4) could **not** be verified first-hand and is
> marked provisional.

## 1. Authority hierarchy (what governs an AML/CTF risk assessment)

For a regulated AML/CTF risk assessment the authority is AUSTRAC + FATF, in order:

1. **AML/CTF Act 2006, s26C / s26A** - mandates the assessment, the four factors, and
   proliferation financing (PF).
2. **AUSTRAC "Step 2: Identify and assess your risks"** - the regulator's own method.
3. **FATF risk-based-approach guidance for legal professionals** - the international
   standard AUSTRAC implements.
4. **Law Society of NSW, AML/CTF Implementation Guide for sole practitioners and small
   practices (April 2026)** - AUSTRAC-co-developed; the on-point operational kit for
   Onus's user. Annexure 4 states it is "completely drawn from the AUSTRAC Conveyancing
   and Starter Kits."

NIST and ISO are **not** AML authorities and never override the above. They contribute
methodological rigor only (sections 5-6).

## 2. AUSTRAC publishes two methods - Onus uses the one written for small practices

- **Method B - factor-counting (Starter Kit).** Rate each factor (designated service,
  customer type, delivery channel, country) by inherent risk Low/Medium/High; aggregate
  to an overall rating by counting; attach controls + review cadence to the rating tier.
  This is the method the Law Society guide reproduces. **Onus's operative method.**
- **Method A - likelihood x impact matrix.** A separate 3x3 (likelihood x impact ->
  L/M/H) AUSTRAC offers for "medium complexity" businesses, expressly an example you may
  expand. **Not operative in Onus** (sections 4, 7).

AUSTRAC requires the method be "tailored to the nature, size and complexity" of the
business and lets smaller businesses "assess their impact only." For a sole
practitioner / small firm, Method B (impact-based factor ratings + count aggregation) is
both compliant and the intended approach.

## 3. Onus's operative method (Method B) - rule by rule, with provenance

| Rule | What Onus does | Authority | Verified |
|---|---|---|---|
| Four factors | services, customer types, delivery channels, countries | Act s26C(3) | Yes (statute) |
| Factor rating | each selected item carries an inherent L/M/H rating + plain rationale | AUSTRAC Step 2; NRA vulnerability ratings | Yes |
| Property/conveyancing = High | "Property transactions" rated High | AUSTRAC 2024 ML NRA | Yes (Law Society Annexure 4 pp54-56) |
| Overall aggregation | High if any factor High; else Medium if 2+ factors Medium; else Low | Law Society Annexure 4 p53 (verbatim) | Yes (first-hand) |
| Review cadence | High yearly / Medium 2-yearly / Low 3-yearly | Law Society Annexure 4 p53 | Yes (first-hand) |
| Basel band | Basel AML Index < 5.00 = Low | Law Society p21 (verbatim) | Yes (first-hand) |
| Basel medium/high split | 5.01-6 = Medium, > 6 = High | none - **Onus banding choice** | No AUSTRAC boundary above 5.00 exists |
| Country automatic High | forced by FATF high-risk listing OR DFAT/UN sanctions | Law Society p21 (verbatim override) | Yes (first-hand) |
| Country enhanced triggers | prescribed-foreign-country / tax-haven / terrorism-support also force High | **Onus enhanced** (good practice, not mandated) | Labelled as such |
| Sanctions hit | "must not deal" prohibition - screen any connected party | sanctions law (absolute prohibition) | Yes |
| PF | four-criterion "low PF" screen; record PF as assessed even if low | Act s26C(1); AUSTRAC Step 2 PF guidance; s52 proportionality | Yes (statute) |

Honest caveats baked into the code/UI: the Basel medium/high split and the three
enhanced country triggers are Onus choices, labelled as such; the factor ratings are
Onus's default starting positions (editable), grounded in AUSTRAC's NRA where one exists.

## 4. Why the likelihood x impact matrix (Method A) is not shipped

It was built and unit-tested but never fed by any input (no per-factor likelihood/impact
capture), so it never affected a rating - dead code implying a capability Onus did not
have. Its exact cells and the "Step 2 p.28" citation could not be verified first-hand
(every AUSTRAC source timed out in research; the grid is search-index-only, and the
impact axis label is ambiguous - "Minor/Moderate/Major" vs "Low/Medium/High"). So it is
removed from the engine and specified here, to be activated deliberately (section 7) -
not shipped on faith.

Provisional Method A grid (CONFIRM on the live AUSTRAC Step 2 page before activating):

| Likelihood \ Impact | Minor | Moderate | Major |
|---|---|---|---|
| Very likely | Medium | High | High |
| Likely | Low | Medium | High |
| Not likely | Low | Low | Medium |

## 5. Methodological rigor: NIST SP 800-30 (for Method A, if activated)

NIST SP 800-30 is the canonical "risk = likelihood x impact" method: define explicit
qualitative scales with written descriptors and a documented matrix. It is an
information-security guide, **not** an AML authority - so it does not change any rating
in section 3; it lends discipline only **if** Method A is activated. If we do, each
likelihood and impact level gets a written, plain-English descriptor (NIST-style) so a
firm's choice is defensible and repeatable, and the matrix is documented with its
provenance. Output stays in AUSTRAC's L/M/H terms.

## 6. The GRC option: ISO 31000 as the backbone

ISO 31000 (with ISO 31010 techniques) is the international enterprise-risk standard: the
assess -> evaluate -> treat -> monitor -> review process and the consequence/likelihood
matrix technique. It is the natural backbone **if** Onus broadens from AML-only
compliance to firm-wide GRC (conflicts, trust-account, cyber, practising certificates,
...), with the AML assessment as one ISO-31000-shaped domain among several. Adopting its
process vocabulary is a down-payment on that reframe. For AML alone it is not required -
AUSTRAC + the Law Society kit suffice.

## 7. The decision this spec anchors

Two linked choices:

1. **Stay AML-focused (current).** Keep Method B as in section 3; the matrix stays an
   optional, documented future tier. No further work needed for AML correctness.
2. **Expand to full GRC.** Adopt ISO 31000 as the firm-wide risk backbone; activate
   Method A for medium-complexity firms with NIST-style scales + per-factor
   likelihood/impact capture; the AML assessment becomes one domain. This is the "make
   Onus real GRC" reframe - larger scope, decided deliberately.

Recommendation: do AML correctness now (done - see the risk engine), and treat Method A
activation + ISO 31000 adoption as part of the GRC decision, not a quiet add-on.

## Sources

- AML/CTF Act 2006, s26C / s26A.
- AUSTRAC, Step 2: Identify and assess your risks (general + Reform).
- FATF, RBA Guidance for Legal Professionals.
- Law Society of NSW, AML/CTF Implementation Guide for sole practitioners and small
  practices (April 2026): Annexure 4 p53 (aggregation + cadence), pp20-21 (Basel +
  country override), pp54-56 (NRA ratings).
- NIST SP 800-30 Rev.1, Guide for Conducting Risk Assessments.
- ISO 31000:2018 (risk management) + ISO 31010 (risk assessment techniques).
