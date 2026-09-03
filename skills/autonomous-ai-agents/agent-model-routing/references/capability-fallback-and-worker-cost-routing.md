# Capability-preserving fallback and worker cost routing

Session-derived routing detail; revalidate live model access and prices before applying.

## Separate three axes

1. **Capability** — planning/reasoning quality for the role.
2. **Availability** — quota, account health, transport, and provider uptime.
3. **Cost** — expected total cost including failed first attempts, repeated context, and review.

A high-quota model can be a useful availability fallback without being capability-equivalent. If the fallback is weaker, label the run **degraded** and reduce its authority; do not silently present it as an equal substitute.

## Current operational ladder supplied by the user

These are user-observed capability estimates, not claims about hidden model provenance:

- `gpt-5.6-terra` ≈ Opus 4.8 class for ordinary/medium coordination and planning.
- `gpt-5.6-sol` ≈ Opus 5 class for hard/high-risk coordination and planning.
- Claude Antigravity currently exposes Sonnet/Opus 4.6 with broad quota.
- Claude Pro exposes newer Claude models but has scarce quota, so reserve it for independent audit.

Consequences:

- **Do not route Terra → AG Sonnet 4.6.** That is an unjustified capability drop.
- The broad-quota Claude availability fallback is **AG Opus 4.6**, for Terra or Sol, and must be marked degraded—especially when replacing Sol.
- A degraded coordinator may triage, preserve progress, and do reversible work; it should not independently approve risky live/deploy/security/recovery decisions.
- Availability fallback and independent audit are separate roles even when both use Claude.

Current semantic role split:

| Role | Normal | Hard |
|---|---|---|
| Coordinator/planner | Terra High | Sol High/Max |
| Implementation | DeepSeek Flash for easy/mechanical | DeepSeek Pro for medium/hard logic |
| GPT availability fallback | AG Opus 4.6, degraded | AG Opus 4.6, strongly degraded |
| Independent audit | Newer Claude Pro model, quota-gated | Newer Claude Pro/Opus, quota-gated |

The operator owns account rotation and transport fallback in 9Router. Hermes owns semantic classification and role selection. Do not configure the same transparent fallback in both layers; migrate only after the router lane passes primary/fallback smoke tests.

## Flash vs Pro expected-cost rule

Let Flash cost `1`, Pro cost `r`, and `p` be the probability that a Flash attempt fails and must be redone by Pro.

- Direct Pro cost: `r`
- Flash-first expected cost: `1 + p*r`
- Break-even failure probability: `p = (r - 1) / r`

For the current subsidized ratio `r = 2.76`:

- One failed Flash followed by Pro costs `3.76` Flash units.
- That is `36.23%` more than starting directly with Pro.
- Pure token-cost break-even is `p ≈ 63.77%`.

Latency, repeated context, reviewer time, and risk lower the practical switch point. Therefore:

- Flash: deterministic/mechanical edits, narrow scans, simple tests, independent batch work.
- Pro: medium/hard business logic, multi-file coupling, ambiguous bugs, state/recovery/concurrency, or tasks with a material chance of Flash rework.
- Do not use Flash as a ritual “cheap probe” for work already known to be difficult.

## Review checklist

Before approving a routing map:

- Restate the user's explicit capability ordering.
- Identify every fallback as equivalent or degraded.
- Keep router failures (quota/network/5xx) separate from semantic failures (bad plan/test failure).
- Verify the live model catalog and route names.
- Compute expected retry cost instead of comparing sticker prices alone.
