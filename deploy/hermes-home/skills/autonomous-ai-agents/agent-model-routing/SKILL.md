---
name: agent-model-routing
description: "Route coordinator and worker agents by task difficulty and cost."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [agents, orchestration, model-routing, delegation, cost]
    category: autonomous-ai-agents
    related_skills: [hermes-agent, codex, opencode]
---

# Agent Model Routing Skill

Use this skill when one agent coordinates work while another model or coding CLI performs implementation. It defines routing by role, difficulty, quota, and verification needs. It does not prescribe a permanent ranking for models; provider catalogs and model IDs change, so verify the live catalog before configuring.

## When to Use

- Hermes should plan, delegate, and verify rather than implement everything itself.
- A coding worker has different quota or quality characteristics from the coordinator.
- Multiple models such as Codex and OpenCode Go need role-based routing.
- A local OpenAI-compatible router is being considered for centralized credentials and fallback.

## Prerequisites

- Know the actual provider/model IDs from the provider's current model picker or CLI.
- Confirm which agent can call tools and which agent owns filesystem changes.
- Keep a verification path: diff inspection, tests, logs, or another concrete artifact.

## How to Run

1. Classify the request as routine implementation, architecture/review, or debugging/recovery.
2. Select a coordinator model that is cheap and reliable at planning/tool orchestration.
3. Select a worker model based on implementation difficulty, not brand preference.
4. Delegate with explicit scope, acceptance criteria, workdir, and proof requirements.
5. Inspect the worker's result and run or request verification.
6. Escalate only after evidence: normal worker → stronger review model → recovery/debug model.

## Quick Reference

| Role | Default strategy |
|---|---|
| Coordinator | Cheap, stable model with reliable tool calls and delegation |
| Routine worker | Fast coding model with good repository execution |
| Architecture/review | Strong reasoning model |
| Recovery/debugging | Strong reasoning model after a classified failure |
| Final gate | Coordinator verifies proof; never trust a completion claim alone |

A practical split when Codex quota is available is: Hermes coordinator on a low-cost OpenCode Go model; Codex Luna for routine implementation; Codex Sol for architecture/review; Codex Terra for debugging/recovery. For the current OpenCode Go catalog, Qwen3.7 Plus is a reasonable coordinator starting point, with DeepSeek V4 Flash or MiMo-V2.5 as cheaper fallbacks. Verify IDs live before use.

For this user's preferred role loop, route Codex through the local 9Router `omni` provider: default worker/debugging model `gpt-5.6-luna` at high effort; use `gpt-5.6-sol` at high effort for planning, audit/review, and code changes; when automation debugging in `D:/Taadaa` loops, escalate Luna → Terra → Sol. Use Claude Opus at low effort as the default independent reviewer, with OpenCode only as reviewer fallback when Claude quota/provider access fails. The loop is Worker implementation → Reviewer audit → Worker accepts/rejects each finding with evidence → Reviewer consensus re-check, bounded by a maximum round count and persisted state/artifacts.

## Procedure

### Portable Hermes setup and migration

When moving a coordinator/worker setup to another PC, separate portable behavior from machine-local state:

1. Move or clone the Hermes source repo if it contains custom code or bundled skill changes; the repo alone is not the complete user configuration.
2. Export the active Hermes profile with `hermes profile export default -o <archive>.tar.gz`, then import it on the destination with `hermes profile import <archive>.tar.gz --name default`. This carries user-facing configuration, skills, plugins, cron, scripts, persona, and related preferences while intentionally excluding credentials and runtime databases.
3. Install the external worker CLIs independently on the destination (Claude Code and Codex) and verify their versions.
4. Authenticate again on the destination with each CLI and with Hermes (`hermes auth add ...`) instead of copying `.env`, `auth.json`, or CLI credential directories through Git/cloud storage.
5. Run `hermes doctor`, `hermes skills list`, and `hermes tools list`; execute a harmless task in a Git repository to verify the coordinator → worker → verification path.
6. If user-level skills override bundled skills, ensure the exported `skills/` content is included and inspect the destination's effective skill list after import.

Do not copy the entire Hermes home blindly: caches, SQLite state, locks, absolute paths, and secrets are machine-specific. A manual migration should copy `config.yaml`, `SOUL.md`, user `skills/`, `plugins/`, `cron/`, and `scripts/`, then re-authenticate secrets separately.

### Coordinator prompt contract

Tell the coordinator explicitly:

- Do not implement the main task itself unless a tiny coordinator-side fix is necessary.
- Break the request into independently verifiable worker tasks.
- Require workers to report changed files, commands run, and concrete output.
- Inspect the result and classify failures before retrying.
- Do not report success without proof.

Keep coordinator access to read-only inspection and verification tools where possible. Do not remove its ability to inspect diffs, logs, and tests: a delegation-only coordinator cannot validate worker claims.

### Escalation policy

- Routine implementation: fast worker first.
- Design or broad refactor: stronger worker/reviewer first.
- Test failure: classify the failure, then use a different recovery action/model; do not blindly rerun.
- Repeated identical failure: stop and report the signature and artifact rather than looping.

### Router decision

Use a local router when several clients need one credential store, provider fallback, or one stable OpenAI-compatible endpoint. First smoke-test the direct path (client → provider), then add the router hop. In the routed path:

```text
client → local router → upstream provider/model
```

Store the upstream credential in the router. Configure the client with the router endpoint and the router's local authentication key, not the upstream credential. Keep direct configuration when only one client needs the provider or when simpler debugging is more valuable than centralized routing.

## Pitfalls

- Do not use the strongest coding model for every coordinator turn; orchestration usually does not need maximum coding ability.
- Do not assume a model name or catalog is current; verify the live `/models` list/provider metadata.
- Do not confuse an upstream provider key with a local router key.
- Do not make the coordinator pure delegation-only if no component can independently inspect and verify results.
- Do not retry the same failed worker command without a changed hypothesis or recovery action.
- Do not claim success from a worker's prose alone.

## Verification

For each worker task, record:

- selected model and reason;
- workdir/repository scope;
- changed files or explicit no-change result;
- test/build/lint commands and actual output;
- unresolved risks or recovery attempts.

For router setup, verify the local endpoint with a harmless smoke request, confirm the requested model ID is accepted, and confirm the upstream key is not exposed in the client configuration or logs.
