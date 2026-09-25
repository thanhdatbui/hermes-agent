# Model-Specific Rule Refactoring and Claude Supervision

## Why the original rules failed

The old policy was calibrated against an action-biased Gemini-like worker. It used many absolute negative bans but did not define the permitted next action after a worker timeout. A legalistic fallback model treated the strongest prohibition as authoritative and selected `clarify` or a freeze. The durable fix is not weaker safety; it is a model-neutral constitution with explicit state transitions and bounded permissions.

## Canonical escalation contract

1. Classify the result before counting it:
   - `TRANSIENT`: timeout, disconnect, 429/5xx, no worker response. Retry the same contract at most twice; do not consume the structural breaker.
   - `STRUCTURAL`: incorrect patch, repeated test failure, wrong interpretation, or zero files on a Fix-Code task. At most two structural dispatches; the second must materially change the contract.
   - `SCOPE/BUSINESS`: missing authority, irreversible/paid action, or undecidable business choice. Use clarify with evidence and options.
2. After transient retries are exhausted or structural failure reaches its cap, use **Emergency Surgery** only if an exact diff is already known. It is a pre-authorized lane, not a general override:
   - <=2 files including tests;
   - <=30 total added+deleted lines (`git diff --numstat`);
   - no dependency, refactor, rename, policy/config/hooks/credential/account/device changes;
   - worker termination and target cleanliness verified before mutation;
   - logic changes: one offline/mock-focused test under 30s; syntax-only changes: `py_compile` is sufficient;
   - failed verification: revert the exact scope, remove newly created files, record `BLOCKED`;
   - one surgery per subtask; automation still needs its normal canary/closeout proof.
3. Gate failure must resolve to one of: narrow the contract, take L2 if its activation predicate is true, or `BLOCKED` with evidence. “Stop” must identify the stopped scope, not freeze the entire session.
4. `clarify` is not a permission checkpoint for L0/L1/L2 and is not a timeout escape. Its output must contain: evidence tried, 2–3 options, agent recommendation, and a safe default. Never auto-delete, logout, or incur paid cost while unanswered.

## Precedence audit checklist

When changing orchestration rules, inspect all layers that can supersede one another:

- runtime `SOUL.md`;
- runtime `config.yaml` main prompt;
- every Telegram/channel override;
- workspace `AGENTS.md` and standalone rules file;
- dispatch/pre-tool guards and hooks;
- worker handoff and closeout rules.

Search for older phrases such as `MUST NOT perform directly`, `CẤM ... tự sửa`, `CẤM DISPATCH`, `retry prompt cũ`, `tối đa 2 lần dispatch`, and `DỪNG NGAY để báo cáo`. Replace contradictory blocks instead of merely appending an exception. Confirm runtime and deploy copies agree, then parse YAML and verify exact markers.

## Claude CLI supervision loop

Use Claude as a reviewer, not as an implementer:

1. Send a self-contained prompt containing the proposed contract and the exact post-change excerpts. Do not rely on Claude reading protected `D:` paths.
2. Require a first-line verdict: `APPROVED`, `MINOR_FIXES`, or `REJECT`.
3. On `MINOR_FIXES`, apply only exact, unique old→new anchors and re-audit the delta.
4. Keep the complete output in a file; do not pipe through `tail`, which can hide blocker findings.
5. If Claude returns a session-limit/quota message, preserve the last real verdict as unverified. Never convert quota exhaustion into approval; use the configured independent review fallback if the gate is required.
6. Stop after findings converge. Do not keep adding exception blocks or run a fourth loop when the same root cause is recurring.

## Evidence that must be reported

- Which files were changed and whether runtime/deploy copies are synchronized.
- YAML parse result.
- Exact verdict history and whether the final verdict is verified or blocked by quota.
- Any unverified hook/guard behavior; do not claim the prompt alone physically enforces an L2 boundary.
