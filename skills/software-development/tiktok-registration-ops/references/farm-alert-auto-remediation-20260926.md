# Farm Alert Auto-Remediation Loop

A farm alert is an execution trigger, not a diagnosis-only request. Use this class workflow:

`ALERTED -> RESOLVE_TARGET -> EVIDENCE_CAPTURED -> CLASSIFIED -> WORK_ASSIGNED -> PATCH_VERIFIED -> CANARY_APPROVED -> CANARY_RESULT -> CLOSED/BLOCKED`

`DIAGNOSED` is never terminal.

## Evidence gate

- Read a bounded window from the exact current canonical run log; never load a multi-hundred-MB log wholesale.
- Correlate run ID, machine, serial, timestamp, XML, and screenshot. A stale artifact is not evidence.
- Open the matching XML and screenshot; quote UI text/resource IDs and label findings `CONFIRMED`, `EXCLUDED`, or `UNPROVEN`.
- Read the matching `docs/farm-automation-cases.md` / `docs/uiautomator.md` case before selector/state changes.

## Classification

- `STRUCTURAL`: same fingerprint plus same screen/state/function on >=2 machines in one run, or deterministic parser/selector mismatch. Dispatch one worker per fingerprint.
- `INFRA`: serial not found, device offline, ADB/ATX unavailable. Preserve lock and escalate; do not retry the registration runner or patch code from this evidence alone.
- `TRANSIENT`: bounded timeout with a healthy resolved device. Retry at most twice per `(machine, fingerprint, alert-chain)`; do not reset the counter in a new alert.
- `UNKNOWN_UI`: preserve XML/screenshot, fail closed; fix only the detector portion, while OTP/phone/business actions remain manual.
- `BUSINESS/MIXED`: never auto-submit or bypass OTP, phone verification, capacity, or ownership decisions.

## Worker/verification contract

Provide exact files, function anchor, evidence paths, expected delta, focused offline test, allowlist, and budget. Worker must abort if scope is infeasible. Coordinator independently checks allowlisted diff, `git diff --check`, numstat, syntax, and reruns the focused test against the real incident XML fixture.

## Canary gate

After independent verification only: one official runner, one resolved machine, one bounded attempt, correct lock, Safe Resume checkpoint, fresh XML/screenshot/log. Never use manual tap/keyevent/ime, broad scans, pause cron, or release a failed lock. Two same-signature meaningful failures produce `BLOCKED + Audit Packet + handoff`.

## Known detector pitfall

TikTok email verification XML can contain `Xác minh email`, `Sử dụng liên kết này hoặc nhập mã được gửi đến ...`, `Gửi lại mã`, and `Bạn cần trợ giúp đăng nhập?`. Because `_tiktok_flat_xml()` is package-scoped, add accent-normalized phrases to both primary OTP detection and secondary fallback so the existing `registered_otp` state is returned instead of `[07] unknown`. This does not authorize solving OTP automatically.
