---
name: ui-evidence-first
description: Use when investigating any UI, device, log, XML, screenshot, or artifact issue across any repo; read exact evidence before conclusions.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [ui, xml, screenshots, logs, artifacts, debugging, evidence]
    related_skills: [systematic-debugging, agent-verification-loop]
---

# UI Evidence First — Global Rule

References:
- `references/avatar-upload-false-success-20260903.md` — Avatar runner exit-0/log-success false-positive: requires fresh live profile screenshot with non-placeholder avatar before claiming success.
- `references/capture-timing-and-anchor-resolution.md` — Differential review and regression fixture pattern for timing/anchor resolution.
- `references/screenshot-product-claim-audit.md` — Evidence matrix and report template for external posts and product claims.
- `references/telegram-incoming-image-investigation.md` — Workflow for extracting, reading via local LLM vision endpoint, and verifying Telegram image attachments and farm alerts.
- `references/uiautomator-popup-case-fixes.md` — Case Fix & Anti-Pattern catalog for UIAutomator, popup detection, and negative exclusions (mandatory reading per `docs/uiautomator.md`).

## Scope

This is a global Hermes workflow for **every repository and every script**: flows, workers, schedulers, recovery, popup handling, login, registration, upload, follow, feed, device automation, tests, and incident investigation. It is not limited to TikTok or profile verification.

## Mandatory evidence gate

## Fix báo lỗi máy = Sửa script toàn cục (CẤM fix tay)
Khi user yêu cầu fix lỗi trên máy N (kèm ảnh chụp/alert/log):
1. **Trích xuất hiện trường nhanh (CẤM GREP / CẤM QUÉT ĐĨA):**
   - Chạy duy nhất `python D:/Taadaa/tools/inspect_machine.py <N>` hoặc kiểm tra ADB trực tiếp theo serial.
   - TUYỆT ĐỐI CẤM dùng `os.walk`, `glob(recursive=True)`, `find`, `grep -rn` quét diện rộng codebase hay ổ đĩa để tìm chuỗi lỗi / file log.
2. **Hiện trường máy là Read-Only Evidence:** Trạng thái, màn hình và XML trên máy N chỉ dùng để trích xuất bằng chứng phân tích root cause.
3. **BẮT BUỘC ĐỌC FILE CASE TRƯỚC KHI SỬA:**
   - Trước khi sửa bất kỳ logic code/flow/matcher/parser nào, BẮT BUỘC đọc file case trong repo (`docs/farm-automation-cases.md` / `docs/uiautomator.md`) hoặc case catalog để đối chiếu hiện tượng, kiểm tra xem case này đã có chưa, tránh sửa trùng lặp code và tránh tái diễn các Anti-Pattern đã bị cấm.
4. **Nhiệm vụ Fix BẮT BUỘC là Patch mã nguồn script:**
   - Sửa logic code/flow/matcher/parser trong repo tương ứng để giải quyết dứt điểm cho toàn bộ 160 máy trên Farm.
   - BẮT BUỘC chạy unit test / regression test xác nhận logic mới.
   - BẮT BUỘC cập nhật Case Fix và Anti-Pattern vào `docs/farm-automation-cases.md` (Gate 0.5).
5. **CẤM thao tác bấm tay / Ad-hoc bypass:** Tuyệt đối CẤM coi việc gửi lệnh ADB bấm tay, tap qua màn hình, gửi phím Home/Back để máy hết kẹt là đã hoàn thành task. Thao tác tay chỉ che giấu lỗi tạm thời trên 1 máy và để lại lỗi hệ thống trên các máy khác.

Before concluding which screen, account, popup, blocker, or recovery actor was involved:

1. Identify the exact repository/task scope, run ID, target machine/device/serial, account scope, timestamp, and artifact root.
2. Read the target `log.jsonl` around the failure or decision point, including the immediately preceding and following events. Read manifest, recovery metadata, and lock metadata when the log references them.
3. Resolve the **exact attempt artifact**. A directory path, `artifact_path`, `xml_available=true`, parser field, summary line, or folder name is not proof that the artifact was captured or read.
4. Open the actual `ui.xml` for that attempt and inspect the tree. Record relevant node text/content-desc/resource-id, bounds, selected/focused/clickable state, parent/anchor relationship, and whether the XML is complete and parseable.
5. Open the matching `screen.png`/screenshot from the same attempt. Do not substitute a later screenshot, an Android Home/Launcher screenshot, or a screenshot from another attempt.
6. Compare the exact final evidence with the pre-action capture, last known-good capture, and manifest/recovery timeline. Mark each finding `confirmed`, `excluded`, or `unproven`.

