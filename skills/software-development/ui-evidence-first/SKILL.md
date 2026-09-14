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
- `references/false-success-newsletter-and-cloudflare-traps-20260913.md` — False-success claims on background actions & Cloudflare HTTP 200 traps: forbids claiming success from HTTP 200 or blank screen captures.
- `references/screenshot-product-claim-audit.md` — Evidence matrix and report template for external posts and product claims.
- `references/telegram-incoming-image-investigation.md` — Workflow for extracting, reading via local LLM vision endpoint, and verifying Telegram image attachments and farm alerts.
- `references/temporal-artifact-mismatch-offline-device.md` — Diagnostic protocol for 'image exists but device reported offline' due to temporal artifact mismatch between sessions.
- `references/trust-artifacts-not-summaries-claude-architect.md` — Kiến trúc chốt chặn 4 lớp "Trust Artifacts, Not Summaries": chống worker subagent tự suy diễn text "SUCCESS" khi script timeout âm thầm; bắt buộc gửi MEDIA:<path> lên Telegram để user đối chiếu.
- `references/uiautomator-popup-case-fixes.md` — Case Fix & Anti-Pattern catalog for UIAutomator, popup detection, and negative exclusions (mandatory reading per `docs/uiautomator.md`).
- `references/tap-coordinate-root-cause-misdiagnosis-20260909.md` — Tap coordinate fix is code-correct but root cause may be TikTok session/auth; canary proves/disproves. Always verify before committing.

## Scope

This is a global Hermes workflow for **every repository and every script**: flows, workers, schedulers, recovery, popup handling, login, registration, upload, follow, feed, device automation, tests, and incident investigation. It is not limited to TikTok or profile verification.

## Mandatory evidence gate

### Quy tắc Bắt Buộc Đọc Log Tại Nguồn (CẤM Suy Đoán Theo Exit Code / Quá Khứ)
Khi một lệnh, batch run, feed session hoặc canary test thất bại (exit code non-zero hoặc status manual-needed/fail):
1. **Turn 1 BẮT BUỘC đọc file log thực tế (`summary.txt` / `log.jsonl`):** Dùng `read_file` mở trực tiếp artifact log trong thư mục `.ai-runs` / run artifact vừa sinh ra và trích dẫn dòng lỗi thực tế (`reason`, `stop_reason`, traceback) trước khi đưa ra bất kỳ nhận định hoặc hành động sửa code nào.
2. **CẤM suy đoán dựa trên triệu chứng/lỗi cũ:** Tuyệt đối không được lấy lỗi của các phiên trước đó (ví dụ: phiên trước bị `ATX_SESSION_UNAVAILABLE` thì phiên này vội quy kết do ATX/thiết bị treo) để giải thích cho phiên hiện tại khi chưa kiểm tra log mới.
3. **Phân loại blocker bằng bằng chứng log thật:** Trích xuất nguyên văn dòng lỗi từ log để định vị chính xác nguyên nhân (như gate cohort mismatch, missing CLI flags, device lock conflict...) thay vì phỏng đoán cảm tính.

## Fix báo lỗi máy = Sửa script toàn cục (CẤM fix tay)
Khi user yêu cầu fix lỗi trên máy N (kèm ảnh chụp/alert/log):
1. **Trích xuất hiện trường nhanh (CẤM GREP / CẤM QUÉT ĐĨA):**
   - Chạy duy nhất `python D:/Taadaa/tools/inspect_machine.py <N>` hoặc kiểm tra ADB trực tiếp theo serial.
   - TUYỆT ĐỐI CẤM dùng `os.walk`, `glob(recursive=True)`, `find`, `grep -rn` quét diện rộng codebase hay ổ đĩa để tìm chuỗi lỗi / file log.
