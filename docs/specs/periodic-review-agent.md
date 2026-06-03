# Spec - Periodic-review agent (Managed Agents / Sessions)

> Purpose: implementation spec for Onus's first autonomous, long-running agent on the
> Claude Managed Agents platform - a periodic-review agent that re-assesses the firm when a
> review falls due, drafts the updated risk assessment + program, flags what changed, and
> stops for human approval. Grounded in managed-agents-evaluation.md (verified API shapes).
>
> STATUS: design ready. The build is gated on one infrastructure prerequisite (section 7) -
> a persistent Australian host. It cannot run on the current Vercel serverless engine.

## 1. Why an agent (not a scripted Messages call)

The drafting we already ship is single-shot: one prompt, one draft. A periodic review is
genuinely multi-step and stateful: re-read the firm's services/clients/matters/screening,
compare to the last approved assessment, decide what changed, redraft the assessment and
the affected program policies, and assemble a change summary - over minutes, with tool use
and a working filesystem. That is what Sessions are for, and the human gate
(`user.tool_confirmation`) is built in.

## 2. Trigger

When a `risk_assessment_review` or program-review `ComplianceDeadline` is within N days (or
overdue), enqueue a review job for the firm. (Also runnable on demand from the Risk Profile
/ Program pages: "Run a review with Onus".)

## 3. Agent configuration (`POST /v1/agents`, beta `managed-agents-2026-04-01`)

- `model`: the configured Claude model.
- `system`: "You are Onus's AML/CTF reviewer for a small Australian law firm. Re-assess the
  firm against AUSTRAC's method, draft updates, and flag changes. You never approve - you
  prepare for the senior manager." Plus our standard ASCII/no-fabrication style rules.
- `tools`: read-only access to the firm's data + write drafts, via **custom tools** backed
  by our API (e.g. `get_firm_profile`, `get_risk_assessment`, `get_clients_summary`,
  `propose_risk_summary`, `propose_program_changes`). Each write tool is gated (section 6).
- `skills`: the AUSTRAC methodology packaged as a Skill (section 8) once available.
- Versioned: update the config as the methodology evolves; new version applies next session.

## 4. Environment (`POST /v1/environments`)

- `config.type`: **`self_hosted`** - the sandbox + tool execution + files run on our AU
  host (section 7), keeping working data onshore. (Cloud is the fallback if we accept the
  residency trade-off with disclosure, per the product philosophy - but self-hosted is the
  default.)
- `config.networking`: `limited` with an `allowed_hosts` allowlist of our own API only;
  `allow_package_managers: false`.

## 5. Session flow (`POST /v1/sessions` + SSE `/events/stream`)

1. Create a session referencing the agent + environment.
2. Send `user.message`: "Review {firm}'s risk assessment and program; draft updates and a
   change summary."
3. Stream agent events (`message`, `thinking`, `tool_use`, `tool_result`).
4. On `session.status_idle` + `stop_reason: requires_action`: a write/consequential tool
   needs confirmation -> surface it to the human; send `user.tool_confirmation`
   (allow/deny) per `event_id`.
5. On completion: the drafted updated assessment + program changes are saved as **drafts**
   (status stays draft) with a change summary; the senior manager approves through the
   existing approval flow (unchanged human gate).
6. Capture the full event transcript to our `AuditLog` / `AgentTask`, then **delete the
   session** (it is not ZDR-eligible) - our audit log is the retained record.

## 6. Human-in-the-loop (non-negotiable)

- Every write/consequential tool (`propose_*`, anything that changes firm data) is gated by
  `user.tool_confirmation`; reads can run freely.
- The agent only ever produces **drafts**. Approval of the risk assessment and program stays
  with the senior manager via the existing endpoints. The agent cannot approve, lodge, or
  sign off anything - same rule as every Onus agent.

## 7. Infrastructure prerequisite (the gate on building)

This cannot run on the current Vercel serverless engine, for two structural reasons:

1. A **self-hosted environment** runs Anthropic's worker process (polls for work, executes
   tools) - a long-lived process. Serverless functions are short-lived; they cannot host it.
2. **Sessions are long-running** (minutes); orchestrating/streaming one from a serverless
   function exceeds function timeouts.

So the periodic-review agent requires the **persistent Australian host** we have discussed
for performance and residency. That host now pays off three ways: it removes cold starts
(performance), keeps client data onshore (residency), and is the home for the self-hosted
worker + session orchestration (this agent). **Standing up that host is the prerequisite,
and the recommended next concrete action.** (A cloud environment would let us prototype
sooner but still needs a persistent process to orchestrate the session, and trades away
residency - so it is a fallback, not the path.)

## 8. Skills

Once we are on the agent runtime, package the AUSTRAC methodology + document templates as a
Skill (`POST /v1/skills`) and reference it in the agent config, so the reviewer uses
consistent, maintainable domain knowledge (updated centrally when AUSTRAC guidance changes).
Skills are not usable from the plain Messages API, so this only applies here.

## 9. Build plan (once the host exists)

1. `engine/ai/managed/` client module: typed calls for agents/environments/sessions/events
   with the `managed-agents-2026-04-01` beta header; feature-flagged off by default.
2. Bootstrap one agent config + one self-hosted environment (idempotent, on the host).
3. Custom tools (read + `propose_*`) backed by our existing endpoints, with the write tools
   behind tool-confirmation.
4. A worker/loop on the host: pick up review jobs, run the session, handle confirmations,
   capture the transcript, delete the session.
5. UI: surface the proposed changes + a change summary on the Risk Profile / Program pages
   for approval; a "Run a review with Onus" trigger.
6. Disclose the processing (self-hosted; inference to Anthropic) to the firm.

## 10. Open items to confirm before/at build

- Session compute pricing (model the per-review unit cost).
- Whether inference can be pinned to an AU-relevant region; DPA coverage.
- Exact custom-tool schema + the self-hosted worker setup/ops.

## Sources

managed-agents-evaluation.md and the Anthropic docs it cites (managed-agents/*,
agent-skills/overview, api-and-data-retention), verified 2026-06-03.