## Fail-closed rules

- Missing XML, missing screenshot, nonexistent path, malformed/truncated XML, mismatched timestamp, or ambiguous attempt identity means `capture_artifact_missing` / `UNPROVEN`.
- Do not infer identity or screen from `texts[0]`, a generic marker, one parser field, a successful tap/ADB acknowledgement, a stale capture, or a later terminal image.
- Do not claim an XML or screenshot was inspected unless the exact file was actually opened.
- User correction (2026-09-03, avatar false-success): never declare avatar/profile upload complete from runner exit code, `verified=True`, or log line `Avatar upload thành công` alone. Those signals only prove the save tap happened; the TikTok CDN upload can still be cancelled by an early `adapter.back()` / `force-stop`. A success claim requires a fresh live re-open of the profile plus a fresh screenshot showing a non-placeholder avatar (photo content with high pixel variance, not default silhouette/camera icon). If the only post-run screenshot is blank/white, Home screen, or unread, report `UNPROVEN`, not success.
- When a user-supplied image arrives as unavailable (no vision-capable provider, placeholder text instead of pixels), explicitly state the image could not be seen and ask for re-upload/description. Never argue against the user's visible evidence or claim completion over an image that was never actually opened.
- Do not run recursive filesystem scans (`os.walk`, `find`, broad `glob`) over massive directories like `D:\\Taadaa` or `runtime`; directly address machine-scoped directories (e.g. `runtime/machines/machine_N`) with tight timeouts (<10s) to prevent terminal I/O hangs.
- **User correction (2026-09-02):** "mày lại bắt đầu đi quét grep toàn bộ thư mục r phải k" — when user explicitly stops a broad scan, immediately halt. Prefer targeted paths (`glob` with specific pattern, known file location) over exploratory sweeps. If the target file location is unknown, ask the user for the path instead of scanning.
- Do not widen recovery, cleanup, force-stop, BACK, HOME, retry, or live intervention while the evidence gate is incomplete. Stop and report the precise blocker.

## Capture implementation contract

Any script that captures UI for an error, blocker, mismatch, or recovery decision must persist the exact `ui.xml` and matching screenshot under the exact attempt artifact before identity parsing, classification, cleanup, or final reporting. `xml_available=true` is valid only when the actual XML file exists and the artifact status is complete. If either capture fails, emit a capture-invalid/incomplete result and preserve the scene.

When validating persisted screenshots (e.g. `screen.png`), a simple signature check (`startswith(PNG_SIGNATURE)`) is insufficient. The validator must strictly enforce: (1) `IHDR` is the first chunk and valid; (2) mandatory chunks like `PLTE` exist before `IDAT` for indexed color types; (3) all `IDAT` chunks are consecutive; (4) `IEND` is terminal; (5) valid CRCs; (6) successful zlib decompression with exact expected scanline bytes; and (7) valid filter bytes (`0..4`) per scanline. Missing or corrupted image data must fail-closed as incomplete artifact.

## Action verification

Before any tap, swipe, BACK, force-stop, HOME, recovery, or retry, read the available evidence and verify the intended target. After every state-changing action, capture fresh XML and screenshot and verify the post-condition from those fresh artifacts. A command return code is not UI success proof.

### Capture timing is part of behavior

Treat UI capture/dump calls as both evidence collection and possible synchronization points. When a regression follows a change that removes or moves screenshots/XML dumps, perform a differential history review before changing selectors:

1. Identify the exact commit and timestamp that changed capture frequency or placement.
2. Compare the pre/post call sequence, sleeps, retries, timeout budget, and state-transition boundaries.
3. Check whether the removed capture was the only wait before selector resolution or a post-action verification gate.
4. Reproduce the timing hypothesis offline with a fixture or mocked transition; do not infer causality from the incident screenshot alone.
5. Keep the conclusion split into `confirmed`, `plausible`, and `UNPROVEN` when the exact live attempt artifact is unavailable.

A capture can be causally relevant as a missing synchronization point without being proof of which UI node was tapped.

### Fail closed on semantic anchor resolution