2. **Hiện trường máy là Read-Only Evidence & Phân vai Bắt buộc (Coordinator vs Worker):**
   - Trạng thái, màn hình và XML trên máy N chỉ dùng để trích xuất bằng chứng phân tích root cause.
   - Session chính LÀ COORDINATOR: CHỈ đọc log, trích xuất hiện trường O(1) (XML + screencap), phân tích phạm vi lỗi rồi BẮT BUỘC dispatch worker subagent qua `delegate_task(goal=..., context=...)` ngay lập tức.
   - CẤM TUYỆT ĐỐI Coordinator tự viết script Python probe, test hàm, reproduce thử nghiệm hay sửa code trực tiếp trong terminal ở session chính (tránh bloat context và vi phạm kỷ luật phân vai).
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
- **CRITICAL ANTI-PATTERN — CẤM TUYỆT ĐỐI `pm clear` TRÊN TOÀN BỘ FARM:** Tuyệt đối CẤM dùng lệnh `pm clear <package>` (đặc biệt là TikTok `com.ss.android.ugc.trill` / `com.zhiliaoapp.musically`) khi app bị lag, kẹt splash hoặc lỗi cài đặt. `pm clear` xóa toàn bộ dữ liệu ứng dụng (`/data/data`), hủy sạch auth/session tokens, làm văng toàn bộ tài khoản đăng nhập trên thiết bị. Khi nâng cấp hoặc sửa lỗi Split APK, BẮT BUỘC CHỈ dùng `adb install-multiple -r -d base.apk [splits...]` để giữ nguyên 100% token đăng nhập, kết hợp `am force-stop` + `input keyevent 3` (HOME).
- User correction (2026-09-03, avatar false-success): never declare avatar/profile upload complete from runner exit code, `verified=True`, or log line `Avatar upload thành công` alone. Those signals only prove the save tap happened; the TikTok CDN upload can still be cancelled by an early `adapter.back()` / `force-stop`. A success claim requires a fresh live re-open of the profile plus a fresh screenshot showing a non-placeholder avatar (photo content with high pixel variance, not default silhouette/camera icon). If the only post-run screenshot is blank/white, Home screen, or unread, report `UNPROVEN`, not success.
- **User correction (2026-09-06, GPM/Device false-success & Epistemic Trust):** Never trust free-text summaries ("SUCCESS") from worker subagents for UI/login/device tasks. When scripts timeout or fail silently without raising an exception (exit 0), worker LLMs frequently hallucinate success while the screen remains stuck on error/recovery pages (e.g. "Khôi phục tài khoản"). Apply the 4-layer enforcement rule ("Trust Artifacts, Not Summaries"):
  1. *Script level:* Always capture a terminal screenshot in a `finally:` block and print `SCREENSHOT_SAVED: <abs_path>` + `FINAL_URL:` to stdout.
  2. *Artifact Contract:* Require worker tasks to return a valid physical screenshot path; missing or nonexistent path = immediate `FAILED_NO_EVIDENCE`.
  3. *Coordinator Verification Gate:* Coordinator must verify the image file exists, timestamp is fresh (<=60s), and perform quick OCR/sanity check against target URL/state before reporting success.
  4. *Telegram Media Delivery:* Coordinator MUST deliver the physical screenshot via `MEDIA:<path>` to Telegram so the user can inspect with their own eyes. Never report completion with text-only summaries.
- **User correction (2026-09-08, Account Switcher proof vs Settings page):** When verifying account state, login/logout, or multi-account inventory on TikTok/mobile apps, NEVER present a screenshot of "Settings and privacy" (`Cài đặt và quyền riêng tư`) or confirmation popups as proof of completion. Those screens only prove an action was triggered; they do not prove which accounts remain active or that unwanted accounts were removed. Verification proof MUST be captured from the live **Account Switcher** (`Chuyển đổi tài khoản` bottom sheet) showing the full account list and active states.
- **User correction (2026-09-12, CẤM Đoán Mò / Điền Bậy Password Khi Bị Mất Session RAM):** TUYỆT ĐỐI CẤM agent tự suy diễn, phỏng đoán công thức password hoặc điền giá trị chưa được kiểm chứng vào workbook / production Excel (`gmail_clean_v2.xlsx`, `taikhoan_dat_v2_updated .xlsx`, etc.). Khi script chạy đơn lẻ không lưu password và tiến trình RAM đã thoát:
  1. Thừa nhận trung thực ngay lập tức là không lấy lại được password do thiếu cơ chế lưu (`--result-dir`).
  2. BÁO CÁO RÕ RÀNG cho user để gỡ tài khoản rác/mất pass khỏi thiết bị và dọn hàng Excel.
  3. BẮT BUỘC vá mã nguồn (hàm `persist_success_result`) để có fallback lưu trực tiếp vào Excel khi không có `--result-dir`, bảo vệ dữ liệu cho các lần chạy sau. CẤM TUYỆT ĐỐI bịa pass điền vào file production.
- **User correction (2026-09-13, Báo cáo ảo newsletter/action và bắt buộc bằng chứng hiện trường):** TUYỆT ĐỐI CẤM agent/subagent tự nhận hành động thành công (như "đã subscribe thành công", "đã bấm nút", "đã hoàn tất") chỉ dựa trên: (1) HTTP status 200 từ request Python/urllib (thực chất là trang Cloudflare challenge chặn bot hoặc redirect trống); (2) Script/Subagent report text mà không có ảnh bằng chứng màn hình xác nhận sau submit.
  - Khi user hỏi bằng chứng ("Nút subscribe bằng chứng đâu?", "Hình đâu?"): BẮT BUỘC cung cấp ảnh chụp màn hình thật chứa nội dung kết quả thực tế (thư rớt vào inbox, thông báo thành công trên trang, hoặc màn hình lỗi thật). CẤM gửi ảnh màn hình trắng, ảnh treo load, hoặc ảnh không chứa bằng chứng của hành động mà tự nhận là xong.
  - Nếu hành động chưa có bằng chứng hoặc thất bại: PHẢI THỪA NHẬN THẲNG THẮN NGAY LẬP TỨC, tuyệt đối không bao biện hoặc tạo ảo giác đã hoàn thành.
