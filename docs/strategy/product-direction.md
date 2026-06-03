# Product Direction - Risk-spine GRC, agentic delivery

> Purpose: a durable, actionable statement of what Onus is becoming and the staged path
> to get there. Captures the GRC-scope and agentic-AI direction so we build against an
> agreed plan rather than ad hoc. Companion to `docs/specs/risk-methodology.md`.

## 1. The frame

Onus is described as an "AI GRC officer" but today it is, narrowly, an **AML/CTF
compliance tool** - the C in GRC. The reframe:

- **Risk** is the spine - the things that can actually harm a small firm.
- **Compliance** is meeting external obligations. AML/CTF is one (new, mandatory,
  deadline-driven) compliance domain: the **wedge**.
- **Governance** is accountability + oversight. For a small firm it is a thin wrapper
  (roles, approvals, audit trail) that every domain shares.

Onus's real product: **a risk-and-compliance operating system for small Australian law
firms**, with AML as module #1.

## 2. Strategic thesis: wedge -> land -> expand

- **AML is the perfect wedge.** Mandatory, hard deadline (1 July 2026), every small firm
  must comply, and they do not know how. A rare forcing function for adoption.
- **AML alone is a "deadline tool"** - high churn risk once a firm is set up.
- **Risk is the expansion vector** that turns Onus into a standing backbone: stickier,
  higher value per customer, larger surface to automate.

So: ship AML (drives adoption), prove the spine, then extend into the risks that actually
keep principals up at night. Do **not** pivot away from AML - use it.

## 3. Domain expansion map (and order)

Risks that matter to a small AU firm, roughly by stakes:

1. **AML/CTF** - module #1 (the wedge). [in build]
2. **Trust account compliance** - recommended domain #2. Among the highest-stakes risks
   (trust breaches are a leading cause of solicitors being struck off), heavily regulated
   under the Legal Profession Uniform Law, and adjacent to AML.
3. **Cyber / data breach** - universal, rising; Privacy Act + Notifiable Data Breaches.
4. Then: **conflicts of interest**, **confidentiality/privilege**, **costs disclosure**,
   **PI / negligence exposure**, **practising certificate + CPD**, **supervision**.

Principle: do not ship six half-baked modules. Nail AML, then take trust account as #2 to
prove the spine generalizes, then widen. Each new domain is cheap once the spine + agents
exist.

## 4. The agentic model: propose / dispose

"Agentic" = the AI runs multi-step work toward a goal, with tools and checkpoints. The
non-negotiable rule (a product rule and a trust/liability necessity):

> **Agents propose, humans dispose.** Agents do the tedious, document-heavy 90% and
> *prepare* decisions. Humans approve anything consequential or regulated. Never
> auto-approve the program; never auto-lodge a report.

Every agent action is recorded (AgentTask + audit log) so the firm can always see "what
Onus did and why."

## 5. Agent catalogue (mapped to the spine)

| Agent | Job | Human gate |
|---|---|---|
| Risk-assessment | Draft the full assessment with rationale + citations from the firm profile (and its real matters); flag gaps | Senior manager approves the assessment |
| CDD / onboarding | For a new client/matter: gather requirements, screen sanctions/PEP, draft the CDD record, flag EDD triggers | Human verifies identity decisions |
| Monitoring | Watch conditions across all domains (sanctions/FATF/DFAT changes, EDD now required, overdue trust reconciliation, expiring practising certificate, data-breach indicator); raise prioritized, explained alerts with a recommended action | Human acts on alerts |
| Regulatory-change | Watch AUSTRAC / Law Society / OAIC; summarize relevance to this firm; draft register entry + the review it triggers | Human reviews relevance |
| Report-prep | Draft the SMR / breach notification with deadline + tipping-off logic | Human approves + lodges |
| Orchestrator ("standing GRC officer") | Plan the compliance calendar, delegate to the others, deliver a weekly "needs you / I did" digest | n/a (delegates only) |

Substrate already in place: AgentTask/audit trail, a human-approval gate, and a
provider-agnostic AI layer (`engine/ai/`).

## 6. The unifying insight

**The GRC expansion and the agentic expansion are the same build, staged.** Every agent
sits on a shared spine (the ISO-31000 risk model + the action/approval/audit machinery),
so it is reusable as domains are added. More domains = more for agents to do; better
agents = more leverage per domain. They compound.

## 7. Cautions / guardrails

- **Focus first.** AML must be rock-solid before chasing breadth. Breadth is the
  post-launch story.
- **Human gate on every regulated action.** Non-negotiable.
- **Mind the advice line.** Broadening toward "risk management" edges nearer professional
  judgment. Frame as decision-support/tooling, not advice; keep the "Not legal advice"
  posture.
- **Competition.** Practice-management incumbents (LEAP / Smokeball / Actionstep) could
  bolt on AML. Onus's edge is AI-native + agentic + AML-deep at the deadline. Win the
  wedge with depth, then expand before they do.
- **Privacy / residency.** Broader domains mean more sensitive data; the Australian
  hosting decision becomes more important, not less.

## 8. Staged roadmap

**Now (pre-launch, within AML):**
- Turn the existing assistive AI into 2-3 *real* agents within AML: risk-assessment
  drafting, CDD/onboarding, monitoring - each with a human-approval gate + audit trail.
- Success: a firm can go profile -> drafted assessment -> human approval, and Onus visibly
  "did the work" with citations and an audit trail.

**Post-launch:**
- Generalize the spine (ISO 31000) and the monitoring agent to **trust account** (domain
  #2). Activate the likelihood x impact tier (Method A) only with verified cells +
  per-factor capture.
- Success: a second domain reuses the spine with minimal new machinery.

**Later:**
- Add the orchestrator ("standing GRC officer") spanning domains; widen to cyber,
  conflicts, etc.
- Success: a weekly digest that plans + reports across multiple risk domains.

## 9. Immediate next step

Build the **risk-assessment drafting agent** first: most visible, builds directly on the
just-grounded risk methodology, and proves the agentic propose/dispose pattern. It sits on
`engine/ai/` (provider-agnostic) and writes a draft assessment + rationale for the senior
manager to review and approve - it never approves on its own.
