# Batch Aggregator: Post Verification Timeout vs Challenge Detection

## Context
In `automation-core/src/automation_core/batch_aggregator.py`, batch runs across the fleet are evaluated for systemic and critical errors.
The aggregation logic checks:
```python
CHALLENGE_KEYWORDS: tuple[str, ...] = (
    "verification",
    "manual_challenge",
    "checkpoint",
    "captcha",
    "xác minh",
    "xac minh",
)
```

## Problem (Keyword Collision False Positive)
When TikTok upload workflows in consumer repos (`Tiktok-video` / `scripts.tiktok_workflow.state_machine`) perform post-verification via `PostVerifier.verify_post()` with a 120-second timeout, if TikTok or the network is slow, it emits:
```text
UploadHook: 2026-10-22 06:44:35,695 [ERROR] scripts.tiktok_workflow.state_machine: Post verification inconclusive/failed: TIMEOUT
```
Because `"verification"` is in `CHALLENGE_KEYWORDS`, `batch_aggregator.py` matches `post verification` and marks the failure as a `challenge_failure`.
This leads to false-positive alerts on Telegram:
`⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện N máy gặp captcha/xác minh (chưa mất phiên)`
even when the devices are clean, at Home screen, and completely free of any Captcha or verification challenges.

## Remedy & Fix Invariant
In `automation_core/batch_aggregator.py`:
1. `CHALLENGE_EXCLUSIONS` must include `"post verification"` alongside `"profile verification"`, `"ip verification"`, and `"verification failed"`:
   ```python
   CHALLENGE_EXCLUSIONS: tuple[str, ...] = (
       "did not verify",
       "failed to verify",
       "could not verify",
       "cannot verify",
       "unable to verify",
       "recapture did not verify",
       "ip verification",
       "profile verification",
       "post verification",
       "verification failed",
       "egress",
       "proxy",
       "vpn",
   )
   ```
2. When triaging batch alerts with `UploadHook: ... Post verification inconclusive/failed: TIMEOUT`, verify device state via O(1) inspect (`inspect_machine.py`) before concluding there is a real challenge or Captcha.
