# Batch Alert: UploadHook Post Verification Inconclusive/Timeout False Positive Triage

## 1. Symptom & Alert Pattern
When a fleet batch alert reports:
```text
🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM ADMIN / KIBE】
...
⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện N máy gặp captcha/xác minh (chưa mất phiên):
   • Máy Mxxx: UploadHook: 2026-10-22 06:44:35,695 [ERROR] scripts.tiktok_workflow.state_machine: Post verification inconclusive/failed: TIMEOUT
```

## 2. Root Cause Analysis
- Consumer upload workflow (`scripts.tiktok_workflow.state_machine`) executes post-publish verification via `PostVerifier.verify_post()`.
- When network or TikTok indexing latency exceeds 120s, the consumer logs:
  `Post verification inconclusive/failed: TIMEOUT`
  and executes `_recheck_ambiguous_post()`. It concludes inconclusive, avoids reposting duplicate video, and safely navigates back to Home screen (LauncherActivity).
- However, `automation_core/batch_aggregator.py` has `CHALLENGE_KEYWORDS` including `"verification"`.
- Without `"post verification"` in `CHALLENGE_EXCLUSIONS`, `batch_aggregator` matches `"verification"` and misclassifies the upload verification timeout as a `challenge_failure` ("CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI").

## 3. O(1) Evidence Verification
1. Run O(1) inspection on the flagged machines:
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
2. Verify:
   - Current focus is `LauncherActivity` (Home screen) or TikTok closed.
   - Screen state is `OFF (Sleep/Dozing)` or clean idle.
   - Proxy is reachable and returning public egress IP.
3. Conclusion: **FALSE POSITIVE** — no Captcha, no checkpoint, no session loss.

## 4. Operator Communication & Resolution Protocol
- **Direct & Blunt Answer**: When the operator asks "Là tóm lại lỗi gì sao bị report báo lỗi", avoid vague summaries. State immediately:
  - This is a false alarm from watchdog keyword collision (`verification` matched in upload hook timeout).
  - Devices are verified clean and idle at Home screen, zero Captchas.
- **Immediate Fix (No Delay)**:
  - Add `"post verification"` to `CHALLENGE_EXCLUSIONS` in `automation-core/src/automation_core/batch_aggregator.py`.
  - Add focused test in `tests/test_batch_aggregator.py`.
  - Verify via focused pytest.
