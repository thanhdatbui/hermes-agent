# Policy/config change closeout review loop

Use this reference when changing SOUL.md, AGENTS.md, HERMES_SUBAGENT_RULES.md, config.yaml, routing policy, delegation settings, or guard prompts.

## Evidence contract

A policy diff has three distinct proof layers:

1. **Text/config proof** — YAML parses; canonical policy sections and channel overrides are consistent; forbidden legacy wording is absent.
2. **Behavior proof** — focused offline tests exercise allow/block branches, hook behavior with mocked stdin/subprocess, timeout/retry classification, and exact scope limits. String-presence assertions alone are insufficient.
3. **Operational proof** — real test command/exit code, staged diff, reviewer verdict/score, and (when relevant) runtime telemetry or canary evidence.

Do not claim layer 3 from layer 1 alone.

## Rejected-gate recovery

When `closeout_gate.py` returns `REJECTED` or score `<85`:

1. Preserve the reviewer findings and exact score.
2. Do not push, commit, or report closeout.
3. Classify each finding as text inconsistency, missing behavior test, missing runtime evidence, or scope/provenance issue.
4. Improve the evidence set with a materially different focused test or exact policy correction. Do not rerun the same gate unchanged.
5. Stage only the intended allowlist. Check `git diff --cached --name-only`, `--stat`, `--numstat`, and `--check`.
6. Run the focused test directly; then rerun the gate so the gate's own test evidence matches the staged diff.
7. Stop after two structurally identical rejection patterns and report the blocker rather than adding speculative production hooks.

## Practical test set

For a policy/routing change, prefer a small offline test module that:

- parses the deploy YAML;
- checks local/deploy SOUL synchronization when the local copy exists;
- iterates every channel override and rejects obsolete budgets or missing escape-hatch wording;
- checks ordered escalation semantics (`TRANSIENT` versus `STRUCTURAL`, no third structural dispatch, L2 activation predicate);
- invokes any existing guard script via `subprocess.run(..., input=json.dumps(payload))` with mocked/offline payloads and verifies both allow and block outcomes;
- checks exact-diff/L2 bounds as data-level predicates rather than merely searching for a phrase.

Keep the test offline and below 30 seconds. Do not add a live device, network, account, or farm canary merely to satisfy a reviewer asking for runtime evidence; either exercise an existing guard safely or report that runtime evidence is a separate scope.

## Model quota fallback

If Claude CLI reaches a session limit, preserve the last Claude result as unverified and route the next independent audit through the configured Sol/OmniRoute fallback. Label the provenance accurately: a fallback review based on pasted excerpts is weaker than a direct filesystem review. Never convert `MINOR_FIXES`, quota errors, or transport failures into `APPROVED`.