- **User correction (2026-09-14, Báo cáo lỗi dịch vụ/job nào thì nghiệm thu ảnh dịch vụ/job đó — CẤM gửi nhầm ảnh S7 thay cho GPM/Web):**
  Khi báo cáo kết quả khắc phục hoặc điều tra lỗi của một dịch vụ/nền tảng cụ thể (như GPM browser, ChatGPT web, OmniRoute, yt-dlp, web scraping...):
  1. Bằng chứng nghiệm thu hình ảnh (`MEDIA:<path>`) BẮT BUỘC phải trích xuất từ đúng môi trường của dịch vụ đó (ví dụ: screenshot Chromium/GPM profile bị lỗi/thành công trong `D:/Taadaa/GPM auto/debug_screenshots/`, web UI của OmniRoute :20129...).
  2. TUYỆT ĐỐI CẤM thói quen máy móc lấy screencap từ điện thoại Android/S7 qua ADB để đính kèm cho một job hoàn toàn thuộc về GPM/Browser trên PC. Bằng chứng sai môi trường bị coi là vi phạm Gate nghiệm thu ảnh.
- **User correction (2026-09-14, CẤM BỊA NGUYÊN NHÂN KHI CÓ EVIDENCE ẢNH — HERMES EVIDENCE PROTOCOL INVARIANT GATE):**
  TUYỆT ĐỐI CẤM agent tự suy diễn, đoán mò các nguyên nhân phổ biến (nghẽn mạng, proxy timeout, server lag, cookie hết hạn...) khi có ảnh/screenshot hiện trường mà CHƯA THỰC SỰ ĐỌC ẢNH:
  1. *Zero Assumption:* Cấm kết luận nguyên nhân trước khi trích xuất text từ ảnh.
  2. *Mandatory OCR / Verbatim Extraction:* BẮT BUỘC phải chạy OCR (ví dụ WinRT OCR qua `windows-native-ocr`) hoặc dump XML, trích xuất text thực tế từ ảnh. Báo cáo chẩn đoán BẮT BUỘC phải trích dẫn nguyên văn (verbatim quote) ≥ 1 dòng text thực tế từ màn hình. Định dạng: `Theo OCR: '<text trích dẫn>' → Kết luận: <nguyên nhân>`.
  3. *Contradiction Circuit Breaker:* Tự đối chiếu kết luận với text OCR. Nếu kết luận mâu thuẫn với chữ trên màn hình (như ảnh thể hiện đòi xác minh SĐT nhưng báo cáo là nghẽn mạng), báo cáo bị coi là VÔ GIÁ TRỊ, kích hoạt Circuit Breaker hủy bỏ kết luận cũ và viết lại trung thực theo đúng chữ trên ảnh.
  4. *Google Challenge SĐT đuôi 24:* SĐT đuôi 24 là số cá nhân của user Tad. Khi gặp màn hình Google Identity Verification đòi mã xác minh gửi về số đuôi 24, dừng automation và gọi user lấy mã OTP, CẤM cố retry tự động.

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
- **Do not tap full-width container center for list/sheet item selection:** When selecting an item from a list or modal sheet (e.g. TikTok account switcher rows `id/l9b` or `id/lpw` in 46.8.3 spanning `[0, 1080]`), taking `bounds.center` (`x=540`) can land in dead whitespace past the text (`id/mtx` or `id/nba` ending at ~542) if the row is not a clickable button. However, **BEWARE the non-clickable child view trap (Samsung S7 / Máy 8 & Máy 46):** if the container `id/lpw` is `clickable="true"` but the inner `TextView` `id/nba` has `clickable="false"`, an `adb shell input tap` targeting the inner child (`center x=397`) will be swallowed without triggering the parent's click listener! Always prefer ATX JSON-RPC `click([x, y])` or synthetic touch on the clickable container. If using ADB input tap, ensure the targeted node is actually `clickable="true"`.
- **Active item tap in bottom sheets does not dismiss:** In the TikTok account switcher, tapping an account that is already active (marked with `Dấu kiểm` `id/fmc`) will NOT dismiss or close the switcher sheet. The sheet remains open until explicitly dismissed via the "Đóng" button or `BACK` key.
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
