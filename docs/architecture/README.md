# Onus — Architecture

> Onus is an AI GRC (Governance, Risk & Compliance) officer for small Australian
> law firms, purpose-built for AML/CTF compliance under Australia's Tranche 2 reforms.

## What is Onus?

Australia's "Tranche 2" reforms extend the *Anti-Money Laundering and
Counter-Terrorism Financing Act 2006* (the AML/CTF Act) to "designated
non-financial businesses and professions" — including legal practitioners. Small
law firms now carry obligations they have historically never had to
operationalise: enrolling with AUSTRAC, performing customer due diligence (CDD),
screening clients against sanctions and politically-exposed-person (PEP) lists,
conducting ongoing monitoring, maintaining a written AML/CTF program, and keeping
audit-ready records.

Onus acts as an always-on compliance officer for these firms. It guides matter
intake, runs the due-diligence and screening workflows, scores money-laundering /
terrorism-financing (ML/TF) risk, records every decision with an audit trail, and
produces the artifacts a firm needs to demonstrate compliance to AUSTRAC.

This repository is a monorepo containing the full Onus stack.

## System overview

Onus runs as three services, orchestrated locally with Docker Compose:

```
            ┌────────────────────┐
 browser ─▶ │  web (Next.js)     │  :3000
            │  operator UI       │
            └─────────┬──────────┘
                      │ HTTP (REST)
            ┌─────────▼──────────┐
            │  engine (FastAPI)  │  :8000
            │  compliance API    │
            └─────────┬──────────┘
                      │ SQL + vectors
            ┌─────────▼──────────┐
            │  db (Postgres 15   │  :5432
            │  + pgvector)       │
            └────────────────────┘
```

| Service  | Stack                                            | Port | Responsibility |
|----------|--------------------------------------------------|------|----------------|
| `web`    | Next.js · App Router · TypeScript · Tailwind     | 3000 | Operator-facing UI — matter intake, CDD workflows, risk dashboards, reporting |
| `engine` | FastAPI · Python 3.11 · SQLAlchemy · Alembic     | 8000 | Compliance API — due diligence, sanctions/PEP screening, risk scoring, document generation, auth |
| `db`     | PostgreSQL 15 + pgvector                         | 5432 | Relational data plus vector embeddings for semantic search / retrieval |

## Stack decisions and why

**Next.js (App Router, TypeScript, Tailwind) — `web`**
One framework for server- and client-rendered UI with first-class TypeScript
support. The App Router gives server components and route-level data fetching,
Tailwind keeps styling consistent without a heavy component library, and
production deploys are straightforward later.

**FastAPI (Python 3.11) — `engine`**
The compliance logic is data- and integration-heavy (screening providers,
document parsing, future ML / embedding work), which is squarely Python's
strength. FastAPI gives typed request/response models via Pydantic, automatic
OpenAPI docs, and async I/O for calling external screening APIs.

**PostgreSQL 15 + pgvector — `db`**
A single durable store for both relational compliance records and vector
embeddings. `pgvector` lets us do semantic search and retrieval (matching client
data, regulation lookup, document Q&A) without standing up a separate vector
database. We use the `pgvector/pgvector:pg15` image because the stock
`postgres:15` image does not bundle the extension.

**SQLAlchemy + Alembic**
SQLAlchemy as the data/ORM layer and Alembic for versioned, reviewable schema
migrations — essential when the data model underpins an auditable compliance
record.

**Auth — NextAuth + bcrypt + python-jose**
NextAuth manages sessions in the web tier; the engine issues/validates JWTs
(`python-jose`) and hashes credentials (`bcrypt`).

**External integrations (configured via environment)**
- **Azure OpenAI** — LLM reasoning for risk narratives, document understanding,
  and assistant features (Azure for data-residency / enterprise posture).
- **OpenSanctions** — sanctions, watchlist, and PEP screening data.
- **Resend** — transactional email (alerts, review reminders, reports).

**Docker Compose**
One command brings up the whole stack with hot reload, so every developer runs an
identical web + engine + db environment.

## Local development setup

### Prerequisites
- Docker Desktop (Docker Engine 24+ and Compose v2)
- To run the services outside Docker: Node.js 20 and Python 3.11

### 1. Configure environment
```bash
cp .env.local.example .env.local
# then fill in the blank secrets (NEXTAUTH_SECRET, Azure OpenAI, OpenSanctions, Resend)
```
`.env.local` is git-ignored. All three services read it via Docker Compose.

> Note: inside the Docker network the database host is `db`, not `localhost`.
> Compose overrides `DATABASE_URL` to
> `postgresql://onus:onus_local@db:5432/onus` for the `engine` service
> automatically; the `localhost` value in `.env.local` is for tooling run on the
> host (psql, Alembic, etc.).

### 2. Start the stack
```bash
docker compose up
```
- web → http://localhost:3000
- engine → http://localhost:8000 (health check: http://localhost:8000/health)
- db → localhost:5432 (database / user / password: `onus` / `onus` / `onus_local`)

Source for `web` and `engine` is bind-mounted, so edits hot-reload.

### 3. (Optional) Run services directly on the host
Web:
```bash
cd web && npm install && npm run dev
```
Engine:
```bash
cd engine
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Database migrations (Alembic)
```bash
cd engine
source .venv/bin/activate
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## The three services

### `web` — Next.js front end
Operator-facing application for the firm's staff: matter/client intake, the guided
CDD workflow, risk dashboards, alerts, and report/export views. Talks to `engine`
over REST. Lives in [`web/`](../../web).

### `engine` — FastAPI compliance API
The compliance brain. Exposes the API consumed by `web`, owns the data model and
migrations, runs sanctions/PEP screening and risk scoring, integrates with Azure
OpenAI for reasoning/generation, and enforces auth. Health endpoint:
`GET /health` → `{"status": "ok", "service": "onus-engine"}`. Lives in
[`engine/`](../../engine).

### `db` — PostgreSQL 15 + pgvector
Durable storage for compliance records (clients, matters, screening results, risk
assessments, audit log) and vector embeddings for semantic retrieval. Data
persists in the `onus_db_data` Docker volume; the `vector` extension is enabled on
first boot via
[`infrastructure/docker/db/init.sql`](../../infrastructure/docker/db/init.sql).

## Repository layout
```
onus/
├── web/                      # Next.js front end
├── engine/                   # FastAPI compliance API
│   ├── main.py               # app + /health
│   ├── requirements.txt
│   └── alembic/              # migrations
├── infrastructure/
│   └── docker/               # service Dockerfiles + db init
├── docs/
│   ├── architecture/         # this document
│   └── data-model/           # entities, ERDs, schema notes
├── .github/workflows/        # CI
├── docker-compose.yml
└── .env.local.example
```
