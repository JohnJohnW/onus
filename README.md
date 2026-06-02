# Onus

**An AI GRC officer for AML/CTF compliance - built for small Australian law firms
under the Tranche 2 reforms.**

From **1 July 2026**, the *Anti-Money Laundering and Counter-Terrorism Financing Act
2006* extends to legal practitioners. Onus turns those obligations into a working
system: it builds and maintains the firm's **AML/CTF program**, runs **customer due
diligence** before the firm acts, **monitors** for suspicious activity, drafts the
**reports** AUSTRAC requires, schedules the **independent evaluation**, and keeps
**audit-ready records** - with an AI that drafts the paperwork and a human who
approves it.

> Onus is software, not legal advice. Generated content is a starting point for a
> qualified person to review. See the per-section specs in [`docs/specs/`](docs/specs/README.md).

---

## System architecture

```mermaid
flowchart LR
  User(["Firm staff"]) -->|HTTPS| Web["web - Next.js App Router<br/>operator UI - :3000"]
  Web -->|REST + JWT via server proxies| Engine["engine - FastAPI<br/>compliance API - :8000"]
  Engine -->|SQLAlchemy + Alembic| DB[("db - PostgreSQL 15<br/>+ pgvector - :5432")]
  Engine -->|provider-agnostic| AI["AI provider<br/>Anthropic - OpenAI - Azure"]
  Engine -. firm-scoped RLS .-> DB
```

Three services, orchestrated locally with Docker Compose. The web tier renders
server components and calls the engine through **server-side proxies**, so the JWT
never reaches the browser. Every table is **firm-scoped** behind a row-level-security
GUC. AI is reached through a **provider-agnostic interface** (swap providers via env).

---

## The AML/CTF program model

Onus mirrors AUSTRAC's reformed structure: a program is a **ML/TF risk assessment**
plus **AML/CTF policies**, owned by a governance framework, and kept current through
review, evaluation, reporting and record-keeping.

```mermaid
flowchart TD
  GB["Governing body (oversight)"] --> PROG
  SM["Senior manager (approves - s26P)"] --> PROG
  CO["AML/CTF compliance officer"] --> PROG

  subgraph PROG["AML/CTF program - Act Pt 1A"]
    RA["ML/TF risk assessment<br/>-> Risk Profile"]
    POL["AML/CTF policies<br/>-> Compliance Program"]
    RA --> POL
  end

  POL --> CDD["Customer due diligence<br/>-> Clients &amp; Matters"]
  CDD --> MON["Suspicious-activity monitoring<br/>alert -> SMR"]
  MON --> REP["Reporting<br/>SMR - TTR - IVTS - annual"]
  PROG --> REV["Review &amp; update<br/>>= every 3 yrs + triggers"]
  PROG --> EVAL["Independent evaluation<br/>>= every 3 yrs -> Evaluation"]
  CDD --> REC["Records - 7-year retention"]
  REP --> REC
  EVAL -->|adverse finding| REV
```

---

## The per-matter workflow (CDD -> monitoring -> SMR)

```mermaid
flowchart TD
  A["New client"] --> B["Initial CDD<br/>collect + verify KYC,<br/>identify beneficial owners,<br/>screen PEP / sanctions"]
  B --> C{"Assess"}
  C -->|sanctions hit| X["Blocked - must not<br/>provide the service"]
  C -->|foreign PEP / high risk| E["Enhanced CDD"]
  C -->|low risk| S["Simplified CDD"]
  C -->|otherwise| D["Standard CDD"]
  E --> G
  S --> G
  D --> G
  G{"CDD gate<br/>passed?"} -->|yes| M["Open matter -<br/>provide designated service"]
  M --> MON["Ongoing monitoring"]
  MON --> AL{"Suspicious<br/>indicator?"}
  AL -->|reasonable grounds| SMR["Escalate -> draft SMR -> lodge<br/>(never tip off the client)"]
  AL -->|no| MON
```