For account/profile/navigation controls, never tap a node merely because it is a unique text header in the expected region. A generic header fallback may select a creator/profile, caption, bio action, username link, or stale transition node. Before tapping:

- Prefer a canonical semantic marker or canonical resource-id.
- If identity is known, require the resolved handle/display value to agree with the captured identity; reject an unrelated `@handle`.
- Reject generic text when identity is absent unless the node carries an explicit semantic/resource signal.
- Re-capture and resolve a fresh node after `BACK`, scroll, navigation, or any transition that can re-layout the header; do not reuse an old element/coordinate by default.
- Add a regression fixture containing a valid-looking creator/profile node beside the intended control, and assert that the creator node is not returned.

If no semantically verified target remains, stop with a bounded failure/manual-needed result rather than tapping a guessed coordinate.

### Offline incident mode

When live UI artifacts are missing, work only from source, Git history, and sanitized fixtures. Do not use ADB or relaunch/retry the live device to compensate. Mark the live root cause `UNPROVEN`, but it is still valid to prove a narrower code-level hazard by reproducing the selector/timing behavior offline. Report the exact missing artifact class (`ui.xml`, matching screenshot, or log window) and keep code-level evidence separate from live-incident evidence.

See `references/capture-timing-and-anchor-resolution.md` for the reusable differential-review and regression-fixture pattern.

## External-post and product-claim verification

When the artifact is a social-media post, screenshot, launch announcement, or product claim, apply a second evidence gate before endorsing it:

1. Transcribe only legible text from the image. Mark cropped, obscured, inferred, or OCR/vision-uncertain text explicitly.
2. Identify the canonical project from distinctive wording, repository search, package registry, or the publisher's direct link. Prefer the canonical repository/API over search snippets; if a search engine is blocked, query the provider API directly.
3. Compare the screenshot claims with the current README, repository metadata, configuration defaults, and implementation paths. Treat post text as a publisher claim until source evidence confirms it.
4. Separate **configured** from **reachable** and **working**: UI labels such as `Configured`, `Running`, `Not checked`, or `Missing key` are state labels, not proof of successful inference. Require a real model-list or inference request, HTTP status, and tool/streaming check for runtime claims.
5. Translate “free”, aggregate token totals, “unlimited”, and “ToS-friendly” into the actual mechanism: provider free tiers/credits, local inference, subscription OAuth, fallback routing, or a publisher assertion. Do not present an aggregate quota as a guaranteed user quota.
6. For proxies/routers, inspect default bind host/port, authentication defaults, secret and OAuth handling, outbound provider destinations, logging/redaction, installer download-and-execute behavior, and whether admin access is local-only. Report security exposure separately from feature compatibility.

Use `references/screenshot-product-claim-audit.md` for the reusable evidence matrix and report template.

## Component identity and causality

Before attributing a failure to another workflow, prove that the workflows share a resource or dependency. In particular, an independent downloader using its own command, runtime, log, and SQLite state DB must not be conflated with a concurrently running TikTok farm/account workflow merely because both exist on the same Windows host.

For every incident, record the failing component's exact command line, executable/module, working directory, config, log path, and state path. Classify other active processes as `unrelated context` unless evidence directly connects them through a shared file/database, lock holder, process parent, network endpoint, or explicit dependency. A generic "other Python process is running" observation is not causal evidence.

When the user asks about a specific component, stay scoped to that component. Do not broaden into farm operations, device safety, or restart-impact analysis unless the evidence shows a real interaction or the requested action would affect it. If an earlier explanation mixed components, correct it explicitly and concisely rather than repeating the irrelevant context.

## Reporting

Report concise facts, preferably in this form:

- `Mục đích`
- `Kết quả`
- `Bằng chứng`: exact path, timestamp, node/anchor/bounds/state
- `Confirmed / Excluded / Unproven`
- `Blocker`

Never replace missing evidence with a plausible explanation. Keep the answer scoped to the user's named component; do not pad it with unrelated active processes or workflows.

## Verification checklist

- [ ] Exact log window was read.
- [ ] Exact attempt `ui.xml` was opened and parsed/inspected.
- [ ] Matching screenshot was opened.
- [ ] Timeline and artifact identity match.
- [ ] Findings are labeled confirmed, excluded, or unproven.
- [ ] No action or conclusion bypassed the evidence gate.
- [ ] Missing evidence is reported as capture_artifact_missing/UNPROVEN.
