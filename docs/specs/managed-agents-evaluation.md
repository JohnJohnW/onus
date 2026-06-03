# Spec - Evaluation: Claude Managed Agents / Sessions / Skills

> Purpose: a grounded decision aid on whether and how Onus should adopt Anthropic's beta
> Managed Agents platform (Agents + Sessions + Environments APIs) and the Skills API,
> beyond the Files API we already use. Verified against the live docs (platform.claude.com,
> 2026-06-03); uncertainties flagged explicitly. Companion to product-direction.md.

## 1. Verdict

**Keep the existing features on the Messages API + our own propose/dispose loop. Adopt
Managed Agents selectively, later, only for genuinely autonomous, long-running, multi-step
workflows - and if we do, run a self-hosted environment on our Australian host.** The
platform is real and capable, but it costs more, adds moving parts, and (in cloud mode)
is not ZDR/HIPAA-eligible. Its standout feature for us is the **self-hosted environment**,
which keeps the agent's execution and files on our own infrastructure.

## 2. What each piece is (verified)

- **Agents API** (`POST /v1/agents`): a stored, versioned agent *configuration* (model,
  system prompt, tools, skills). It does not execute on its own.
- **Sessions API** (`POST /v1/sessions`, SSE `/events/stream`): a running, stateful agent
  instance that executes a task over time - tool use (bash, file read/write, web), a
  persistent filesystem, conversation state. Long-running; resumable; deleted explicitly.
- **Environments API** (`POST /v1/environments`): the sandbox template a session runs in.
  **Two types: `cloud` (Anthropic-operated) and `self_hosted` (our own infrastructure,
  via a worker process).** Configurable packages + network allowlist.
- **Skills API** (`POST /v1/skills`): a reusable, filesystem-based package (a SKILL.md +
  bundled resources) of domain expertise. **Consumed only by an agent runtime** (Managed
  Agents, Claude Code, or the code-execution container) - **not available through plain
  Messages API calls.**
- Beta header for the platform: `managed-agents-2026-04-01`.

## 3. The data-residency question (the crux for Onus)

- **Cloud environments** run in Anthropic-operated sandboxes; the region is **not
  documented as configurable**, and Managed Agents are **not ZDR- or HIPAA-eligible** -
  session data (conversation, filesystem) is retained until we delete it. For a
  privacy-sensitive AU legal product, putting client data into cloud sandboxes is the
  concern I flagged.
- **Self-hosted environments** change the calculus: the sandbox, tool execution, and
  filesystem run **on our own infrastructure** (we run Anthropic's worker that polls for
  work). Model inference still goes to Anthropic (as it already does today for every AI
  feature), but the agent's *working data and files stay on our AU host.* This is the
  best-effort-residency path that fits the "innovate boldly, respect sovereignty, disclose"
  principle.
- UNCERTAIN (confirm before committing): whether `inference_geo` can pin inference to a
  region relevant to AU; exact self-hosted network-isolation guarantees; whether a DPA
  covers this. Worth a direct check with Anthropic.

## 4. What it would unlock for Onus

The Messages API + our loop is great for *single-shot* "propose" steps (drafting,
document analysis, the brief). Managed Agents/Sessions earn their keep for **autonomous,
multi-step, stateful** work, with **built-in human-in-the-loop** via `user.tool_confirmation`
(allow/deny) and `user.interrupt`:

- A **periodic-review agent**: when the risk-assessment or program review falls due, run a
  session that re-reads the firm's data, drafts the updated assessment + program, flags
  what changed, and stops for approval - over minutes, not one call.
- A **deep-investigation agent**: on a serious alert, gather the client/matter/screening
  history, check the documents, and assemble an SMR-ready pack, pausing for the human at
  each consequential step.
- An **onboarding agent** that runs the whole chain end to end with tool-confirmation
  gates (a more autonomous version of today's client-side orchestrator).

The human gate maps natively: the session pauses (`requires_action`) and we send allow/deny.

## 5. Costs and trade-offs

- **Cost:** tokens (as today) **plus session/compute charges** (exact rate not published -
  contact sales). For a small-firm SaaS, per-session compute is a real unit cost to model.
- **Complexity:** event-stream handling, session lifecycle (store IDs, delete after
  retention, checkpoint to our DB for the audit trail), environment/worker ops if
  self-hosted.
- **Loss of ZDR/HIPAA** in cloud mode (mitigated by self-hosted + deletion discipline).
- **Lock-in:** these are Anthropic-specific; our current provider-agnostic `ai/` layer
  would not cover them. Acceptable for a deliberate, bounded use - not for the whole app.

## 6. Recommendation

1. **Do not migrate** existing features (drafting, document understanding, the brief). They
   are simpler, cheaper, ZDR-eligible, and fully under our control on the Messages API.
2. **Adopt Managed Agents only for a specific autonomous workflow** where statefulness +
   tools + multi-step execution clearly beat a scripted loop - the **periodic-review agent**
   is the best first candidate.
3. **If adopted, use a self-hosted environment on the AU host** (so working data/files stay
   onshore), enforce tool-confirmation checkpoints on every consequential action, delete
   sessions after the retention window (checkpointing the transcript to our own audit log
   first), and **disclose** the processing to the firm.
4. **Skills:** only worth packaging the AUSTRAC methodology as a Skill *if* we adopt the
   agent runtime (it cannot be used from the Messages API). Until then, the system prompt is
   our "skill".

Net: the platform is a strong fit for a *future* autonomous-workflow tier, gated behind the
self-hosted environment for residency. It is not a reason to rebuild what already works.

## 7. Next step if we proceed

Prototype the **periodic-review agent** on a self-hosted environment: one agent config, one
environment, a session triggered when a review deadline nears, with tool-confirmation gates
and transcript capture to our audit log. Scope it as its own spec before building.

## Sources

Anthropic docs (verified 2026-06-03): managed-agents/overview, /agent-setup, /sessions,
/environments, /events-and-streaming, /reference; agents-and-tools/agent-skills/overview;
manage-claude/api-and-data-retention. Uncertainties (AU region for cloud sandboxes, exact
session pricing, DPA coverage) to confirm with Anthropic before committing.
