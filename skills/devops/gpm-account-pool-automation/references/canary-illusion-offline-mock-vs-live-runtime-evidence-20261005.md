# Canary evidence: offline tests vs live GPM/OmniRoute

## Core rule
A passing pytest suite with mocks is offline regression evidence, not a live canary. A scheduler/cron return of `execution_success: true` only proves the launcher was invoked, not that the named account recovered.

## Live Canary acceptance gate
Report PASS only when all three target-bound artifacts exist for the same run:
1. Fresh screenshot from the exact GPM/Chromium profile, with valid size and OCR/visual state proving the target result (never a Home/Launcher or unrelated S7 image).
2. Fresh OmniRoute/provider state showing the same target connection changed to the expected active/valid state.
3. Execution log naming the exact target email/profile and recording the live CDP/login/token/validation path.

Missing any one item is `UNPROVEN` or `BLOCKED`, not success. Worker summaries are untrusted until the paths and contents are independently verified.

## Required report labels
Use exactly:
- `Offline test`: pytest/mock result and test count.
- `Live canary`: whether the real profile was opened and the target was exercised.
- `Evidence`: exact screenshot/log/state paths and timestamps.
- `Confirmed / Excluded / Unproven`.
- `Blocker / next action`.

Never title a report "Canary nghiệm thu" when only mock tests passed. Never infer a target account from a cron job's successful launcher status. If the worker is blocked by a sandbox/action gate, report `BLOCKED_BY_SANDBOX_POLICY` and do not substitute offline passes.

## Target binding before launch
Before a live run, verify the exact email-to-profile mapping from the current source of truth. Do not overwrite a multi-profile login list blindly to force a target into an existing script. Preserve unrelated profiles, use a target-scoped official runner, and record the target profile ID, machine/serial (if applicable), and run artifact root.

## Screenshots and UI evidence
For browser/GPM UI actions, keep the pre-action and post-action evidence checkpoints. Capture the result immediately after submit/navigation, and inspect OCR/DOM before claiming success. For live mobile/browser tasks, do not use a phone screenshot to prove a PC GPM result. If no fresh target screenshot exists, explicitly say `capture_artifact_missing`.

## Service preflight ≠ canary
A successful OmniRoute/GPM connectivity check or a pytest selection failure is only a harness/preflight result. It does not validate relogin. If requested test node IDs do not exist, collect the actual node IDs and run the nearest focused test, but keep it separate from the live canary verdict.

## References
- `references/canary-illusion-offline-mock-vs-live-runtime-evidence-20261005.md` — incident detail and tri-evidence rationale.