---

## Features (mapped to AUSTRAC's guidance)

| Section | What it does | AUSTRAC basis |
|---|---|---|
| **Dashboard** | The principal's daily agent feed: actions required, activity, deadlines | - |
| **Risk Profile** | ML/TF/PF risk assessment - 4 categories, likelihoodximpact matrix, country-risk engine, PF screen, AUSTRAC-communications register | Step 2 - Act s26C |
| **Compliance Program** | The policy set + obligation coverage + document-and-approve (senior-manager sign-off) + review lifecycle | Steps 1, 3, 4 - Act ss26F-26P |
| **Clients & Matters** | Per-customer-type KYC, beneficial owners, the CDD-tier engine, the before-you-act gate, monitoring + alert->SMR | Step 3 - Act Pt 2; Risk insights |
| **Reporting** | SMR / TTR / annual compliance report (with the IVTS and cross-border reports gated as non-routine) - real deadlines, tipping-off guardrails, 4-regime record retention | Act Pt 3, Pt 10 |
| **Evaluation** | Independent evaluation - staggered deadline, independence gate, findings & remediation | Step 5 - Transitional Rules s17 |
| **Audit Trail / Settings** | Immutable action log; firm details, users, governance roles | Act s116 |

Cross-cutting: an **AI drafting layer** ("Draft with Onus" for policies and SMR
narratives, human-in-the-loop) and an **onboarding wizard** that builds the firm's
first risk assessment.

---

## Tech stack

| Service | Stack |
|---|---|
| `web` | Next.js 14 (App Router) - TypeScript - Tailwind - next-auth - shadcn/ui |
| `engine` | FastAPI - Python 3.11 - SQLAlchemy 2 - Pydantic v2 - Alembic - python-jose - bcrypt |
| `db` | PostgreSQL 15 + pgvector |
| AI | Provider-agnostic (`engine/ai/`) - Anthropic / OpenAI / Azure OpenAI, + a mock for tests |

## Repository layout

```
onus/
|-- web/                  # Next.js operator UI
|-- engine/               # FastAPI compliance API
|   |-- models.py         # SQLAlchemy models
|   |-- routers/          # auth, risk_assessment, program, clients, alerts, reports, evaluations, ...
|   |-- ai/               # provider-agnostic AI + drafting
|   |-- alembic/          # versioned migrations
|   +-- tests/            # pytest (unit; pure functions)
|-- docs/
|   |-- architecture/     # system overview
|   |-- data-model/       # entities & schema notes
|   +-- specs/            # per-section specs, grounded in the Act/Rules with citations
|-- infrastructure/docker/
|-- .github/workflows/    # CI (tsc + lint + pytest)
+-- docker-compose.yml
```

## Local development

```bash
cp .env.local.example .env.local     # fill in secrets (NEXTAUTH_SECRET, AI key, ...)
docker compose up                    # web :3000 - engine :8000 - db :5432
```

Source for `web` and `engine` is bind-mounted (hot reload). The engine runs
`alembic upgrade head` on start. Inside the Compose network the DB host is `db`.

```bash
# migrations
cd engine && alembic revision --autogenerate -m "describe change" && alembic upgrade head
# tests
docker compose exec engine python -m pytest -q     # engine
docker compose exec web npx tsc --noEmit && docker compose exec web npm run lint   # web
```

## Testing & CI

GitHub Actions runs `tsc`, `next lint`, and `pytest` on every PR to `main`/`develop`.
Engine logic that encodes a regulatory rule (risk matrix, country overrides, CDD
tiers, reporting deadlines, evaluation deadlines, catalogues) is pinned by unit tests.

---

*Built grounded in the AML/CTF Act 2006 (Compilation No. 60), AML/CTF Rules 2025, and
AML/CTF Transitional Rules 2026, with AUSTRAC guidance cited inline in the specs.*
