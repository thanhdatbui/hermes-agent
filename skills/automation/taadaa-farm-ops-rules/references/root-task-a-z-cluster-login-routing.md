# Root-task A–Z, Cluster Canary, and Immediate Login Recovery

## Root-task continuation

When the user orders A–Z completion, treat the request as one persistent root task, not disconnected child tasks. A `delegate_task` child ending does not end the root task. Persist or carry forward `phase`, `status`, `evidence`, `resume_token`, and `next_action`; after `DONE`, `CHECKPOINT`, retryable failure, or timeout, automatically advance, retry, or dispatch a successor. Do not wait for the user to send another message.

Separate lanes:

- **code-surgery:** patch code/fixtures and run focused tests; never wait on device locks.
- **monitor/preemption:** bounded read-only checkpoint; return `LOCK_HELD` with PID/run ID/heartbeat instead of polling blindly.
- **live-runner:** run the official runner only after identity and lock checks pass.
- Lock/drain waiting belongs to a detached deterministic monitor/job, not an LLM child.

Ask the user only for missing credential/2FA, unresolvable identity mismatch, destructive actions, or real business decisions. Dirty files outside scope, stale fixtures, worker timeout, or missing live evidence when offline work remains possible are not stop reasons. Every non-DONE report must include an executable next action.

## Cluster-first canary policy

For multi-machine incidents, classify alerts by failure signature and root-cause hypothesis before live actions. Select one representative canary per cluster. Run independent clusters in parallel when locks and resources permit; do not serialize unrelated machines. A failed representative blocks only its cluster. Fleet reopen requires a passing representative for every identified cluster. Canary every machine only for explicit coverage or documented variant risk. Official runner, lock, screenshot/XML/OCR, and fail-closed gates still apply to every selected representative.

## Immediate TikTok login recovery

When feed flow detects `ACCOUNT_MISSING` or `manual-needed:login`, route immediately through the existing canonical `tiktok_login_v1.py` recovery hook with the required Gmail-live and parent-lock gates. Do not return `manual-needed` before attempting the standard recovery. After login succeeds, perform exactly one post-condition verification with auto-reconcile disabled; if it fails, remain fail-closed with the exact artifact and reason. Never create an ad-hoc login script, guess credentials, use manual taps to bypass the flow, or run `pm clear`.

## Evidence status vocabulary

Use `DONE`, `CHECKPOINT`, `FAILED_RETRYABLE`, `FAILED_FINAL`, and `NEEDS_DECISION` consistently. `LOCK_HELD` is a checkpoint, not success or final failure. `DONE` requires real artifact/test/live evidence; `BLOCKED` requires a concrete blocker and next action.
