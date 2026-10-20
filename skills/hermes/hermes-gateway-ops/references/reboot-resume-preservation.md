# Reboot-resume preservation: evidence and fix pattern

## Trigger
Use this reference when a scheduled reboot/restart preserves some Hermes sessions but a recent Telegram topic becomes silent afterward.

## Diagnostic sequence
1. Read the reboot/preflight log at the exact reboot timestamp.
2. Trace the real `session_key` through `gateway_routing`; do not infer continuity from a newly created Telegram topic/thread id.
3. Inspect active message rows for that `session_id`: latest role, tool-call payload, timestamp, and `active` flag.
4. Compare routing `updated_at` with the latest active-message timestamp. One clock may be stale while the other is current.
5. Inspect the startup consumer: `resume_pending`, accepted `resume_reason` values, freshness window, adapter readiness, authorization, and restart-loop guard. A marker written by preflight is not proof that startup schedules it.

## Failure pattern
A short preflight lookback can discard a session even though it is still the user's active work context. A second lossy rule that treats every `last_role == "assistant"` as completed can discard a recent session waiting for user direction or whose background work was killed by reboot. The result is a false clean shutdown and a silent Telegram topic.

## Safe fix contract
- Widen lookback only to a bounded operational window appropriate for the reboot cadence; never make it indefinite.
- Preserve a recent Telegram session conservatively when its evidence is inside that window; do not classify it as complete solely from `last_role == "assistant"`.
- Keep an existing startup-accepted reason such as `restart_interrupted` so normal freshness, authorization, and restart-loop guards remain active.
- Do not auto-run unfinished farm/device work from stale transcript text. The resume turn should re-check live state, report restoration, and ask for the next decision when no executable user request is pending.
- Add focused offline regressions for assistant-last recent preservation, stale-session rejection, idempotency, and the explicit reboot lookback.

## Verification
Require the exact source diff, a focused offline test or syntax check after the final edit, and independent inspection of `git diff --numstat`, `git diff --check`, and changed paths. A worker self-report or process exit code is not completion evidence. For background workers, use completion notification; do not poll with `ps`/sleep loops or infer success from a quiet worktree.

## Pitfalls
- If the marker is never written, do not jump straight to Gateway changes; prove the failing stage from log and DB evidence first.
- Do not delete the assistant guard globally without a bounded freshness/authorization rule.
- Do not treat a new Telegram thread id as proof that the old session was resumed or disappeared.
