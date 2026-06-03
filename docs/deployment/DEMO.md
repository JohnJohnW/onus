# Onus - free demo deployment (Vercel + Supabase)

A free, public **demo** with everything on Vercel + Supabase: the Next.js front end and
the FastAPI engine both on Vercel, Postgres on Supabase. This is for evaluation only -
the compute is US-hosted (Vercel), so **do not enter real client data**. The app shows a
demo banner and a `/hosting` page disclosing this and offering an Australian-hosted option.

> This serverless path has demo-only trade-offs (see the bottom). For a reliable,
> full-featured deployment, use the Docker path in [README.md](README.md) instead.

You'll create the accounts and do the logins, secrets, and "deploy" clicks (I can't).
Order: **database -> migrate -> engine -> front end**.

---

## 1. Database - Supabase

1. Sign up / log in at supabase.com and create a **New project**. Choose region
   **Sydney (Oceania)** if offered (keeps data in Australia). Set a database password.
2. In **SQL Editor**, run (choose a strong password for `onus_app`):
   ```sql
   create extension if not exists vector;
   create role onus_app login password 'PICK_A_STRONG_PASSWORD'
     nosuperuser nocreatedb nocreaterole nobypassrls;
   grant usage on schema public to onus_app;
   ```
3. In **Project Settings -> Database -> Connection string**, copy the URI Supabase gives
   you. You'll need two forms (keep them private):
   - the **owner** string (user `postgres`) - for migrations
   - the same host/db with user `onus_app` and its password - for the app

   If a connection later fails from GitHub Actions or Vercel, use Supabase's **pooler**
   (IPv4) connection string instead of the direct one - paste me the error and I'll point
   to the right one.

## 2. Migrate the schema (GitHub Action)

The engine runs on serverless functions, so migrations are applied once via a workflow.

1. In your GitHub repo: **Settings -> Secrets and variables -> Actions -> New secret**:
   - `MIGRATE_DATABASE_URL` = the Supabase **owner** connection string
   - `ONUS_APP_PASSWORD` = the password you chose for `onus_app`
2. **Actions** tab -> "Migrate database (manual)" -> **Run workflow**. It applies
   `alembic upgrade head` to Supabase. (Green check = schema created.)

## 3. Engine - Vercel (Python serverless)

1. vercel.com -> **Add New -> Project**, import this repo (authorize GitHub).
2. Set **Root Directory** to `engine`. Vercel reads `engine/vercel.json` and serves the
   FastAPI app from `api/index.py`.
3. Environment Variables:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | Supabase `onus_app` connection string |
   | `JWT_SECRET` | a long random value (`openssl rand -hex 48`) |
   | `ONUS_ENV` | `production` |
   | `STORAGE_DIR` | `/tmp/onus-documents` |
   | `AI_PROVIDER` | `anthropic` |
   | `ANTHROPIC_API_KEY` | your key (optional; AI drafting needs it) |

4. Deploy. When live, note the URL (e.g. `https://onus-engine.vercel.app`) and check
   `https://onus-engine.vercel.app/health` returns `{"status":"ok",...}`.

## 4. Front end - Vercel

1. **Add New -> Project**, import the **same repo** again (a second Vercel project).
2. Set **Root Directory** to `web` (Next.js auto-detected).
3. Environment Variables:

   | Name | Value |
   |---|---|
   | `ENGINE_INTERNAL_URL` | your engine URL from step 3 (e.g. `https://onus-engine.vercel.app`) |
   | `NEXTAUTH_URL` | this project's URL (e.g. `https://onus-demo.vercel.app`) |
   | `NEXTAUTH_SECRET` | a long random value (`openssl rand -hex 48`) |
   | `NEXT_PUBLIC_DEMO` | `true` |

4. Deploy. If the final domain differs from `NEXTAUTH_URL`, update it and redeploy.

## Verify

- Open the front-end URL: landing page + amber **demo banner**; `/hosting` shows the
  trade-offs and the interest form.
- Sign up a firm, complete onboarding, confirm the dashboard populates.
- Expressions of interest land in Supabase: `select * from demo_eois;`.

## Demo-only trade-offs (Vercel serverless)

- **US compute** (Vercel) -> not for real client data. The banner says so.
- **Uploaded documents do not persist** - the serverless filesystem is ephemeral
  (`/tmp`). Fine for a click-through demo.
- **Long AI drafting calls can time out** on the free function limit (~10-60s).
- **Cold starts** - the first request after idle is slow.

A real Australian deployment (Docker engine + managed AU Postgres, no timeouts, durable
storage) is in [README.md](README.md); `render.yaml` is a ready alternative engine host.
