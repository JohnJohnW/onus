# Onus - Deployment (Australian hosting)

Onus holds sensitive, regulated data (KYC documents, beneficial-ownership details,
sanctions/PEP results, suspicious matter reports, 7-year records). **Host it in
Australia.** This keeps data onshore and aligned with the Privacy Act 1988 (Australian
Privacy Principles), AUSTRAC record-keeping, legal professional privilege, and the
Solicitors Conduct Rules. See "Data residency and deployment" in the
[main README](../../README.md) for the reasoning and the Vercel caveat.

This guide covers a simple, defensible production deployment: a single Australian host
running the stack with `docker-compose.prod.yml`, plus the managed-database variant.

## Architecture

```
        HTTPS                      Docker network (private)
client ------> reverse proxy ---> web (Next.js :3000) ---> engine (FastAPI :8000) ---> Postgres
              (Caddy / nginx /                                   |                       (+ pgvector)
               cloud load balancer,                              +--> document volume
               TLS + edge rate limit)
```

- The browser only ever talks to the reverse proxy over HTTPS.
- `web` calls `engine` server-side (the JWT never reaches the browser).
- `engine` connects to Postgres as the least-privilege `onus_app` role (RLS applies);
  migrations run as the owner.
- Keep **all** of it - compute, database, and the document volume - in an Australian
  region (for example `ap-southeast-2`, Sydney).

## Prerequisites

- An Australian-region VM (or container host) with Docker and Docker Compose.
- A TLS-terminating reverse proxy in front of `web` (Caddy is simplest; nginx or a cloud
  load balancer also work). This is also where you add an **edge rate limiter / WAF** -
  the primary defence against volumetric and signup abuse (the app adds per-account login
  throttling and security headers, but the edge sees real client IPs).
- Strong secrets for `JWT_SECRET` and `NEXTAUTH_SECRET` (e.g. `openssl rand -hex 48`),
  ideally from a secrets manager rather than a file.
- An AI provider key. For data residency, prefer Azure OpenAI in an Australian region, or
  a provider whose Data Processing Agreement guarantees Australian processing.

## Path A - single Australian host (bundled Postgres)

1. **Configure secrets.** Copy `.env.production.example` and fill it in (or, better, export
   the variables from your secrets manager). At minimum set `JWT_SECRET`,
   `NEXTAUTH_SECRET`, `NEXTAUTH_URL` (your public HTTPS URL), `POSTGRES_PASSWORD`,
   `ONUS_APP_PASSWORD`, and the AI key. Ensure the password in `DATABASE_URL` matches
   `ONUS_APP_PASSWORD`, and the password in `ALEMBIC_DATABASE_URL` matches
   `POSTGRES_PASSWORD`.

2. **Start the stack.** With the variables in the environment:

   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

   On first boot the engine runs `alembic upgrade head` (as the owner), which creates the
   `onus_app` role with `ONUS_APP_PASSWORD`, then serves. `ONUS_ENV=production` makes the
   engine refuse to start if `JWT_SECRET` is missing or weak.

3. **Put the reverse proxy in front of `web:3000`** and terminate TLS there. Do not expose
   `web` or `db` to the internet directly. The `db` service publishes no host port.

4. **Verify:** browse to your URL, sign up the first firm (becomes the admin), and confirm
   the dashboard loads.

## Path B - managed Australian Postgres (recommended for backups / HA)

Use a managed Postgres in an Australian region (for example AWS RDS/Aurora
`ap-southeast-2`) with `pgvector` available.

1. Create the database and two roles yourself: the owner (for migrations) and the
   non-superuser `onus_app` (for the app; `NOSUPERUSER NOBYPASSRLS`). Grant `onus_app`
   DML on the schema. Because `onus_app` already exists, the migration's create step is
   skipped - you own its password.
2. Enable `pgvector`: `CREATE EXTENSION IF NOT EXISTS vector;`.
3. Delete the `db` service from `docker-compose.prod.yml` and point `DATABASE_URL`
   (onus_app) and `ALEMBIC_DATABASE_URL` (owner) at the managed instance.
4. Start `web` and `engine` as in Path A.

## Operations

- **Migrations** run automatically on engine start (`alembic upgrade head`). To run them
  by hand: `docker compose -f docker-compose.prod.yml run --rm engine alembic upgrade head`.
- **Backups** must stay onshore. Use the managed provider's automated backups
  (point-in-time recovery), or snapshot the `onus_db_data` volume on a schedule, into
  Australian-region storage.
- **Document volume** (`onus_storage`) holds uploaded evidence; back it up onshore too.
- **Audit log** is queryable per firm via the app; export it for an AUSTRAC or Law Society
  request.
- **Logs/observability:** the engine logs a config warning if the signing secret is weak;
  watch for it in your aggregator.

## Security checklist (before go-live)

- [ ] TLS terminated at the reverse proxy; HSTS enabled.
- [ ] Edge rate limiter / WAF in front of the API.
- [ ] `JWT_SECRET` and `NEXTAUTH_SECRET` are strong and injected from a secrets manager.
- [ ] `ONUS_ENV=production` set (weak-secret guard active).
- [ ] At-rest encryption enabled on the database and the document volume.
- [ ] Database and document storage are in an Australian region; backups stay onshore.
- [ ] `AI_PROVIDER` is not `mock`; the AI provider processes in Australia or under a DPA
      that covers it.
- [ ] Database is not reachable from the public internet.

## Data residency / cross-border (APP 8) checklist

Complete this if **any** component (compute, database, AI provider, backups) sits outside
Australia:

- [ ] Documented assessment of the cross-border disclosure (APP 8).
- [ ] Data Processing Agreement in place with every provider in the chain.
- [ ] APP 11 security measures verified (encryption, access control, audit logging).
- [ ] Breach-response plan aligned to the Privacy Act (notifiable data breaches).
- [ ] Written sign-off from the firm's governing body and AML/CTF compliance officer.
- [ ] Legal-professional-privilege risk of offshore storage considered for documents that
      may contain legal advice (program documents, SMRs).

For most small firms, keeping everything in an Australian region is simpler and avoids this
checklist entirely.
