# Onus - web

The operator UI for Onus, an AI GRC officer for AML/CTF compliance. Next.js 14 (App Router,
TypeScript, Tailwind).

It renders the firm-facing experience and talks to the FastAPI compliance engine only
through server-side proxy routes under `app/api/*`, which attach the session's bearer token -
the token is never exposed to the browser.

See the root `README.md` for the full system: architecture, the engine, data residency,
security and deployment.

## Develop

```bash
npm install
npm run dev      # http://localhost:3000
```

The UI expects the engine reachable at `ENGINE_INTERNAL_URL` (default `http://localhost:8000`)
and the usual next-auth environment. The whole stack runs together via the root Docker
Compose.

## Checks

```bash
npm run lint
npx tsc --noEmit
```
