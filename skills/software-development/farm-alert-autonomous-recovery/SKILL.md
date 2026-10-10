---
name: farm-alert-autonomous-recovery
description: >-
  Autonomous Taadaa Farm Alert handling from evidence through scoped fix,
  focused verification, bounded canary, and exact-scope closeout.
---

# Farm Alert Autonomous Recovery

> 📎 Ref: `references/midday-shift-feed-triage-and-dual-cluster-auto-healing-20261010.md` (**[10/10/2026]** Midday triage & auto-heal).
> 📎 Ref: `references/one-tap-welcome-back-guard-bypass-and-auto-login-trap-20261010.md`, `references/admin-cluster-batch-feed-triage-and-missing-session-onetap-20261010.md`.
> 📎 Ref: `references/scheduled-pc-reboot-preflight-abort-triage-20261010.md`, `references/feed-suggestion-xoa-and-scrolled-profile-triage-20261009.md`.
> 📎 Ref: `references/preflight-reg-bu-machine-full-reconcile-pipeline-20261008.md`, `references/anti-skip-physical-hook-gate-discipline-20261004.md`.
> 📎 Ref: `references/avatar-edit-layout-detector-and-closeout-contract.md`, `references/feed-failure-taxonomy-and-guard-boundary.md`.

## 🛑 QUY TẮC BẰNG CHỨNG HÌNH ẢNH: CẤM GỬI ẢNH MÀN HÌNH HOME/LAUNCHER
- User duyệt hiện trường qua `MEDIA:<path>`. **CẤM TUYỆT ĐỐI** gửi ảnh màn hình Home/Launcher Android làm bằng chứng sau teardown/khi lỗi.
- Bắt buộc chụp ảnh in-app thực tế (Profile, Settings, Popup, Dialog, Switcher) TRƯỚC KHI teardown/force-stop.

## 🛑 TRIAGE LỖI CÁP VẬT LÝ ADB (CM_PROB_PHANTOM)
- Khi nhận alert máy offline / `[01_open]` mà ADB báo `device not found` hoặc `offline`:
  Chạy ngay lệnh PowerShell trên host:
  `Get-PnpDevice | Where-Object { $_.InstanceId -like "*<serial>*" } | Select-Object FriendlyName, Status, Present, Problem`
- Nếu `Present: False` hoặc `Problem: CM_PROB_PHANTOM`: Đây là lỗi cáp USB/sập nguồn vật lý. DỪNG NGAY mọi loop retry hoặc sửa code, chuyển L3 BLOCKED và báo chủ farm kiểm tra cáp tại rack.

## QUY CHUẨN THIẾT KẾ WATCHDOG & BÁO CÁO ĐỊNH KỲ (CHỐNG SPAM ALERT)
Mọi cronjob / watchdog / script tự động (cũ lẫn mới tạo) bắt buộc tuân thủ nghiêm ngặt:
1. **Auto-Healer / Maintenance Watchdog (Ngầm):** Cấu hình `deliver: "local"`. Áp dụng Silent Pattern: khi bình thường hoặc tự sửa/tự vá thành công -> ghi log ngầm vào file `D:\Taadaa\runtime\...`, **`stdout` BẮT BUỘC RỖNG 100% (`sys.exit(0)`)**. CẤM TUYỆT ĐỐI dùng `print()` thông báo kết quả thành công để tránh kích hoạt Hermes gửi tin nhắn spam về Telegram. Chỉ in ra `stdout` khi gặp lỗi nghiêm trọng (`errors`) không thể tự sửa cần người can thiệp. Giãn nhịp cron hợp lý (cuối ngày hoặc theo ca, tránh `*/5`).
2. **Scheduled Summary Report (Định kỳ):** Chỉ gửi đúng kênh chỉ định vào đúng khung giờ quy định (kết thúc ca, 6h/lần, 07:00 sáng). BẮT BUỘC chuẩn hóa schema: Header rõ ràng, số liệu tổng hợp (Tổng | Pass | Fail | Tỷ lệ %), danh sách cô đọng. CẤM dump raw log/terminal hoặc xả chi tiết vụn vặt.
3. Chi tiết xem tại: `references/watchdog-silent-and-reporting-standard.md` và `references/adb-transport-two-phase-healing.md`.

## Trigger and state machine

Use for `[MÁY N]` alerts, batch failure summaries, and explicit requests to recover farm automation.

### Alert scope gate (mandatory)

- **KỶ LUẬT PHẢN HỒI ĐIỀU PHỐI (CHỐNG ĐỨNG IM / "OK" VÔ NGHĨA)**:
  Khi nhận Farm Alert hoặc chỉ thị từ User, CẤM TUYỆT ĐỐI chỉ phản hồi cụt ngủn ("OK", "Đã nhận", "Vâng") rồi đứng im không hành động. Mục tiêu tối thượng là đưa task về DONE hoặc BLOCKED kèm bằng chứng thực tế. Ngay lập tức parse scope, phân loại fingerprint lỗi, kiểm tra hiện trường O(1) và kích hoạt luồng khắc phục.

- **KỶ LUẬT XỬ LÝ FALSE ALERT (CHỐNG BẪY "BẢO USER BỎ QUA" / TELL-TO-IGNORE ANTI-PATTERN)**:
  Khi phát hiện một Farm Alert bị báo nhầm (False Alert — ví dụ S7 Security Code bị nhận nhầm thành SMS OTP đuôi 24, hoặc tài khoản dính popup phụ bị gán nhãn mất phiên):
  CẤM TUYỆT ĐỐI chỉ giải thích lý thuyết rồi dặn User *"Sếp bỏ qua alert đó, không cần làm gì"* rồi dừng lại!
  Lý do: Alert sai đồng nghĩa với việc pipeline đang bị kẹt hoặc tài khoản bị ghi nhận nhầm vào file cờ chờ (`waiting_otp.json`) hoặc bị gán oan cooldown (`RATE_LIMIT_SMS_PHONE_24`, `cooldown_7days`). Bảo User bỏ qua là bỏ rơi tài khoản và đùn đẩy trách nhiệm.
  BẮT BUỘC THỰC THI TRỌN GÓI A-Z:
  1. Ngay lập tức kiểm tra hiện trường thiết bị thật / browser profile.
  2. Khắc phục tận gốc nguyên nhân kẹt (nếu S7 hết hạn phiên: tự động điền mật khẩu khôi phục phiên; nếu sai selector: patch code và tự động trích xuất mã/token để vượt challenge).
  3. Hoàn tất luồng xác thực trên browser/app, chụp ảnh nghiệm thu thị giác (`MEDIA:`).
  4. Dọn sạch file cờ tạm và xóa bỏ trạng thái cooldown gán nhầm trong file cấu hình (`oauth_pipeline_status.json`).

- **KỶ LUẬT THỰC THI "FIX ĐI" (PIPELINE A-Z KHÉP KÍN: CANARY -> CLOSEOUT NGẦM -> CHỜ USER DUYỆT ẢNH MỚI PUSH)**:
  Khi User ra lệnh "Fix đi để k bị lại" hoặc yêu cầu fix triệt để lỗi farm: CẤM TUYỆT ĐỐI chỉ phân tích lý thuyết hay dừng lại sau khi sửa file offline. BẮT BUỘC thực hiện đúng 5 bước Pipeline A-Z (tham chiếu chi tiết `references/canary-first-closeout-pipeline.md`):
  1. **Fix code & Unit test focused < 30s**: Sửa lỗi tận gốc, pass test, commit LOCAL (CẤM push remote).
  2. **TỰ ĐỘNG chạy Canary máy thật**: Acquire device lock -> chạy trên 1 máy thật đại diện -> chụp ảnh `MEDIA:<path>` -> **Tự chạy WinRT OCR đọc text ảnh** (OCR Readback Gate). PASS/FAIL chỉ kết luận từ text OCR, cấm suy đoán từ log.
  3. **TỰ ĐỘNG chạy Closeout Gate ngầm**: `python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base $(git merge-base HEAD '@{u}' 2>/dev/null || git merge-base HEAD origin/main) --json-output`. Reviewer Sol High chấm >= 85 và exit 0 mới qua. Nếu < 85: tự sửa ngầm (tối đa 3 vòng lặp), KHÔNG báo User. Nhả device lock ngay sau khi Canary chụp ảnh và OCR xong.
  4. **Báo cáo nghiệm thu trọn gói (Gửi 1 lần duy nhất)**: Gồm Ảnh `MEDIA:` + Text OCR đọc được + Điểm Reviewer (>=85) + Commit SHA + Diffstat. Sau đó giải phóng device lock và session.
  5. **Quyền Push Remote thuộc về User**: CHỈ KHI User xem ảnh và gõ lệnh (`chốt`, `chốt phiên`, `done`, `ok` khi trả lời báo cáo nghiệm thu) thì Agent mới được `git push` remote và tuyên bố hoàn tất phiên. CẤM TUYỆT ĐỐI tự động push remote khi User chưa xem ảnh duyệt!

- **KỶ LUẬT THỰC THI KHI GẶP LỖ HỔNG MAPPING (CHỐNG DỪNG BÁO CÁO MAPPING LỆCH)**:
  Khi chạy `ensure_row_accounts.py <row>` mà runner báo "Toàn bộ máy đã đầy đủ tài khoản! Không cần reg" (false full / false skip) do mapping slot trong `taikhoan_run_safe.xlsx` bị nhảy cóc/lệch hàng (gapped slot mapping):
  CẤM TUYỆT ĐỐI dừng lại để giải thích lý thuyết về mapping lệch hay hỏi User có sửa không (tránh kích hoạt phản ứng tiêu cực "Fix cho tao đkm mapping óc chó v").
  BẮT BUỘC CHỦ ĐỘNG:
  1. Chuẩn hóa dồn toa Contiguous Slot Packing ngay trong `taikhoan_run_safe.xlsx` (dồn K nick có thật vào Slot 1..K, dồn ô trống về Slot K+1..8).
  2. Cách ly email lỗi (nếu có email bị TikTok từ chối do đã tồn tại bên ngoài) bằng cách set cột 11 `trạng thái = 'used'` trong `gmail_clean_v2.xlsx`.
  3. Chạy ngay `ensure_row_accounts.py <K+1> --machines <STT>` để hoàn tất đăng ký nick còn thiếu.
  4. Báo cáo kết quả cuối cùng kèm bằng chứng thị giác (`MEDIA:`).

A batch total is **statistics, not an action scope**. Parse every alert into two explicit sets before acting:

- `ACTION_SCOPE`: only machine IDs explicitly named as affected or proven by their own fresh log/artifact fingerprint.
- `NO_TOUCH_SCOPE`: successful, unmentioned, or unrelated machines; do not stop, lock, retry, or reopen them.

When an alert provides only aggregate counts (e.g. "160 total / 39 failures") without machine IDs in the prompt text:
1. Do not halt at an abstract refusal report or ask the user to provide machine IDs before inspecting runtime artifacts.
2. Immediately check the current date's active run manifests: `D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/*/*/run_manifest.json`.
3. Extract the exact list of failed machines (`final_status != success/degraded`) and categorize by blocker taxonomy (`script-blocker`, `manual-needed-popup`, `login-gms-verification`, `proxy-vpn`, `focus-device-issue`).
4. Identify any actionable code/watchdog/test defects (e.g. reconciliation delta calculations, mock fixture counts), perform focused surgery/dispatch, verify with tests, pass closeout gate, and push.
5. Present concise, structured machine categorization to the user instead of abstract scope refusals. If no matching manifests exist for the current date after checking targeted runtime paths, only then classify as `UNPROVEN / NO RUN ARTIFACT FOUND`.

Never perform recursive filesystem scans (`os.walk`, `grep -r`, `find`, recursive `glob(..., recursive=True)`) across farm repositories or `D:/Taadaa/runtime/**`. Heavy `.ai-runs`, quarantined runs, virtualenvs, test caches, and thousands of runtime XML/screenshot dumps cause 600s terminal timeouts. Inspect only targeted directories by exact date and depth (e.g. `.ai-runs/YYYYMMDD*`, `D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/*/*/run_manifest.json` with explicit date filter, or state files under `cron-state/`). Never use `**` across `D:/Taadaa/runtime`. When an aggregate batch alert does not name machine IDs, do not attempt to scan historical manifests across dates to guess the machines; report machine IDs as `UNKNOWN`, `ACTION_SCOPE: NONE`, and verify current machine state O(1) via `inspect_machine.py` (hỗ trợ cả định dạng `python D:/Taadaa/tools/inspect_machine.py M<N>` lẫn `<N>`).

Every report must state `ACTION_SCOPE` and `NO_TOUCH_SCOPE`. “Batch locked” may only be reported when an actual batch-control action was executed and evidenced; otherwise say `NO GLOBAL STOP ACTION.` Do not use vague shorthand such as “fleet”, “batch locked”, or “reopen the fleet” without naming the exact machine set and whether a real control action occurred. Keep the user-facing scope explanation short and concrete; distinguish `observed`, `authorized target`, and `not touched`.

### Required first-pass alert parse

Before any tool action, render the alert as:

```text
BATCH_CONTEXT: totals/statistics only
ACTION_SCOPE: explicitly named machines or machines proven by fresh per-machine evidence
PENDING_SCOPE: failures without their own log/artifact classification
NO_TOUCH_SCOPE: successful, unmentioned, and unrelated machines
CANARY_SCOPE: the one named canary and only its proven matching fingerprint group
GLOBAL_STOP_ACTION: NONE unless an actual control command was executed and evidenced
```

A prior mistaken interpretation must be corrected by changing the operational contract, not by asking the user to rewrite the alert. The alert already contains enough scope when it names machines; do not let batch totals override those names.

### Login/feed handoff triage (mandatory)

Do not equate a feed consumer's `login/account screen detected` with “the login runner failed” or “login was not run.” First distinguish: (a) login runner invocation and result, (b) post-login/session handoff evidence, and (c) feed's current UI classification. Read the exact artifact and XML before concluding. When the classifier emits a canonical field such as `detected=manual-needed:login` but `reason` is human text such as `login/account screen detected`, route recovery from the canonical classification field—not a prefix test on the human reason. Preserve exact reason/artifact and fail closed for non-login states. A proven login-state routing defect requires a focused mocked regression before another live canary.

Every incident report must label `LOGIN_INVOKED`, `LOGIN_RESULT_EVIDENCE`, `FEED_UI_STATE`, and `HANDOFF_STATUS` as confirmed or unknown; never infer one from another.

When recovery falls back from feed to a machine-scoped reconcile, propagate the complete target identity: `expected_username`, physical `source_row`, `account_row_index`, and serial when available. A machine may contain multiple accounts; never allow a fallback receiving only `--machines N` to select an arbitrary account. Require an explicit target or fail closed on ambiguous machine-wide inventory. Report separately: `fast_login invoked`, `fast_login result`, `fallback target`, `fallback result`, and `post-recovery verification`. Do not “fix” a missing target by supplying credentials for another account on the same machine.

```text
ALERT → SCOPE_PARSE → EVIDENCE → CLASSIFY → WORKER → VERIFY → CANARY → DONE/BLOCKED
```

`DONE` requires real test/artifact/canary evidence. `BLOCKED` is valid only after the applicable recovery ladder is exhausted or a genuine credential, business/ownership, irreversible/paid, or exhausted-escalation gate is reached. Diagnosis alone is never terminal.

## A–Z operating sequence

1. Resolve the exact cluster/host, machine, serial, row/account, runner, and current run artifact. Do not guess mappings or scan the farm broadly.
2. Read the bounded log window and the exact matching XML/screenshot/artifact. Label facts `CONFIRMED`, `EXCLUDED`, or `UNPROVEN`.
3. Group machines by error fingerprint. Separate code surgery, infrastructure recovery, runtime/canary, and long batch work.
4. Dispatch a worker with an exact allowlist, anchor, acceptance check, non-goals, and timeout lane. Worker completion is a claim; independently inspect status, diff/numstat, focused test output, and artifacts.
5. Run the canonical runner for one bounded canary after offline verification. Re-resolve host/mapping before live action.
6. Continue other independent targets while a long process runs through an event-driven background launcher. Do not poll blindly. When a target device lock is held by a live owner, never wait or poll within the agent; if an incident supervisor is not yet upgraded, return a precise handoff state without touching the stub, launch only an existing supported detached status monitor, emit `next_action=monitor <target>`, and exit within budget. Never kill, force-preempt, delete active locks, or run canaries against locked devices.

## Recovery ladder

- **R1 transient:** one retry per error signature with explicit timeout/backoff and fresh evidence. Network/worker transport timeout does not consume the structural breaker.
- **R2 structural:** redispatch once with a materially different `contract_delta` (hypothesis, scope, acceptance, handler/model). Never repeat the same prompt/contract.
- **R3 exact surgery:** only with proven exact diff and bounded allowlist/budget; verify immediately and use no device in offline tests. Never bypass asset, credential, lock, or logout guards.
- **R4 pivot:** if the blocker is wrong host, mapping, or runner, pivot only through canonical sources; re-prove target identity.

### Common Alert Error Signatures & Triage Paths

- `[Google OAuth/2FA: S7 Security Code vs Phone 24 SMS False Alert Trap & Anti-False-Alert Gate]`:
  * **Hiện tượng**: Telegram Farm Alert bắn `⚠️ [FARM ALERT] [MÁY N] 📱 Google gửi mã xác minh SMS về SĐT đuôi 24 (Tad)! Vui lòng nhắn/nhập mã OTP 6 số (hạn 180s)`. Trong khi đó màn hình GPM browser thực chất là Google yêu cầu mã bảo mật thiết bị S7 (*"Verify it’s you: Get your Galaxy S7 -> Settings -> Google -> Manage your Google Account -> Security -> Security code"*).
  * **Căn nguyên cốt lõi**:
    1. Ô nhập Security Code ngoại tuyến mang thuộc tính `name="Pin"`, trùng selector với ô SMS OTP lỏng lẻo (`input#idvPin, input[name="Pin"]`).
    2. Trong màn hình `challenge/selection`, selector SĐT 24 được xếp trước S7 Prompt và S7 Security Code, khiến bot chủ động chọn SMS 24 làm phiền User và gây rate limit.
  * **Kỷ luật xử lý O(1) & Khắc phục triệt để**:
    1. **Anti-False-Alert Gate & Regex Word Boundary**: CẤM TUYỆT ĐỐI gọi `send_telegram_otp_alert` nếu thiếu positive proof (`is_real_sms_24`). Bắt buộc thỏa mãn đồng thời: `not is_s7_sec` VÀ (`"24"` in body hoặc `"••24"` in body) VÀ regex word boundary `re.search(r"(tin nhắn|text message|gửi mã|verification code|mã xác minh|\bsms\b)", body)` (tránh bẫy substring false match).
    2. **Đảo ngược thứ tự ưu tiên & Kiến trúc 2 tầng (detect_challenge_options + classify_s7_challenge_selection)**: Tách lớp quét locator ra khỏi hàm xử lý lớn; gom thứ tự ưu tiên: Google Authenticator (TOTP) -> Google Prompt S7 ("Nhấn vào Có") -> S7 Security Code (10 số) -> SIM Farm -> SĐT đuôi 24 của Tad (CHỈ khi không còn cách nào khác).
    3. **Điều hướng S7 qua Account Card Popup & Chống Shell Injection**: Google Play Services mới trên S7 giấu nút "Tài khoản Google" bên trong popup tài khoản (`[60,758][204,902]`). Bắt buộc tap thẻ tài khoản trước khi tìm nút "Tài khoản Google". Nếu gặp màn hình hết hạn phiên trên S7, tự động điền mật khẩu từ sổ cái để phục hồi. LƯU Ý BẢO MẬT: Bắt buộc truyền mật khẩu dạng argv rời (`[ADB_EXE, "-s", serial, "shell", "input", "text", pwd]`), TUYỆT ĐỐI CẤM ghép chuỗi shell command (tránh lỗ hổng shell injection khi mật khẩu có ký tự đặc biệt).
    4. **Fail-safe S7 & Tiêu Chuẩn Closeout Gate**: Không lấy được mã S7 thì bấm "More ways to verify" hoặc exit `BLOCKED_S7_CODE_FAILED` kèm structured telemetry (`event=s7_security_code status=BLOCKED_S7_CODE_FAILED reason=... correlation_id=...`) và JSON metric sink (`log_telemetry_metric`), CẤM TUYỆT ĐỐI nhảy trôi sang alert đòi SMS 24. Trong `detect_challenge_options`, bọc kiểm tra DOM locator trong `try...except` (`_is_loc_ready`) để phòng ngừa Playwright exception khi DOM render động. Commit L2/code surgery chỉ bao gồm code và test (bao phủ cả edge case rỗng/None, error branch, unmounted locators và mock page mapping), TUYỆT ĐỐI CẤM trộn lẫn việc xóa/sửa file config trạng thái (`oauth_pipeline_status.json`) vào chung commit để tránh bị reviewer Closeout Gate đánh rớt. Chi tiết: `gmail-account-automation/references/gmail-soak-aging-session-recovery-and-s7-safety-rules.md`.
- `[follow-timeout / Mode 1 Search Deadline Reserve Gap]`:
  * **Hiện tượng**: Farm alert báo `[MÁY N] follow-timeout`, `follow_result.json` ghi `"status": "timeout", "reason": "follow-timeout"` dù máy không bị treo UI, tiến trình cha văng `subprocess.TimeoutExpired` chạm trần 1200s (20 phút).
  * **Căn nguyên cốt lõi**: Mỗi lượt tìm kiếm UID + kiểm tra profile trong Mode 1 ngốn trung bình 60–75s (mở tìm kiếm, gõ UID, chờ kết quả, vào profile, kiểm tra quan hệ). Nếu `reserve_seconds` trong `has_time_for_next_action` chỉ đặt 60s, runner sẽ tiếp tục bốc thêm UID mới khi thời gian còn lại < 60s, dẫn đến quá giờ hard deadline 1200s của tiến trình cha trước khi kịp hoàn tất và chốt kết quả.
  * **Xử lý O(1)**: Đặt `reserve_seconds >= 120.0s` trong cả `follow_engine.py` và `mode1_search_follow.py` (và 180s cho Mode 2). Khi còn dưới 120s, engine sẽ hoàn tất phiên nhẹ nhàng (graceful exit), lưu `follow_result.json` trạng thái `OK` và trả quyền điều khiển về cho runner thay vì bị kill bởi timeout.
- `[Screencap on Sleeping Devices (12KB Black Frame Trap) & Settle Time]`:
  * **Hiện tượng**: Lệnh `exec-out screencap -p` khi máy đang Sleep/Dozing trả về file ảnh đúng 12,491 bytes (ảnh đen rỗng do frame buffer màn hình chưa bật).
  * **Triage & Xử lý chuẩn**: Khi chụp ảnh nghiệm thu máy đang tắt màn hình, BẮT BUỘC: (1) Bật màn hình qua `adb shell input keyevent 224`, (2) **Sleep tối thiểu 1.0s** để GPU/display driver kịp render frame (chờ 0.3s vẫn bị bẫy 12KB trên dòng Exynos SM-G930K/L/S), (3) Chụp `exec-out screencap -p`, (4) Tắt lại màn hình qua `adb shell input keyevent 223` để dưỡng pin máy.
- `[7c] Không lấy được OTP từ <email> / Graph API Zero Messages Timeout (Dead Mailbox vs TikTok Silent Drop)`:
  * **Bản chất kỹ thuật**: Token Microsoft Graph OAuth2 hợp lệ (`verify_graph_token == True`) nhưng mailbox không nhận được thư ngoại bộ từ TikTok (Inbox & Junk `totalItemCount = 0`). Cần phân biệt rõ qua thực nghiệm gửi mail nội bộ/chéo: nếu hòm thư vẫn nhận bình thường thì mailbox 100% không hỏng, mà do **TikTok Risk Engine "Silent Drop"** (app báo đã gửi nhưng backend TikTok âm thầm hủy/drop lệnh gửi OTP hoặc MTA bị chặn ngầm).
  * **BẪY TỬ HUYỆT BLACKLIST EMAIL TIMEOUT OTP (CHỐNG COOK OAN TÀI SẢN MAIL CỦA FARM)**: `registered_emails_blacklist.json` là blacklist vĩnh viễn DÀNH RIÊNG cho email **ĐÃ ĐĂNG KÝ TIKTOK THÀNH CÔNG**. Một email dính timeout OTP CHƯA hề có nick TikTok, hòm thư vẫn sống bình thường. TUYỆT ĐỐI CẤM gọi `record_registered_email_blacklist(email)` khi chỉ mới dính timeout OTP `[7c]` (làm vứt bỏ tài sản mail đã bỏ tiền ra mua).
  * **Xử lý O(1) & Kỷ luật sửa code**: Trong `social_reg_v1.py`, khi hết timeout OTP chỉ lưu UI XML/screenshot hiện trường và phát structured telemetry `[telemetry][otp_timeout] provider=microsoft email={email} reason=mailbox_otp_not_received`. Với mailbox chưa nhận được thư lúc này, bảo toàn trạng thái trong `gmail_clean_v2.xlsx` hoặc chuyển xuống cuối hàng đợi chờ retry sau cooldown/đổi proxy. Cấp email sạch kế tiếp của máy đó để hoàn tất reg bù qua `ensure_row_accounts.py <row> --machines <STT>`. Sau khi tạo xong, bắt buộc chạy WinRT OCR trên `profile_<stt>_after_ensure.png`, nắn chuẩn lệch cột (ngày tạo cột 9, serial cột 10) trong `taikhoan_dat_v2_updated .xlsx` và đồng bộ 3 bên (`TikX`, safe workbook, tracker DB). Chi tiết: `references/preflight-reg-bu-row-email-exhaustion-triage.md`.
- `[07] Tat ca N email cua STT da co TK TikTok`: **BẪY TỬ HUYỆT / CHỐNG BÁO ẨU "CẠN MAIL"**: Nick là tài sản farm, TUYỆT ĐỐI CẤM vội vàng phán cạn mail hay đòi nạp/mua thêm mail mới! Trong thực tế vận hành farm, phần lớn trường hợp này là do **NICK ĐÃ ĐƯỢC REG THÀNH CÔNG TỪ TRƯỚC** nhưng bị rơi rớt dữ liệu khỏi `taikhoan_dat_v2_updated .xlsx` (do script lỗi không ghi nhận, do công thức STT Tik/Folder bị lệch khiến bộ lọc restore/clean xóa nhầm, hoặc do chưa sync sang `taikhoan_run_safe.xlsx` / `TikX.xlsx`).
  * **Căn nguyên kỹ thuật cốt lõi (Vỡ vụn ghi nhận Excel - `FAILED_SYNC_OSError` & Slot Collision)**:
    1. **Lỗi `FAILED_SYNC_OSError` nuốt chửng kết quả**: Khi batch reg hoàn tất (`_run_all_targets.py`), tiến trình gọi `write_deferred_results_sequential` để ghi danh sách `tracking_result_*.json` vào `taikhoan_dat_v2_updated .xlsx`. Nếu file Excel bị khóa bởi OneDrive sync, tiến trình khác đang mở hoặc lỗi I/O, toàn bộ batch sẽ dính `"workbook_write": "FAILED_SYNC_OSError"`. Máy thật đã đăng ký thành công và giữ nick đăng nhập, file `tracking_result_*.json` đã sinh, nhưng Excel không có dữ liệu!
    2. **Trùng Slot Folder (Modulo 8 Collision)**: Một máy có 2 nick nhưng Folder video cùng chia hết cho 8 (ví dụ Folder 121 và 129 cùng mod 8 = 1, chiếm Slot Tik1), đẩy các Slot khác (Slot 5, 6, 7) thành `None` trên `taikhoan_run_safe.xlsx`.
    3. **Vòng lặp treo Preflight**: Khi runner preflight (`ensure_row_accounts.py <row>`) thấy slot trống giả, nó bốc các mail còn lại của STT đó trong `gmail_clean_v2.xlsx` đi reg lại. Nhưng các mail này chính là những mail đã đăng ký thành công ở các đợt bị `FAILED_SYNC_OSError` hoặc đã có tài khoản TikTok. TikTok trả về màn hình OTP login / "Email đã tồn tại" -> Script cạn mail và văng `[07]`.
  * **Triage bắt buộc (CẤM NẠP/MUA MAIL MỚI NGAY):**
    1. Trích xuất ảnh switcher dropdown `screenshots_social/<STT>_03_dropdown_*.png` và chạy WinRT OCR (`scripts/winrt_ocr.py`) để lấy toàn bộ danh sách username thực tế đang login trên máy.
    2. Kiểm tra `all_results.json` trong runtime batch gần nhất (`D:/Taadaa/runtime/<cluster>/artifacts/runs/social-batch-all/<run_id>/all_results.json`) xem có dính `FAILED_SYNC_OSError` hay không.
    3. Trích xuất file `tracking_result_stt<STT>_*.json` trong thư mục batch để lấy đủ `tiktok_id`, `email`, `mail_password`, `created_date`.
    4. Kiểm tra `taikhoan_run_safe.xlsx` để biết máy đang thực sự thiếu ở Row/Slot nào (1..8).
    5. Quét các bản sao lưu gần nhất (`taikhoan_dat_v2_updated_BEFORE_RESTORE*.xlsx`, `.bak`, `archive_history`, `workbook-backups`, runtime JSON logs) để tìm lại TikTok UID/Password của các email này.
    6. Đối soát STT gán mail trong `gmail_clean_v2.xlsx` với số Máy trong `taikhoan_dat_v2_updated .xlsx` để **KHÔI PHỤC VỀ ĐÚNG MÁY GỐC**. CẤM TUYỆT ĐỐI gán lung tung sang máy khác tạo ra tài khoản "kí sinh" (parasite account).
    7. Backfill bổ sung ngay vào `taikhoan_dat_v2_updated .xlsx`, cập nhật `taikhoan_run_safe.xlsx` và `TikX.xlsx` để giải phóng máy khỏi vòng lặp reg bù vô nghĩa.
    8. Nghiệm thu hậu kỳ sau fix lock Excel: Xác nhận dòng mới trong sổ gốc, slot trong safe workbook không còn `None`, kiểm tra PID tiến trình nền (`ensure_row_accounts.py` có cơ chế mutex lock tránh chạy chồng), và đối soát O(1) `adb devices` khi Hub USB phục hồi (bóc tách rõ máy nào đã online lại và máy nào còn rớt cáp lẻ).
    9. CHỈ KHI đã quét sạch toàn bộ backup/log và chứng minh chắc chắn email chưa từng có nick hợp lệ trên farm thì mới được kết luận cạn mail để nạp mail mới. Chi tiết: `references/preflight-reg-bu-row-email-exhaustion-triage.md`.
    10. **Bẫy lỗ hổng Slot giữa chừng & Chuẩn hóa Slot dồn toa (Contiguous Slot Packing)**: Khi máy có $K < 8$ nick thực tế (ví dụ 7 nick), BẮT BUỘC dồn $K$ nick này vào liên tục từ Slot 1 đến Slot $K$ trong `taikhoan_run_safe.xlsx`, đẩy toàn bộ ô `None` về cuối dải (Slot $K+1$..8). CẤM để lỗ hổng ở giữa (như Slot 4 để `None` trong khi Slot 7, 8 có nick), vì khi lệnh `ensure_row_accounts.py 7` kiểm tra ô thứ 7, nó thấy có nick nên báo "Đã đầy đủ" và exit mà không reg bù! Slot reg bù chuẩn luôn là `ensure_row_accounts.py <K+1>`. Đồng thời nếu email bị TikTok báo "Đã có tài khoản trên hệ thống", phải set ngay cột 11 `trạng thái = 'used'` trong `gmail_clean_v2.xlsx` để cách ly. Chi tiết: `references/preflight-reg-bu-row-email-exhaustion-triage.md`.
    11. **Bằng chứng thị giác bắt buộc cho kết quả reg hoàn tất (Visual Evidence Invariant)**: CẤM TUYỆT ĐỐI gửi ảnh màn hình chọn ngày sinh (DOB picker) hoặc ảnh màn hình video For You feed để báo hoàn tất. Bằng chứng hợp lệ DUY NHẤT để báo DONE reg tài khoản là ảnh chụp màn hình **Tab Hồ sơ (Profile)**: `profile_<stt>_after_ensure.png` (thể hiện rõ username `@<handle>`, 0 Follow/Follower/Like, và active tab Hồ sơ). Chi tiết: `references/preflight-reg-bu-row-email-exhaustion-triage.md`.
- `[adb-timeout] / UI_XML_TIMEOUT / device not found`: ADB daemon hang on host or physical USB hub disconnect. Coordinator phải chủ động giám sát: nếu lệnh kiểm tra/ADB shell time out > 10s hoặc worker im lặng bất thường, KHÔNG chờ đụng trần timeout 600s; chạy ngay `taskkill -F -IM adb.exe` và `adb start-server` (chỉ trên local host) để thông đường truyền trước khi phán đoán tiếp. ĐẶC BIỆT trên Remote Host (Admin 192.168.110.119): TUYỆT ĐỐI CẤM `kill-server` từ xa vì nguy cơ chết server vĩnh viễn. Nếu `adb get-state` trả về `device` nhưng `adb shell` bị hang, dùng lệnh O(1) phục hồi đúng socket thiết bị: `adb -H <ip> -P <port> -s <serial> reconnect`.
- `[Bulk device not found / USB Hub Outage & Hardware PnP Topology Triage]`:
  * **Hiện tượng**: Batch alert báo cụm 10-20 máy liên tục (ví dụ: M261-M280) bị `device '<serial>' not found` hoặc danh sách máy rải rác (ví dụ: M1, M7, M14, M15, M16, M17, M20, M69, M74, M75) đồng loạt dính `device offline` trên host local Kibe hay remote Admin.
  * **Căn nguyên thực tế**: Sự cố vật lý Hub USB phần cứng (sụt áp adapter nguồn, lỏng cáp uplink USB vào PC, hoặc controller hub WCH/QinHeng bị kẹt port reset).
  * **Phân định Phần mềm vs Phần cứng (Two-Phase Verification Gate)**: Chi tiết tham chiếu `references/software-recoverable-vs-hardware-usb-triage.md`. CẤM báo cáo ảo "đã fix" chỉ vì đã gửi lệnh `reconnect offline`. Bắt buộc kiểm chứng 2 tầng: sau khi gửi lệnh, `adb devices` phải chuyển `device` và shell ping `adb shell echo 1` phải trả về `1`. Nếu vẫn `offline` và PnP báo `Port Reset Failed` -> khẳng định 100% phần cứng.
  * **Chuẩn hóa CLI inspect_machine**: Hỗ trợ đồng thời cả định dạng `M<N>` lẫn `<N>` (ví dụ: `python D:/Taadaa/tools/inspect_machine.py M1`).
  * **Triage bắt buộc O(1) qua Windows PnP Topology**:
    - **KHÔNG THỂ cứu bằng phần mềm (Sự cố phần cứng Hub USB)**: Sụt áp adapter nguồn hoặc kẹt controller Hub QinHeng/WCH (`VID_1A86&PID_8095`). Các lệnh `Disable-PnpDevice` bị Windows chặn (`0x80041001`), hub thương mại không có IC điều khiển nguồn riêng từng cổng (PPPS). BẮT BUỘC chuyển L3 BLOCKED và yêu cầu thao tác vật lý (bật/tắt công tắc nguồn Hub hoặc cắm lại cáp uplink). Chi tiết: `references/usb-hub-hardware-failure-vs-software-recovery.md`.
  * **Triage bắt buộc O(1) qua Windows PnP Topology (Chi tiết: `references/hardware-pnp-topology-hub-outage-triage.md` & `references/usb-hub-hardware-failure-vs-software-recovery.md`)**:
    0. **Preflight Live Batch Protection Gate**: Trước khi chạy lệnh kill/restart nào, bắt buộc kiểm tra `~/.codex/device-locks` và tiến trình `python.exe` (`Get-Process`). Nếu đang có batch khác chạy trên các máy khỏe, CẤM TUYỆT ĐỐI `taskkill -F -IM adb.exe` làm sập phiên toàn fleet.
    1. **Sàng lọc từng máy**: Chạy `python D:/Taadaa/tools/inspect_machine.py M<N>` (hỗ trợ cả tiền tố `M<N>` lẫn `<N>`). Phân loại máy đã tự hồi phục (`NO_TOUCH_SCOPE`, ví dụ M7, M17) và máy thực sự `offline`. Lưu ý trong git-bash nếu `adb` chưa trong PATH, dùng đường dẫn tuyệt đối `/c/Program Files (x86)/xiaowei/tools/adb.exe`.
    2. Truy vấn parent hub của các serial lỗi bằng PowerShell:
       ```powershell
       $offline_serials = @('<serial1>', '<serial2>', ...)
       foreach ($s in $offline_serials) {
           $dev = Get-PnpDevice | Where-Object { $_.InstanceId -like "*$s*" } | Select-Object -First 1
           if ($dev) {
               $p = (Get-PnpDeviceProperty -InputObject $dev -KeyName 'DEVPKEY_Device_Parent').Data
               Write-Host "$s -> $p"
           }
       }
       ```
    3. Nếu đa số máy lỗi (ví dụ 5/7 máy) cùng trỏ về 1 Hub InstanceId chung (như `USB\VID_1A86&PID_8095\...`), kiểm tra tiếp trạng thái các cổng trên Hub đó:
       `Get-PnpDevice | Where-Object { (Get-PnpDeviceProperty -InputObject $_ -KeyName 'DEVPKEY_Device_Parent' -ErrorAction SilentlyContinue).Data -like "*<Hub_ID>*" } | Select-Object FriendlyName, Status, Present`
    4. Nếu thấy các thiết bị con báo `Unknown USB Device (Port Reset Failed)`, `Configuration Descriptor Request Failed`, `Device Descriptor Request Failed`, hoặc `Set Address Failed`: Khẳng định 100% sự cố phần cứng Hub USB / nguồn cấp, các lệnh `adb reconnect offline` hay `taskkill -F -IM adb.exe` sẽ không thông được cổng. Chuyển L3 BLOCKED và yêu cầu kiểm tra vật lý (cắm lại cáp uplink, tắt/bật lại adapter nguồn Hub). Chi tiết: `references/hardware-pnp-topology-hub-outage-triage.md`.
- `[Batch Aggregator & Classifier False Alert Triage (Fix Lỗi Báo Ngu)]`:
  * **Egress IP & Header Spam Trap**: Bổ sung `"ip verification"`, `"verification failed"`, `"egress"`, `"proxy"`, `"vpn"` vào `CHALLENGE_EXCLUSIONS`. Khi format alert, bắt buộc collapse whitespace/newlines <= 160 ký tự (`_format_inline_error`).
  * **P0 Mất Phiên Ảo (Profile Verification Navigation/Focus)**: Trong `batch_aggregator.py`, `error_type="login-gms-verification"` bị chuỗi `"login"` bắt nhầm thành văng nick. Bổ sung `SESSION_LOST_EXCLUSIONS` (`"profile verification"`, `"navigation-failed"`, `"focus lost"`, `"swipe"`) và log telemetry `[SESSION_LOST_EXCLUSION]`.
  * **Xác Minh / Captcha Ảo (Caption Phóng Sự Chứa "xác minh")**: Video trên feed chứa *"điều tra xác minh"* khiến `classifier.py` gán nhãn `manual-needed:verification`. CẤM bypass toàn cục `> 80` chars (bị Sol Auditor reject vì lọt challenge thật); CHỈ bypass generic `"xác minh"` khi `len > 40` chars, tuyệt đối không bypass explicit markers (`"manual_challenge"`, `"kiểm tra bảo mật"`), ghi log `[CLASSIFIER_CHALLENGE_BYPASS]` và viết đủ 4 test hồi quy. Chi tiết: `references/batch-aggregator-false-alert-and-classifier-trap.md`.
- `[Upload Hook Post-Feed Failure Policy & Preflight VPN Gate Invariant]`:
  * **Chỉ thị nghiệp vụ bất biến của Sếp (Policy Invariant)**: **CHO PHÉP UPLOAD VIDEO KỂ CẢ KHI FEED SESSION THẤT BẠI** (ví dụ feed swipe dính timeout hay non-critical issue vẫn được quyền upload video theo lịch). TUYỆT ĐỐI CẤM chặn upload toàn bộ chỉ vì feed không đạt status success, và **CẤM TUYỆT ĐỐI thêm `manual-needed` vào `_SENSITIVE_STOP_WORDS`** (vì hầu hết feed thất bại đều dừng với stop_reason `manual-needed:...`, việc nhét `manual-needed` vào sensitive stop words sẽ bóp nghẹt quyền upload hợp lệ của các máy feed fail).
  * **Căn nguyên thực sự khiến máy vẫn nhảy vào `ACCOUNT_SWITCHER` khi mạng hỏng**:
    - Khi feed session thất bại do proxy rớt mạng (ví dụ proxy timeout ở bước preflight hay auto-login), runner vẫn gọi Upload Hook theo thiết kế cho phép upload.
    - Trong `Tiktok-video/scripts/tiktok_workflow/run_post.py`, hàm `run_preflight()` có gọi `require_android_vpn()`, nhưng hàm chạy thật `run_post()` lại bỏ quên bước kiểm tra này. Nó nhảy thẳng vào `machine.execute(context)` mở app TikTok và chạy `ACCOUNT_SWITCHER` trên một kết nối proxy đã chết!
  * **Khắc phục chuẩn mực (Đúng thiết kế & Không chặn nhầm upload)**:
    - **TUYỆT ĐỐI KHÔNG sửa bộ lọc `_SENSITIVE_STOP_WORDS` trong `multi_machine_feed_session.py`** để giữ nguyên quyền upload khi feed fail.
    - **Bắt buộc chốt cổng Preflight VPN ngay đầu `run_post()`**: Gọi `require_android_vpn(adb, required=vpn_required)` trước khi khởi tạo `StateMachine` hay chạm vào UI. Nếu proxy chết / timeout, script fail-closed exit 2 (`[PREFLIGHT_VPN_BLOCKED]`) ngay lập tức, tuyệt đối không mở TikTok hay vào Account Switcher. Nếu proxy sống, script tiến hành upload bình thường kể cả feed trước đó thất bại. Chi tiết: `references/watchdog-silent-and-reporting-standard.md`.
- `[Auto-Login Recovery on Missing Account: Fast Login vs Ambiguous Machine-Wide Reconcile Fallback]`:
  * **Bản chất kiến trúc**: Khi runner phát hiện thiếu tài khoản trong Account Switcher (`_maybe_recover_missing_account_via_login`), hệ thống tự động chạy theo 2 lớp:
    - **Lớp 1 (Fast Targeted Login)**: Gọi trực tiếp `tiktok_login_v1.py <machine> --email <expected> --ss --allow-parent-lock`.
    - **Lớp 2 (Fallback Reconcile)**: Nếu Lớp 1 fail hoặc unverified, fallback sang `reconcile_tiktok_accounts.py`.
  * **2 Cạm bẫy gây dừng tự động hóa**:
    1. **VPN Gate Fail-Closed do Proxy Timeout**: Đúng lúc fast login chạy, nếu proxy port của máy bị timeout kiểm tra IP ngoại vi (`ifconfig.me`), VPN Gate sẽ fail-closed (exit code 2) để bảo vệ IP thật. Đây là lỗi TRANSIENT, không phải mất phiên.
    2. **Lỗi Ambiguous Machine-Wide Reconcile**: Lệnh gọi `reconcile_tiktok_accounts.py` trong `feed_swipe_smoke.py` nếu thiếu argument `--expected-username <expected>` sẽ bị script reconcile từ chối: `CONFIG_ERROR: machine <id>: ambiguous machine-wide reconcile; explicit expected username is required` (do máy có thể chứa nhiều slot nick).
  * **Khắc phục**: Luôn đảm bảo lệnh gọi fallback reconcile trong `feed_swipe_smoke.py` truyền đầy đủ `--expected-username <expected>`, và phân biệt rõ lỗi VPN preflight timeout để retry thay vì gắn cờ lỗi vĩnh viễn.
- `[XiaoWei Screen Mirroring "Phone disconnected" vs ADB Offline Triage]`: **BẪY BÁO ẢO SẬP MÁY / VĂNG ADB KHI SOI APP CON GẤU (XIAOWEI / JIWEI VIP)**: Khi máy hiển thị cam *"Phone disconnected"*, CẤM vội kết luận sập nguồn hay mất toàn bộ ADB.
  * **Bản chất**: XiaoWei stream qua reverse ADB port 5037; timeout >15s sẽ khóa slot mà không tự reconnect dù máy sống 100%. Tránh xung đột ADB cũ (v29 SamFwTool vs v34 XiaoWei).
  * **Triage O(1)**: `adb devices` kết hợp test `adb shell echo 1` (timeout 2.5s):
    1. *Rớt thật (device not found/offline)*: Dùng PnP/SSH kiểm tra, nếu `CM_PROB_PHANTOM` -> Báo L3 BLOCKED cắm lại cáp/nguồn.
    2. *Treo I/O / nghẽn socket*: `adb -s <serial> reconnect` nguyên tử (CẤM kill-server toàn farm), máy hồi sinh sau 1-2s.
    3. *Ảo do XiaoWei*: Shell <0.5s bình thường -> click chuột vào slot trên XiaoWei hoặc gửi `keyevent 224` là lên hình.
  * **Kỷ luật Hạ Tầng & Tự Cứu Bằng Phần Mềm (Watchdog Hạ Tầng)**:
    1. *CẤM vẽ script mới rác*: Khi user yêu cầu auto-fix hoặc gặp lỗi hạ tầng, bắt buộc kiểm tra `cronjob action='list'` và tái sử dụng watchdog hiện có (`farm-adb-transport-healer` [*/3m], `farm-wifi-auto-healer` [*/5m], `farm-idle-screen-and-app-healer` [*/15m], `reap-dead-owner-locks` [*/5m], `farm-app-provision-watchdog` [04:00]).
    2. *Two-Phase Verification Gate*: Trong auto-healer, CẤM gọi `reconnect` rồi tự append "cứu sống" mà không kiểm tra lại. Bắt buộc quét lại `adb devices` và ping `echo 1`. Chỉ khi máy thật sự sang `device` mới báo `HEALED`; nếu vẫn `offline` do lỗi phần cứng Hub USB (Port Reset Failed) thì KHÔNG báo ảo.
    3. *Đồng bộ ADB binary*: Ưu tiên ADB của XiaoWei (`C:\Program Files (x86)\xiaowei\tools\adb.exe` v34) trên Kibe local để đồng bộ server port 5037.
    4. Chi tiết: Xem `references/farm-infrastructure-auto-healer-and-xiaowei-rules.md` và `taadaa-farm-ops-rules/references/xiaowei_screen_mirror_diagnostics.md`.
- `[P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT (UploadHook / Focus Lost) False Positive Triage]`:
  * **Hiện tượng**: Telegram bắn alert `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện N máy dính lỗi login/mất phiên` kèm các lý do:
    - `profile verification navigation-failed: TikTok focus lost`
    - `UploadHook: [ACCOUNT_SWITCHER_FAILED] open_switcher failed: SWITCHER_NOT_CONFIRMED: switcher markers were not confirmed. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa, dismiss popup/onboarding thủ công rồi retry.`
    - `UploadHook: [ACCOUNT_SWITCHER_FAILED] open_profile_root failed: ATX_SESSION_UNAVAILABLE: ATX session UI capture failed after retry and reset. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa, dismiss popup/onboarding thủ công rồi retry.`
    - `UploadHook: [ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa, dismiss popup/onboarding thủ công rồi retry.`
    - `UploadHook: [ACCOUNT_SWITCHER_FAILED] TikTok không trở lại foreground trước ACCOUNT_READY. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa, dismiss popup/onboarding thủ công rồi retry.`
  * **Bản chất kỹ thuật (100% False Positive cho mất phiên / logout)**:
    - Watchdog/batch aggregator tự động gộp bất kỳ exception nào mang thông báo chứa cụm `Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa` hoặc `focus lost` vào cảnh báo P0 văng account.
    - Thực tế tài khoản vẫn đăng nhập 100%:
      1. Với `ATX_SESSION_UNAVAILABLE` ở `open_profile_root`: Thường do tiến trình uiautomator stub phản hồi chậm hoặc nghẽn I/O khi dump XML lúc chuyển trang; nếu trước đó feed session đã hoàn thành (`swipes_completed > 0`), tài khoản hoàn toàn bình thường, chỉ cần reconnect ADB hoặc khởi động lại atx-agent daemon (`/data/local/tmp/atx-agent server -d`).
      2. Với `ACCOUNT_MISSING` ở `select account failed`: Rất thường do 2 nguyên nhân (cả 2 đều KHÔNG PHẢI mất phiên/logout):
         - **Tài khoản kí sinh (parasite account)** từ máy khác đăng nhập nhầm vào chiếm viewport hoặc danh sách có >= 7 tài khoản làm nick đích bị cuộn khuất ngoài tầm nhìn.
         - **Máy chưa nạp đủ slot tài khoản (Unpopulated Slot Trap)**: Thiết bị thực tế chỉ mới đăng nhập $K < 8$ nick (ví dụ 7 nick, nút `+ Thêm tài khoản` vẫn hiển thị ở đáy switcher), nhưng safe workbook đã map đủ 8 nick từ sổ cái. Khi ca nuôi yêu cầu nick thứ 8 (ví dụ ca nuôi Row 3 yêu cầu nick chưa login), runner tìm không thấy trong switcher nên ném `ACCOUNT_MISSING`. Tài khoản chính và $K-1$ nick phụ vẫn đăng nhập 100% an toàn. Chỉ cần kiểm tra thông tin đăng nhập trong sổ cái Master (`taikhoan_dat_v2_updated .xlsx`) và nạp bổ sung nick vào slot còn thiếu: `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <target_id> --ss --no-track` (cờ `--no-track` tránh lỗi workbook lock giả).
      3. Với `SWITCHER_NOT_CONFIRMED`: Do milestone popup ("Tổng số lượt thích: ... đã nhận tổng cộng N lượt thích cho tất cả video [OK]", "Bạn đang nghĩ gì...") che khuất profile header anchor khiến `Header candidates=0`.
      4. Với `TikTok không trở lại foreground trước ACCOUNT_READY`: Do Google Play Store (`com.android.vending/PlayCoreAcquisitionActivity`) bung popup tải split APK PlayCore feature delivery đè lên giao diện sau khi switch tài khoản.
      5. Với `profile verification navigation-failed: TikTok focus lost`: Nếu `swipes_completed > 0` và hook upload kế tiếp thành công (`upload_result.json` có `exit_code: 0, status: success`), máy đã hoàn thành nhiệm vụ trọn vẹn; focus lost chỉ là trạng thái chuyển tiếp giữa các app hoặc socket ADB bị chậm ở bước cleanup cuối session.
  * **Triage bắt buộc O(1)**:
    1. Kiểm tra live focus & screencap: `python D:/Taadaa/tools/inspect_machine.py <N>`. (Lưu ý: trong môi trường git-bash nếu lệnh `adb` chưa có trong PATH, dùng đường dẫn tuyệt đối `C:\Program Files (x86)\xiaowei\tools\adb.exe`).
    2. Chạy WinRT OCR (`from validate_evidence_screen import run_winrt_ocr`) trên `soft-reboot-*-before.png` hoặc live screencap:
       - Nếu OCR thấy 5 tab điều hướng (*Trang chủ, Cửa hàng, +, Hộp thư, Hồ sơ*) hoặc username `@...`: khẳng định ngay **PHIÊN ĐĂNG NHẬP AN TOÀN 100%**.
       - Kiểm tra `upload_result.json` và `run_manifest.json` trong runtime batch để xác nhận số swipes và trạng thái upload thực tế.
       - Tuyệt đối CẤM can thiệp tay login lại hay thao tác xóa nick khi chưa có bằng chứng văng tài khoản thật sự.
- `[profile verification navigation-failed / focused package unavailable vs P0 Session Lost Trap in Batch Aggregator]`:
  * **Bản chất**: RẤT THƯỜNG LÀ FALSE POSITIVE cho "mất phiên / văng account". Nếu máy đã chạy xong swipes (`swipes_completed > 0`), nguyên nhân thường do socket ADB bị stall ở bước `verify_profile` hoặc `cleanup_close_all`.
  * **Bẫy `batch_aggregator.py` nuốt chửng lỗi navigation thành P0 mất phiên**:
    - Trong `batch_aggregator.py`, `SESSION_LOST_KEYWORDS` có chứa từ khóa `"login"`.
    - Lỗi taxonomy gán category `error_type = "login-gms-verification"`. Khi kiểm tra `any(kw in (m.error_type or "").lower() for kw in SESSION_LOST_KEYWORDS)`, chuỗi `"login"` khớp ngay với `"login-gms-verification"`, khiến mọi lỗi thuộc category này (kể cả `profile verification navigation-failed: TikTok focus lost...`) bị gom nhầm thành `session_lost_failures` và bắn cảnh báo đỏ `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`.
    - **Khắc phục chuẩn**: Bổ sung `SESSION_LOST_EXCLUSIONS = ("profile verification", "navigation-failed", "navigation failed", "focus lost", "focused package unavailable", "failed to focus", "feed swipe", "swipe")` và loại trừ `(m.error_type or "").lower() != "login-gms-verification"` khi kiểm tra bare keyword `"login"`.
  * **Triage chuẩn**: Chạy `adb reconnect <serial>`, gọi `inspect_machine.py`, chụp screencap qua `exec-out screencap -p` và chạy WinRT OCR kiểm tra 5 tab điều hướng (*Trang chủ, Cửa hàng, +, Hộp thư, Hồ sơ*). Nếu đủ 5 tab -> tài khoản an toàn, chỉ cần reconnect ADB.
- `[permission-denied-hang]`: TUYỆT ĐỐI CẤM dùng `grep -rn` quét diện rộng trên cây thư mục repo (như `/d/Taadaa/Tiktok_Reg/`). Trên Windows, các folder test cache (`.pytest-basetemp-*`, `.ai-runs`) có phân quyền khóa chặt gây lỗi *Permission denied* và làm terminal bị kẹt 600s. Chỉ trích xuất log/XML đích danh O(1) theo file name / timestamp cụ thể.
- `tiktok_login_v1 CLI Flags & OneDrive Lock Pitfall`:
  * `tiktok_login_v1.py` KHÔNG hỗ trợ `--no-feed-after-reg` hay `--no-avatar-after-reg` (truyền vào sẽ crash argparse). Muốn tắt feed/avatar hook, dùng env `TIKTOK_REG_FEED_AFTER_REG=0` và `TIKTOK_REG_AVATAR_AFTER_REG=0`.
  * **BẪY `TRACKING_WORKBOOK_WRITE_LOCKED` KHI LOGIN NICK CŨ**: Khi nạp/login lại tài khoản đã có sẵn trong sổ cái Master (`taikhoan_dat_v2_updated .xlsx`), bước cuối của `tiktok_login_v1.py` sẽ cố ghi cập nhật vào workbook. Nếu OneDrive đang đồng bộ hoặc file đang bị khóa bởi tiến trình khác, script sẽ raise `BLOCK TRACKING_WORKBOOK_WRITE_LOCKED: [Errno 9] Bad file descriptor` và thoát với exit code 1 dù máy thật đã đăng nhập 100% thành công! Đối với các tài khoản đã tồn tại trong sổ cái, BẮT BUỘC truyền cờ `--no-track` (ví dụ: `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <nick> --ss --no-track`) để tránh lỗi ghi workbook giả và kiểm chứng kết quả trực tiếp qua WinRT OCR trên Switcher.
- `[01_open] TikTok not foreground after clean launch`: RẤT THƯỜNG LÀ TRIỆU CHỨNG HẠ NGUỒN CỦA MẤT KẾT NỐI ADB (`device '<serial>' not found` hoặc socket stall) trong quá trình clean launch / atx-agent dump UI. Triage chuẩn O(1):
  * Chạy ngay `python D:/Taadaa/tools/inspect_machine.py <N>`.
  * Nếu `device '<serial>' not found`: Kiểm tra xem rớt cáp đơn lẻ hay sập nguồn cả Hub USB 20 cổng (ví dụ dải M261–M280 đồng loạt mất kết nối trên Admin `192.168.110.119:5037`).
  * Với máy đơn lẻ trên host Admin: Dùng SSH kiểm tra PnP device: `ssh admin-farm "powershell -Command \"Get-PnpDevice | Where-Object { \$_.InstanceId -like '*<serial>*' } | Select-Object FriendlyName, Status, Present, Problem\""`. Nếu `Present: False` và `Problem: CM_PROB_PHANTOM` -> Khẳng định 100% rớt phần cứng vật lý (lỏng cáp hoặc sập nguồn máy lẻ), chuyển L3 BLOCKED kèm evidence, CẤM retry hay dispatch sửa code.
  * **BẪY NUỐT LỖI ADB OFFLINE TRONG BỘ BÓC TÁCH LỖI ALERT PREFLIGHT (`_extract_reg_error`)**: Khi máy rớt kết nối vật lý, script con văng `RuntimeError: [01_open]...`. Nếu hàm `_extract_reg_error()` trong `ensure_row_accounts.py` bắt `RuntimeError` trước rồi kẹp check `device not found` trong nhánh `if not err_line:`, lỗi ngọn `[01_open]` sẽ nuốt chửng lỗi gốc khiến alert Telegram báo sai bản chất (*"báo lung tung"*). BẮT BUỘC ưu tiên quét chuỗi `("device" in text_lower and "not found" in text_lower) or "device offline" in text_lower or "offline" in err_lower` ngay đầu bộ phân loại và trả về thẳng `ADB offline (device not found)`.
  * Tuyệt đối không cho `ensure_row_accounts.py` reg bù nếu máy chưa online ADB (`adb get-state == 'device'`).
  * Nếu máy online nhưng TikTok không lên: Kiểm tra atx-agent (`curl http://127.0.0.1:7912/version`) hoặc force-stop TikTok và mở lại.
- `[03_dropdown] Khong mo duoc account dropdown (Profile Chevron vs Text Center Trap & TikTok Rewards Popup & Single-Account Pitfall)`:
  * **Hiện tượng**: Preflight hoặc login dừng tại `[03_dropdown] Khong mo duoc account dropdown` dù đang ở sẵn Profile cá nhân.
  * **Căn nguyên cốt lõi & Các bẫy tử huyệt**:
    1. **THIẾT KẾ CHUẨN ACCOUNT SWITCHER (STICKY HEADER) & BẪY MÁY CHỈ CÓ 1 TÀI KHOẢN (SINGLE-ACCOUNT TRAP)**:
       - **Thiết kế chuẩn của hệ thống**: Khi ở trang Profile, vuốt cuộn để ID tài khoản ghim lên thanh **Sticky Header** trên cùng chính giữa (`pmi`/`pmf`, `bounds=[366, 72][732, 228]`, tâm `(549, 150)`), sau đó tap vào thanh sticky này để bung popup Chuyển đổi tài khoản (Account Switcher bottom sheet) rồi mới bấm "Thêm tài khoản".
       - **Bẫy máy chỉ có 1 tài khoản**: Thiết kế trên hoạt động 100% khi máy đã có từ 2 nick trở lên (có icon chevron ▼). Nhưng trên TikTok v46.x, nếu thiết bị chỉ mới đăng nhập đúng 1 tài khoản (ví dụ máy mới chỉ có nick Slot 1, các slot 2-8 còn trống):
         + Thanh Sticky Header trên cùng chính giữa và Header thông thường (`sv6`, `rz5`, `pmi`) chỉ là TextView/container tĩnh, hoàn toàn KHÔNG CÓ chevron dropdown ▼, tap hay long-press vào đều trơ ra không bung switcher.
         + Trong `Cài đặt và quyền riêng tư` (Settings): Mục `"Chuyển đổi tài khoản"` / `"Thêm tài khoản"` HOÀN TOÀN KHÔNG TỒN TẠI (TikTok chỉ hiện khi đã có >= 2 nick). Ở đáy Settings chỉ có danh mục `"Đăng nhập"` với lựa chọn duy nhất là `"Đăng xuất"`.
         + *Hướng xử lý*: Đối soát số nick thực tế qua sổ cái. Với máy chỉ có 1 nick, điều hướng qua `"Đăng xuất"` ở đáy Settings (TikTok tự lưu session vào One-tap login) để đưa Profile về trạng thái Đăng ký (Signup) có form thêm email mới thay vì lặp lại việc tìm "Chuyển đổi tài khoản".
    2. **BẪY CỬ CHỈ SAMSUNG PAY & SAFE SWIPE BOUNDS (1080x1920)**:
       - Trên các dòng Samsung Galaxy S7 (SM-G930F/L/K/S), mép dưới màn hình `[300, 1893][780, 1920]` có tab vuốt nhanh Samsung Pay / Thanh toán đơn giản.
       - CẤM TUYỆT ĐỐI dùng tọa độ vuốt bắt đầu từ `y >= 1500` (như `swipe 540 1650 540 350`) hoặc tap vào vùng dock điều hướng `y >= 1790`. Lệnh vuốt quá sát đáy sẽ kéo thanh Samsung Pay / App drawer hoặc bấm Home, làm TikTok bị đẩy xuống background và văng ra LauncherActivity.
       - *Quy chuẩn Safe Swipe Bounds*: BẮT BUỘC dùng dải an toàn `y_start <= 1400` (khuyến nghị `1350`), `y_end >= 450` (khuyến nghị `500`), duration `300-400ms`.
    3. **KỶ LUẬT GỬI ẢNH NGHIỆM THU (CHỐNG BÁO CÁO MÙ & CHỐNG ĐỂ USER HỎI "HÌNH ĐÂU")**:
       - User duyệt tiến độ và kết quả bằng mắt qua ảnh (`MEDIA:`). CẤM TUYỆT ĐỐI trả lời câu hỏi trạng thái Canary ("Chạy chưa?", "Xong chưa?") bằng text thuần túy mà thiếu ảnh chụp màn hình máy thật (`MEDIA:<path_anh>`).
       - CẤM TUYỆT ĐỐI gửi ảnh màn hình Home/Launcher của điện thoại làm bằng chứng hiện trường ứng dụng (tránh phản ứng gay gắt: *"Gửi tao màn home của máy chi v"*).
       - Bằng chứng gửi User BẮT BUỘC phải là ảnh giao diện TikTok (Profile, Settings, Popup lỗi). Nếu app bị rơi xuống background, phải launch app lên foreground (`monkey -p ...`) trước khi screencap.
    4. **TREO UIAUTOMATOR STUB & LỖI KILL OPERATION NOT PERMITTED**:
       - `com.github.uiautomator` chạy dưới uid app (`u0_a191`), lệnh `kill -9` từ shell user sẽ văng lỗi `kill: Operation not permitted`.
       - BẮT BUỘC dùng lệnh quản lý gói: `adb shell "am force-stop com.github.uiautomator && am force-stop com.github.uiautomator.test"` để hạ sạch tiến trình stub trước khi restart daemon atx-agent.
    5. **BẪY TAP MÉP PHẢI cx_arrow vs TAP TÂM (cx, cy) CHO DISPLAY-NAME (sv6)**:
       - Trên layout Profile TikTok 46.x: node display-name (`sv6`) là Button/TextView container có bounds rộng (ví dụ `[36, 280][555, 364]`). Nếu ép tap cứng mép phải `cx_arrow = max(x1 + 24, x2 - 28)` (tọa độ ~527), cú tap sẽ rơi vào khoảng trống ngoài lề (blank margin) của nút và không trigger click listener.
       - Cơ chế chuẩn: BẮT BUỘC tap tâm `(cx, cy)` trước (`(x1 + x2) // 2`, tương tự tọa độ đã giúp các máy như M267 mở dropdown thành công), sau đó nếu `_wait_account_dropdown_open` chưa bung mới thử fallback sang mép phải `(cx_arrow, cy)`. CẤM chỉ tap duy nhất mép phải.
    6. Popup chen Phần thưởng TikTok (`SparkActivity`): TikTok bung modal hybrid *"Phần thưởng TikTok / Điểm của bạn / Bạn phải đủ 18 tuổi trở lên... [Hủy] [Đồng ý]"* che khuất toàn bộ tương tác Profile. Bắt buộc bổ sung pattern `"phan thuong tiktok"`, `"diem cua ban"` và tap `"Hủy"` vào `dismiss_profile_overlays`. Chi tiết: `references/preflight-reg-bu-row-email-exhaustion-triage.md`.
- `[Cross-Cluster Safe Sync Leak (M75-80)]`: Khi chạy `sync-safe-workbook.py` trên môi trường không phải Kibe (như Admin), BẮT BUỘC đặt `TAADAA_HOST_ID=admin`. Nếu thiếu env này, script sẽ mặc định coi là Kibe và chèn `EXTRA_MACHINES = {75..80}` vào `admin/taikhoan_run_safe.xlsx`, gây ra lỗi slot trống giả và rơi vào danh sách Cooldown/Bỏ qua khi preflight reg bù. Trong wrapper `scripts/hermes_taikhoan_sync_cron.py`, hàm `_run_sync` BẮT BUỘC truyền tham số `cluster_name` và đặt `sync_env["TAADAA_HOST_ID"] = cluster_name` để cách ly hoàn toàn môi trường thực thi của từng cluster.
- `[Dual-Cluster ADB_SERVER_SOCKET Inheritance Leak]`: Khi chạy script preflight/reg bù từ máy điều phối Kibe sang cụm Admin (`HOST_ID="admin"`), nếu môi trường cha đã tồn tại `ADB_SERVER_SOCKET` (ví dụ `tcp:localhost:5037`), script con KHÔNG được dùng `if "ADB_SERVER_SOCKET" not in env` vì sẽ giữ nguyên socket local Kibe. Điều này dẫn đến toàn bộ lệnh ADB gọi tới serial máy Admin bị lỗi `device '<serial>' not found` và sập ở bước `[01_open] TikTok not foreground after clean launch`. Khi target host là Admin và hostname khác admin-farm, BẮT BUỘC ghi đè vô điều kiện: `env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"`.
- `[ACCOUNT_SWITCHER_FAILED] ACCOUNT_MISSING & Adapter Missing swipe()`: RẤT THƯỜNG LÀ FALSE POSITIVE cho "mất phiên / văng account".
  * **Hiện tượng**: Khi TikTok có >= 7 tài khoản, danh sách switcher bottom sheet chỉ hiển thị 6-7 nick đầu tiên trong viewport ban đầu. Nếu máy có nick phụ/parasite ở đầu danh sách, nick đích (ví dụ Tik 1) bị đẩy xuống dưới đáy (ngoài viewport).
  * **Nguyên nhân gốc rễ**: `automation_core.tiktok.account_switcher.select_exact_account` khi gặp `ACCOUNT_MISSING` sẽ cố gắng cuộn danh sách qua `getattr(adapter, "swipe", None)`. Nếu class adapter của repo consumer (như `TikTokAdapter` trong `tiktok-video/scripts/tiktok_workflow/adapter.py`) chưa implement method `swipe(start_x, start_y, end_x, end_y, duration_ms=450)`, hàm sẽ bỏ qua việc cuộn và văng lỗi `ACCOUNT_MISSING` ngay lập tức.
  * **Triage & Fix**:
    1. Chạy WinRT OCR trên `soft-reboot-account_switcher-before.png` để kiểm tra danh sách nick đang login. Nếu panel vẫn hiển thị 7 nick -> máy không bị logout.
    2. Đảm bảo adapter triển khai method `swipe(start_x, start_y, end_x, end_y, duration_ms=450)` gọi `adb.shell(["input", "swipe", ...])` để cho phép `select_exact_account` cuộn trang tự động tìm nick bên dưới.
    3. **Kỷ luật Sol Auditor Reviewer Gate (>= 85/100) khi sửa adapter/runner**:
       - Nếu chỉ viết 1 happy-path unit test, Sol Auditor sẽ chấm rớt (~70/100 REJECTED) do thiếu failure mode, thiếu integration test với workflow và thiếu telemetry.
       - BẮT BUỘC bổ sung structured telemetry (`logger.debug("[ADAPTER_SWIPE] ...")`, `logger.warning("[ADAPTER_SWIPE_FAILED] ...")`) và viết đủ bộ 4 tests trong `tests/test_adapter.py`: (a) Happy path verify lệnh ADB input swipe, (b) `dry_run=True` không gọi ADB, (c) ADB failure raise đúng `AccountSwitcherError("SWIPE_FAILED", ...)`, (d) Integration test mô phỏng multi-viewport scroll của `select_exact_account`.
       - Lệnh chạy closeout: `python D:/Taadaa/tools/closeout_gate.py --repo <path> --base HEAD~1 --json-output` với `timeout: 60` (tránh timeout > 60s bị guard chặn). Chi tiết: `references/account-switcher-adapter-swipe-contract.md`.
- `[Bẫy Tử Huyệt Dọn Nick Kí Sinh Đang Là Active Profile (Active Profile Parasite Trap)]`:
  * **Hiện tượng**: Chạy watchdog dọn nick kí sinh (`watchdog_idle_parasite_reconcile.py` hoặc thủ công), script báo `DONE` nhưng thực tế tài khoản kí sinh vẫn còn nguyên trong máy, dẫn đến kẹt trần 8 nick và văng `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING` ở các ca nuôi kế tiếp.
  * **Căn nguyên cốt lõi (Active Profile Omission)**: Khi nick kí sinh đang là **tài khoản active trên màn hình chính Profile** (hiển thị ở Header `[36, 280][556, 364]`), TikTok v46.x **chỉ liệt kê các tài khoản phụ khác** trong danh sách switcher bottom sheet. Script duyệt XML switcher không thấy nick nên ngộ nhận là *"Nick đã không còn trong Switcher"* và đánh dấu `DONE` giả (false positive cleanup)!
  * **Quy trình xử lý chuẩn O(1)**:
    1. Kiểm tra username trên Profile Header (`@<handle>`) trước khi mở switcher. Nếu trùng với nick kí sinh cần logout: **TUYỆT ĐỐI KHÔNG mở switcher**.
    2. Đi thẳng vào Menu 3 gạch (`[954, 96][1056, 204]`, tâm `(1005, 150)`) -> `Cài đặt và quyền riêng tư` (`(548, 1276)`).
    3. Cuộn xuống đáy Settings (6-8 lượt swipe an toàn `540 1400 540 400 300`) -> tap `Đăng xuất` (`(282, 1662)`) -> Xác nhận dialog `Đăng xuất` (`(540, 1664)`).
    4. Nghiệm thu thị giác (Capture-Before-Cleanup): Mở lại switcher và cuộn xuống đáy, chạy WinRT OCR xác nhận nick kí sinh đã biến mất và nút `+ Thêm tài khoản` đã xuất hiện trở lại. Sau đó nạp lại nick chính chủ còn thiếu bằng `tiktok_login_v1.py <STT> --email <target_id> --ss --no-track` (dùng `--no-track` để tránh lỗi OneDrive write lock giả). Chi tiết: `references/active-profile-parasite-reconcile-trap.md`.
- `[Kỷ Luật Rà Soát Device Lock: Dead-Owner vs Live Running Batch Lock & Chỉ Đạo "Giành Lock Xử Lý"]`:
  * Khi User yêu cầu kiểm tra/xử lý máy bị chiếm lock (`~/.codex/device-locks`), TUYỆT ĐỐI CẤM xóa mù hoặc kill tiến trình hàng loạt!
  * **Bắt buộc phân biệt 2 nhóm lock qua `psutil.pid_exists(pid)`**:
    1. **Live Running Batch Lock**: PID đang tồn tại trong hệ điều hành và đang thực thi batch nuôi acc/upload hợp lệ (ví dụ: `run_tiktok.py --mode multi-machine-feed-session --machines ... --account-row-index ...` trên Kibe/Admin). Các lock này đang bảo vệ thiết bị trong phiên nuôi thật, **TUYỆT ĐỐI CẤM kill hoặc force-preempt**.
    2. **Dead-Owner Lock**: PID không còn tồn tại trong hệ điều hành (dead process) hoặc lock file đã hết hạn TTL (`ttl_seconds`) mà không có heartbeat cập nhật. Chỉ các lock này mới được kích hoạt `reap-dead-owner-locks.py` để chuyển vào archive `~/.codex/device-locks-reaped/`.
  * **Chỉ đạo "Giành lock xử lý máy nào còn lỗi" (Actionable Fleet Recovery)**: Khi User yêu cầu giành lock xử lý máy lỗi, CẤM chỉ liệt kê danh sách file lock một cách thụ động. BẮT BUỘC chủ động:
    1. Lấy danh sách máy lỗi từ batch gần nhất hoặc nghi vấn acc kí sinh/mất phiên (ví dụ M28, M34, M42, M73, M13...).
    2. Chiếm lock thiết bị O(1) để cô lập, bật màn hình máy thật (`input keyevent 224`), dùng ADB + WinRT OCR kiểm tra hiện trạng thực tế.
    3. Phân biệt rõ lỗi thực tế (dính nick kí sinh, thiếu nick chính chủ) vs False Alarm (video-detail fullscreen làm mất thanh điều hướng Home, PlayCore popup làm mất focus tạm thời).
    4. Xử lý triệt để: đăng xuất nick kí sinh, nạp nick còn thiếu bằng `tiktok_login_v1.py <STT> --email <nick> --ss --no-track`, dismiss popup/video detail, force-stop đưa về LauncherActivity và tắt màn hình dưỡng pin. Chụp ảnh nghiệm thu thị giác gửi `MEDIA:`.
- `[ACCOUNT_SWITCHER_FAILED] open_profile_root failed: PROFILE_ROOT_NOT_CONFIRMED`: RẤT THƯỜNG LÀ FALSE POSITIVE cho "mất phiên / văng account".
  * **Hiện tượng**: Xảy ra ở UploadHook hoặc đầu session khi TikTok vừa mở lên và bị che khuất bởi modal/popup hệ thống (như popup *"Thêm số điện thoại"* / `FindFriendsPageActivity` / cập nhật bảo mật).
  * **Triage & Fix**: Chụp screencap và chạy WinRT OCR trên `soft-reboot-account_switcher-before.png`. Nếu thấy popup "Thêm số điện thoại" hoặc trang tìm bạn bè -> tài khoản vẫn đăng nhập 100%. Dismiss popup hoặc đưa ứng dụng về Home (`keyevent 3`) rồi mở lại TikTok.
- `[TikTok 2FA Trap: Prefer Authenticator 2FA Over Email OTP]`: Màn hình 2FA của TikTok thường mặc định gửi mã về Email ("Sử dụng liên kết này hoặc nhập mã được gửi đến email") kèm dòng "Xác minh 2 bước". Nếu script ngộ nhận đây là Authenticator App và điền TOTP secret vào ô Email OTP -> TikTok từ chối liên tiếp 3 lần. Ngược lại, nếu script chấp nhận Email OTP mà không đổi phương thức thì lãng phí secret 2FA TOTP trong tracking database. Triage & Fix: BẮT BUỘC bấm `Sử dụng phương thức khác >` (`(408, 1098)`), chọn `Trình xác thực` / `Ứng dụng xác thực`, rồi điền mã TOTP Authenticator. Chỉ fallback Email OTP khi không có 2FA secret hoặc không đổi được phương thức. Chi tiết: `tiktok-login-automation/references/prefer-2fa-authenticator-over-email-otp-switch-method.md`.
- `[ACCOUNT_SWITCHER_FAILED] SWITCHER_NOT_CONFIRMED / Header candidates=0`: Occurs when an unhandled profile milestone popup (e.g., "Tổng số lượt thích ... [OK]", "Bạn đang nghĩ gì...") obstructs the profile header anchor.
  * **Triage**: Inspect WinRT OCR on `soft-reboot-account_switcher-before.png`. Nếu thấy text *"Tổng số lượt thích ... đã nhận tổng cộng ... lượt thích cho tất cả video [OK]"* hoặc *"Bạn đang nghĩ gì..."* che Profile header.
  * **Resolution**: Bổ sung pattern dismiss vào `_dismiss_simple_close_popup` trong `state_machine.py`: quét lowered markers (`"tổng lượt thích"`, `"tổng số lượt thích"`, `"bạn đang nghĩ gì"`) và tap label (`"OK"`, `"Xong"`). Bổ sung unit test focused `test_milestone_popup_dismisses_with_ok`. Chi tiết: `references/milestone-popup-and-avatar-edit-contract.md`.
- `[AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở & Bẫy tử huyệt "+ Thêm tiểu sử"`:
  * **Hiện tượng**: Xảy ra ở bước `ENSURE_AVATAR` khi tài khoản chưa có bio và TikTok render layout mới không có nút text `"Sửa hồ sơ"` / `"Edit profile"`, mà chỉ có nút `"+ Thêm tiểu sử"` (Add bio).
  * **Bẫy tử huyệt 1: Nút "+ Thêm tiểu sử"**: Nút `"+ Thêm tiểu sử"` CHỈ mở modal nhập text Tiểu sử (Bio), KHÔNG PHẢI màn hình Sửa hồ sơ / Thay đổi ảnh avatar. TUYỆT ĐỐI CẤM gán `"Thêm tiểu sử"`, `"+ Thêm tiểu sử"`, `"Add bio"` vào selector `_find_profile_edit_button`. Nếu gán vào, script sẽ tap vào đây, mở modal Bio không có nút avatar, `_wait_for_avatar_edit_screen` bị timeout 60s và giam lỏng UI suốt toàn bộ các bước fallback sau, văng lỗi sau 4 phút lãng phí.
  * **Bẫy tử huyệt 2: Bẫy hồi quy ImageView top-left `[24,96][126,204]` (tâm 75..78, 150)**:
    - Khi thấy log `[PROFILE_EDIT] [METRIC] event=pencil_fallback matched=1 position=(75..78, 150)` ngay trước khi TikTok văng ra `com.sec.android.app.launcher` (LauncherActivity), đây là **bẫy tap nhầm nút Back / Thoát góc trái trên cùng** của Android.
    - CẤM TUYỆT ĐỐI gọi `_find_new_profile_pencil` trong `_find_profile_edit_button`. ImageView góc trên bên trái `[24,96][126,204]` KHÔNG PHẢI bút chì mà là nút thoát app, tap vào sẽ đóng TikTok và văng lỗi `AVATAR_EDIT_OPEN_FAILED` trên hàng loạt máy (M218, M222, M223, M238, M4).
  * **Triage & Resolution**:
    1. Giữ selector `_find_profile_edit_button` chỉ tìm các nút sửa hồ sơ thực thụ (`"Sửa hồ sơ"`, `"Chỉnh sửa hồ sơ"`, `"Edit profile"`).
    2. Nút Bút Chì Bên Phải Tên (`right_pencil_button`): Trên layout mới không có text, nút Sửa hồ sơ thực chất là nút Button nằm ngay bên phải tên hiển thị (`bounds=[782,516][926,600]`, Center `(854, 558)`). Duyệt `750 <= left <= 950 and 450 <= top <= 650` để tap trực tiếp mở 100% màn hình Sửa hồ sơ ("Thay đổi ảnh").
    3. Bắt buộc nhấn `adapter.back()` khi `_wait_for_avatar_edit_screen` trả về `"missing"` hoặc `"unavailable"` để dọn sạch modal rác trước khi thử nhánh fallback kế tiếp.
    4. Sinh Avatar Gái Xinh Chuẩn: Dùng `AIFemaleFilter` (ViT ONNX) lọc frame khuôn mặt trích xuất từ clip video trong folder với `female_prob >= 0.8`, resize 512x512 JPEG quality 95 lưu đồng bộ vào cả `D:\video goc\<folder>\avatar.jpg` và `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg`. Chi tiết: `references/milestone-popup-and-avatar-edit-contract.md`.
    5. **Kỷ luật Sol Auditor Closeout Gate & Telemetry**: Khi gỡ bỏ fallback `_find_new_profile_pencil`, bắt buộc phát telemetry `logger.info("[PROFILE_EDIT] [METRIC] event=top_left_back_bypassed")` và `event=layout_detector_matched detector=...` cùng test case tương ứng để tránh bị Sol Auditor trừ điểm Observability (<85 REJECTED).
    6. **Kiểm tra Device Lock & Sàng lọc Máy Rảnh trước Live Canary (Unlocked Machine Canary Selection)**:
       - Khi user yêu cầu "chạy canary các máy lỗi", BẮT BUỘC kiểm tra xem farm có đang chạy ca nuôi acc (`multi-machine-feed-session`) hay không qua `~/.codex/device-locks`.
       - **BẪY "TOÀN FARM ĐANG BẬN" (ALL-FARM BUSY FALLACY)**: Khi feed session đang chạy, **KHÔNG PHẢI TẤT CẢ** các máy trong cụm lỗi đều bị lock. Một số máy (như M223, M238) bị lock, nhưng các máy khác trong cùng cụm lỗi (như M218, M220, M222) hoàn toàn **UNLOCKED và online bình thường**!
       - **Hành động chuẩn**: Quét `~/.codex/device-locks`, nếu có ít nhất 1 máy đại diện trong cụm lỗi rảnh (như M218 cho lỗi `AVATAR_EDIT_OPEN_FAILED`), kích hoạt ngay Canary độc lập trên máy rảnh đó, chạy background với `notify_on_complete=True`. Tuyệt đối không viện cớ tiến trình nuôi acc đang chạy để hoãn toàn bộ canary.
       - **Kỷ luật Remote ADB Host Admin**: Khi chạy avatar canary cho máy Admin (M200+) từ Kibe, BẮT BUỘC export:
         `$env:ADB_SERVER_SOCKET = "tcp:192.168.110.119:5037"`
         `$env:TAADAA_HOST_CONFIG = "D:\Taadaa\machine-config\admin.yaml"`
         PowerShell `Start-Job` trong `run_tiktok_upload_batch.ps1` tự động kế thừa socket này để kết nối sang host Admin. Chi tiết: `references/milestone-popup-and-avatar-edit-contract.md`.
- `[Watchdog Session Error Aggregation vs Ground Truth (Avatar False Alarm trên máy retry thành công)]`:
  * **Hiện tượng**: Báo cáo tổng kết watchdog `post_evening_avatar_watchdog.py` ở cuối ca báo máy bị lỗi (ví dụ: `❌ [AVATAR_UPLOAD_MENU_MISSING]: 42`), nhưng khi kiểm tra thì máy đã hoàn thành tốt đẹp.
  * **Nguyên nhân gốc rễ**: Watchdog tích lũy danh sách `session_failed_by_reason` qua mọi lần thử trong ca. Nếu máy từng fail ở Attempt 1 (ví dụ lúc 09:55 M42 fail menu) nhưng retry thành công ở Attempt 2 (lúc 11:05 M42 up avatar thành công, workbook `Tik5.xlsx` ghi `Avatar = OK`), watchdog không tự động xóa máy khỏi `session_failed_by_reason`. Khi hết khung giờ, báo cáo tổng kết vẫn liệt kê máy trong nhóm lỗi.
  * **Kỷ luật Triage O(1)**: Trước khi dispatch sửa máy bị báo lỗi, BẮT BUỘC đối soát:
    1. Trạng thái trong sổ cái: `python D:/Taadaa/Tiktok-video/scripts/resolve_avatar_pending_machines.py <tik>`. Nếu máy không nằm trong danh sách pending, máy đã `OK` từ trước.
    2. Run artifact gần nhất của serial máy trong `D:/CodexRuntime/tiktok-video/runs/*<serial>*20261001*/report.json`. Nếu `status == "AVATAR_SMOKE_SUCCESS"` hoặc `avatar_status == "FORCED_REPLACED_VERIFIED"`, khẳng định 100% False Alarm do lịch sử tích lũy watchdog, xếp vào `NO_TOUCH_SCOPE`.
- [AVATAR_SOURCE_MISSING] Avatar file not found in folder:
  * **Hiện tượng**: Run upload avatar báo lỗi `Avatar file not found in folder: D:\video goc\<folder>`. Thư mục video gốc có clip MP4 nhưng thiếu file ảnh đại diện `avatar.jpg`.
  * **Xử lý Coordinator T0 O(1)**:
    1. Kích hoạt ngay script sinh avatar đại diện YOLOv8:
       `python D:/Taadaa/Tiktok-video/scripts/_make_avatar.py <folder> --source-root "D:/video goc"`
       Script sẽ tự động extract frame đẹp nhất từ các video có sẵn, crop chuẩn tỷ lệ vuông và lưu vào `<folder>/avatar.jpg` trong vài giây.
    2. Chạy ngay Canary Avatar Smoke trên máy thật:
       `echo AVATAR-SMOKE | D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe D:/Taadaa/Tiktok-video/scripts/run_workflow_cli.py --config D:/CodexRuntime/tiktok-video/config-machine-62.yaml --workflow-workbook D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx --machine <M> --avatar-smoke --force-avatar-upload --force-avatar-machines <M> --no-dry-run`
    3. Xác nhận kết quả nguyên tử: Sổ `Tik<N>.xlsx` tự động ghi `Avatar = OK`, artifact sinh `avatar-uploaded-confirmed.png` xác thực bằng WinRT OCR.
- [AVATAR_PLACEHOLDER_HASH_COLLISION / Bẫy Trùng Avatar Do Copy Placeholder Giữa Các Folder Video]:
  * **Hiện tượng**: User thắc mắc: *"Ủa từ từ. Mặt thằng này đang dùng cho nick máy 1 row 1 rồi mà. Có bị trùng kênh không vậy?"*.
  * **Căn nguyên thực tế**: Kênh video không hề trùng nhau (clip khác biệt 100%), nhưng file `avatar.jpg` trong các folder khác nhau bị TRÙNG HASH MD5 (ví dụ cùng hash `4ff32d59bb9937afaf85cf62e3b2d24c` với Folder 1 do lịch sử copy placeholder hàng loạt ngày 16/08). Khi cập nhật video mới mà chưa chạy `_make_avatar.py` thì uploader bốc avatar cũ mang mặt người nấu ăn up cho kênh thú cưng.
  * **Triage & Xử lý O(1)**:
    1. Kiểm tra đối soát hash MD5 giữa `D:/video goc/1/avatar.jpg` và `D:/video goc/<folder>/avatar.jpg`.
    2. Kích hoạt `python D:/Taadaa/Tiktok-video/scripts/_make_avatar.py <folder> --source-root "D:/video goc"` để sinh avatar mới trích xuất từ chính video của folder đó.
    3. Đồng bộ vào cả `D:/video goc/<folder>/avatar.jpg` và `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg`.
    4. Chạy lại runner với `-ForceAvatarMachineList "<M>"` để ép upload thay thế avatar mới trên nick. Chi tiết: `references/milestone-popup-and-avatar-edit-contract.md`.
- `[Watchdog Database Snapshot Desync vs Workbook Ground Truth (Avatar False Alarm)]`:
  * **Hiện tượng**: Watchdog `post_evening_avatar_watchdog.py` báo máy dính lỗi avatar (ví dụ: `AVATAR_EDIT_OPEN_FAILED`), nhưng khi kiểm tra file Excel `Tik<N>.xlsx` thì cột Avatar đã mang giá trị `'OK'`.
  * **Nguyên nhân**: Watchdog truy vấn bảng `snapshots` trong `D:/Taadaa/data/tiktok_tracker.db`. Nếu máy từng chuyển đổi hoặc dính vết nick cũ/phụ (parasite account) chưa up avatar, query snapshot sẽ trả về `has_avatar == 0` và gắn nhãn máy là chưa up.
  * **Triage O(1)**: Chạy script chuẩn hóa đối soát trực tiếp sổ cái:
    `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/<host>.yaml" python D:/Taadaa/Tiktok-video/scripts/resolve_avatar_pending_machines.py <tik>`
    Nếu máy không nằm trong output pending của script, khẳng định máy đã có Avatar từ trước (False Alarm), không cần chạy lại.
- `[Dashboard Badge Desync vs Workbook Ground Truth (Lệch Slot Tik Dashboard & Chống Báo Ẩu "Excel Tráo Đổi")]`:
  * **Hiện tượng**: Dashboard web (`kibe:1905`) hiển thị badge `M<Máy> · T<X>` (ví dụ: `M69 · T8`), nhưng trong file Excel tài khoản lại thuộc file `Tik<Y>.xlsx` (ví dụ: `Tik7.xlsx`) và User thắc mắc *"Ủa trên này ghi Tik 8 mà sao lại ở Tik 7?"* hoặc *"Mà sao excel lại tráo đổi v?"*.
  * **Căn nguyên thực tế**: Master Excel (`taikhoan_dat_v2_updated .xlsx`), `taikhoan_run_safe.xlsx` và `Tik*.xlsx` **KHÔNG HỀ tráo đổi**, luôn tuân thủ công thức toán học bất di bất dịch $\text{Slot (Tik)} = \text{STT} \pmod 8$. Lệch là do database `farm_account_info` trong SQLite `tiktok_tracker.db` khi crawler nạp nick ban đầu đã ghi nhận theo **thứ tự thời gian tạo nick** thay vì tính theo STT $\pmod 8$, dẫn đến Dashboard hiển thị sai badge Tik.
  * **Kỷ luật ứng xử & Xử lý O(1)**:
    1. CẤM TUYỆT ĐỐI phán bừa *"do Excel bị tráo đổi"*; luôn khẳng định Master Excel và safe workbook là **Ground Truth (chân lý vận hành)**.
    2. Cập nhật đồng bộ ngay bảng `farm_account_info` trong SQLite:
       - Xử lý lẻ O(1): `UPDATE farm_account_info SET tik = <Y>, updated_at = datetime('now', 'localtime') WHERE username = '<username>';`
       - Đồng bộ chuẩn toàn farm từ File Tổng Master: `python D:/Taadaa/tools/sync_farm_account_info.py` (tự động backup DB và nắn chuẩn 100% mapping của Kibe + Admin theo STT mod 8 từ `taikhoan_dat_v2_updated .xlsx`).
    3. Giải thích trực tiếp nguyên nhân do database tracking lưu vết import theo thời gian tạo nick cũ ngày 17/09. Chi tiết: `references/milestone-popup-and-avatar-edit-contract.md`.
- `[proxy watcher readiness was not published after reboot / ATX_SESSION_UNAVAILABLE]`:
  * **Hiện tượng**: Sau khi máy kích hoạt soft reboot (`=== SOFT REBOOT RECOVERY (AUTOMATION-CORE) ===`), workflow kẹt và văng lỗi `Guarded reboot recovery failed: proxy watcher readiness was not published after reboot: proxy readiness timed out for <serial>`.
  * **Căn nguyên**:
    1. Kernel sinh `boot_id` mới sau reboot; `automation_core/readiness.py` chờ watcher ghi trạng thái `proxy_ready` cho `boot_id` mới vào `~/.codex/device-readiness/<serial_hash>.json`. Nếu không có watcher tiến trình nền đang chạy, hàm timeout sau 90-180s.
    2. Reboot làm chết tiến trình `atx-agent` trên port 7912 của điện thoại, khiến lần dump XML kế tiếp trả về độ dài 0 byte (`ATX_SESSION_UNAVAILABLE`).
  * **Triage & Khắc phục O(1)**:
    1. Kiểm tra mạng thiết bị: `adb -s <serial> shell "ping -c 2 8.8.8.8"`.
    2. Đọc boot_id và publish proxy ready ngay lập tức:
       `boot_id = adb.shell(["cat", "/proc/sys/kernel/random/boot_id"])`
       `mark_proxy_state(serial, "proxy_ready", boot_id=boot_id)`.
    3. Hồi sinh daemon atx-agent: `adb -s <serial> shell "/data/local/tmp/atx-agent server -d"`.
    4. Chi tiết: `references/milestone-popup-and-avatar-edit-contract.md`.
- `[account row N is empty / script-blocker]`: Khi batch alert báo nhiều máy bị `script-blocker` hoặc `Bỏ qua` do `account row N is empty (no username)`, đây là cơ chế fail-safe của `tiktok_runner.py` khi slot tương ứng trong `taikhoan_run_safe.xlsx` bị trống. Slot N (1..8) được map theo Folder Video: `(Folder - 1) % 8 == target_slot`. Triage & On-Demand Auto-Reg:
  1. Kiểm tra mapping slot và kho mail bằng preflight check: `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/<host>.yaml" python D:/Taadaa/tools/ensure_row_accounts.py <N> --dry-run`.
  2. Bỏ cờ `--dry-run` để script tự động bốc mail có sẵn trong `gmail_clean_v2.xlsx` (hoặc mua Hotmail bù nếu thiếu) rồi reg TikTok qua `_run_all_targets.py` và sync ngược lại safe workbook. Lưu ý: runner preflight chỉ chạy auto-reg khi thiết bị online ADB.
  3. CẢNH BÁO LỆCH ĐỒNG BỘ SAFE WORKBOOK (Multi-Cluster Safe Sync Pitfall): Nếu sổ gốc `taikhoan_dat_v2_updated .xlsx` của cluster (như Admin) đã cập nhật nick mới nhưng safe workbook chưa được đồng bộ (do cron sync chỉ chạy cho Kibe), runner sẽ nhìn thấy slot bị trống giả (false empty). BẮT BUỘC build đồng bộ lại safe workbook từ sổ gốc trước khi reg bù. Khi gọi `sync-safe-workbook.py`, KHÔNG truyền file `.xlsx` vào `--series-file` (sẽ gây lỗi `UnicodeDecodeError` do script đọc file text), chỉ truyền file text chứa serial hoặc bỏ qua `--series-file` để script tự suy luận serial an toàn.
  4. ĐỒNG BỘ DUAL-CLUSTER VÀO CRON: Cronjob `taikhoan-run-safe-sync` (`scripts/hermes_taikhoan_sync_cron.py`) bắt buộc cấu hình danh sách `SYNC_CLUSTERS` hỗ trợ cả Kibe và Admin để tự động phát hiện thay đổi trên cả 2 sổ gốc và sync kịp thời sang `taikhoan_run_safe.xlsx`, tránh runner hiểu nhầm là trống nick.
  5. ĐIỀU KIỆN MÁY ONLINE TRƯỚC BATCH REG: Preflight auto-reg yêu cầu thiết bị phải online qua ADB. Nếu gặp sự cố vật lý (như rớt cáp USB Hub 20 cổng dải M261-M280), preflight sẽ chỉ chạy reg an toàn cho các máy đang online; các máy offline phải được cắm lại cáp trước khi reg bù.
- `[MACHINE_FULL_8_ACCOUNTS / Lệch Excel - Cần kiểm tra backfill]`: Xảy ra khi preflight (`ensure_row_accounts.py <row>`) thấy slot Row N trong `taikhoan_run_safe.xlsx` bị trống (`None`), kích hoạt batch reg bù nhưng bị văng `[04_add_account] MACHINE_FULL_8_ACCOUNTS`.
  * **CẢNH BÁO BẪY FALSE ALARM (MÁY CHỈ MỚI CÓ 7 ACC)**: Khi máy có 7 acc, danh sách accounts chiếm trọn màn hình (~1700px), đẩy nút "Thêm tài khoản" xuống đáy/ngoài viewport. Nếu script không cuộn (`swipe up`) và bộ đếm `_acc_count` đếm gộp cả layout container (`lli`) lẫn text (`ng8`), script sẽ ngộ nhận máy đã full và văng lỗi sai. Cần sửa logic `tap_add_account`: cuộn bottom sheet (`swipe(540, 1500, 540, 800, 400)`) khi chưa thấy nút và dùng tập hợp `_account_names = set()` chỉ đếm username thật. Chi tiết & fix: `references/machine-full-8-accounts-bottom-sheet-overflow.md`.
  * **CẢNH BÁO BẪY "OFF-GRID FOLDER" GÂY REJECT DUPLICATE & DUAL HARD GUARD**: Khi nick thứ 8 đã được reg thành công nhưng bị gán số Folder ngoài dải chuẩn `base..base+7` (ví dụ M209 base 65..72 nhưng ghi Folder 74, hoặc M256 base 441..448 ghi Folder 449, 450): `(Folder-1)%8` bị lệch slot đè lên nick cũ, bỏ trống các slot khác thành `None`/`MISSING_ID`.
    - **Căn nguyên code**: Trong `deferred_tracking_writer.py`, hàm `_allocate_tracking_row` từng dùng `tik = (max(used_tik) + 1)` khiến máy có folder > 8 tự động tăng tuyến tính thoát khỏi dải 8 slot của máy và lấn sang máy kế tiếp.
    - **Dual Hard Guard**: (1) `_allocate_tracking_row` tính `base = ((stt-201) if stt>=200 else (stt-1))*8 + 1`, chỉ bốc slot thiếu trong `canonical_folders = [base..base+7]`, đủ 8 slot thì trả `None, None`. (2) `_check_expected_row` chặn đứng ghi workbook nếu `expected_tik` không thuộc `1..8` hoặc `base..base+7` (`OFF_GRID_FOLDER_<tik>_FOR_STT_<stt>_BASE_<base>`). (3) `avatar_after_reg.py` dùng đúng `(stt-201)*8 + 7` cho Admin. Chi tiết: `references/preflight-reg-bu-row-email-exhaustion-triage.md`.
  * **CẢNH BÁO BẪY DUAL-CLUSTER REMOTE ADB_SERVER_SOCKET LEAK**: Khi dispatch batch trên máy điều phối Kibe sang cụm Admin (`HOST_ID="admin"`), nếu môi trường cha có `ADB_SERVER_SOCKET="tcp:localhost:5037"`, script con KHÔNG được dùng `if "ADB_SERVER_SOCKET" not in env` vì sẽ giữ nguyên socket local Kibe, dẫn đến lỗi `device '<serial>' not found` và sập `[01_open] TikTok not foreground`. BẮT BUỘC ghi đè: `env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"`.
  * **Triage bắt buộc**: (1) Trích xuất ảnh dropdown `screenshots_social/<STT>_03_dropdown_*.png`. (2) Chạy WinRT OCR đếm số username: nếu chỉ có 7 username và Excel cũng có 7 acc -> False Alarm (cần swipe cuộn bottom sheet trong `tap_add_account` và chuẩn hóa `_account_names = set()`). (3) Nếu OCR đọc được đủ 8 username khác nhau -> Lệch Excel thật sự: truy vết UID từ OCR, đối soát backup, tra cứu `tracking_result_stt<STT>_*.json` trong runtime, rà soát bẫy xáo trộn slot (Slot Displacement - nick cũ bị đẩy khỏi Excel khi nick mới chèn đè, để lại slot cuối `None`), backfill đồng bộ 4 nơi (`taikhoan_dat_v2_updated .xlsx` -> `taikhoan_run_safe.xlsx` -> `TikN.xlsx` -> `tiktok_tracker.db`). BẮT BUỘC: Trước khi ghi UID vào Master, phải quét toàn bộ Master Sheet đảm bảo UID chưa từng tồn tại ở máy khác (do tàn dư nick ký sinh từng logout); nếu có phải clear dòng cũ ngay để tránh bẫy duplicate invariant. Lưu ý lưu Excel trực tiếp `wb.save(path)` để tránh lỗi `PermissionError [WinError 5]` do OneDrive lock atomic rename `.tmp.xlsx`. Sau khi backfill, bắt buộc chạy `excel_preflight_validator.py --exit-on-error` xác nhận 0 lỗi. (4) Rà soát toàn farm an toàn O(1) theo quy trình tại `references/machine-full-8-accounts-bottom-sheet-overflow.md` (cấm wildcard quét sâu trên runtime). (5) Xác minh bằng `ensure_row_accounts.py <row> --dry-run`.
- `[Dual-Cluster Batch Alert Sibling Timestamp Desync (False "Admin Did Not Run" Alarm)]`:
  * **Hiện tượng**: Telegram bắn cảnh báo `[BATCH ALERT: LỖI HỆ THỐNG] ... 【FARM KIBE - MÁY 1-80】` (không có chữ Admin / Toàn Farm), khiến người vận hành tưởng rằng cụm Admin bị bỏ qua hoặc không chạy ("Ủa sao không chạy bên admin?").
  * **Nguyên nhân gốc rễ**: Khi `run-feed-session.ps1` kết thúc, nó gọi `batch_aggregator.py "$targetBatchDir" --telegram`. Hàm `find_sibling_batch_dir()` ghép 2 cụm (`kibe` <-> `admin`) bằng cách thay thế trực tiếp chuỗi tên đường dẫn. Tuy nhiên, nếu 1 trong 2 cụm bị trễ xuất phát (ví dụ: Admin phải đợi 15-20 phút để script preflight `ensure_row_accounts.py` reg bù nick), thì tên thư mục timestamp con (ví dụ: `20260929-001707`) sẽ khác với timestamp của Kibe (`20260929-000252`). Do đó `find_sibling_batch_dir()` trả về `None`, khiến `batch_aggregator` bóc tách thành alert đơn lẻ của Kibe thay vì gộp tiêu đề `【TOÀN FARM】`.
  * **Triage bắt buộc O(1)**: CẤM vội kết luận Admin không chạy hay đóng băng phiên! Kiểm tra ngay `D:/Taadaa/runtime/admin/live/<date>/<window_folder>/` và `feed_session_reported.json`. Thực tế cả 2 cụm đều đã chạy xong và báo cáo tổng kết phiên (`feed_session_watchdog.py`) vẫn được gửi độc lập cho cả 2 cụm.
- `[Cross-Cluster Clear-Cache Hardcoded Path Leak (Admin Silent Exit)]`:
  * **Hiện tượng**: Cronjob `end-of-day-clear-tiktok-cache` trên Admin chạy định kỳ mỗi 10 phút nhưng luôn trả về `silent (empty output)` và không dọn dẹp cache cho máy Admin (201-280).
  * **Nguyên nhân gốc rễ**:
    1. Trên máy Admin: Script `cron_clear_tiktok_cache.py` bị hardcode đường dẫn của Kibe: `TIK1_WORKBOOK = r"D:\OneDrive\TaadaaData\kibe\Tik1.xlsx"` (dẫn đến nạp máy 1–80 thay vì `admin\Tik1.xlsx` máy 201–280).
    2. Hàm `is_ca4_finished()` kiểm tra file `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json`. Do Admin lưu runtime riêng (`D:\Taadaa\runtime\admin\cron-state\`), đường dẫn `kibe` không tồn tại trên Admin khiến `is_ca4_finished()` trả về `False` -> script tự động thoát im lặng (`return 0`) mọi tick.
    3. Trên Kibe: Script `cron_clear_tiktok_cache.py` chỉ quét ADB local, chưa hỗ trợ Remote ADB Socket `192.168.110.119:5037` sang Admin.
  * **Triage & Fix**:
    - Khi triển khai cron độc lập trên Admin: BẮT BUỘC dùng `TAADAA_HOST_ID` hoặc đọc `TAADAA_HOST_CONFIG` (`machine-config\admin.yaml`) để ánh xạ `runtime_root` và `Tik1.xlsx` về đúng folder `admin`, hoặc Kibe điều phối tập trung dọn cache song song cho cả 2 cụm qua Remote ADB Socket. Kiến trúc chuẩn: xem `taadaa-farm-ops-rules/references/dual-cluster-farm-architecture.md`.
- `[Context Steering Discipline: Chống ngáo Session khi nhận câu hỏi ngắn / "???"]`:
  * Khi User hỏi ngắn hoặc thắc mắc trạng thái ("Ủa sao k chạy bên admin?", "Chạy chưa?"), BẮT BUỘC kiểm tra ngữ cảnh tin nhắn hoặc báo cáo cron gần nhất ngay trước câu hỏi (ví dụ: vừa có báo cáo `end-of-day-clear-tiktok-cache` thì câu hỏi là về clear-cache, không được nhảy bổ vào phân tích feed session hay reg bù).
  * **Khi User gửi "???" hoặc dấu hỏi chấm cụt ngủn**: Đây là tín hiệu báo động đỏ (Red Flag) cho thấy Agent vừa có phát ngôn sai lệch thực tế, kết luận vội vàng không có bằng chứng, hoặc mất ngữ cảnh session. TUYỆT ĐỐI CẤM trả lời bằng các câu chào hỏi rỗng tuếch kiểu chatbot mới ("What do you need help with?", "Looks like you're in an empty workspace..."). BẮT BUỘC ngay lập tức: (1) Rà soát alert/lệnh gần nhất, (2) Kiểm tra thiết bị/hiện trường thực tế O(1) qua `inspect_machine.py` và screenshot `MEDIA:`, (3) Đính chính rõ ràng xem đó là lỗi thật hay False Alarm (như trường hợp M73 dính PlayCore popup bị gán nhãn nhầm là mất phiên).
- `[Google/GMS/account screen focused during profile preflight / PlayCore Popup]`: **RẤT THƯỜNG LÀ FALSE POSITIVE** cho "mất phiên / văng account". Xảy ra khi Google Play Store (`com.android.vending`) bung popup yêu cầu tải tệp bổ sung (PlayCore split APK / feature delivery: *"TikTok cần tải các tệp bổ sung xuống để thêm tính năng vào ứng dụng..."*). Khi đó `verify_tiktok_focus` phát hiện focus bị chiếm bởi `com.android.vending` nên gắn cờ dừng an toàn.
  * **Căn nguyên cốt lõi (Thiếu Split APKs < 50 file)**: Khi máy chỉ cài 5 split APK cơ bản thay vì đủ 55-67 splits, thư viện PlayCore trong TikTok sẽ liên tục gọi Google Play đòi tải các dynamic modules (player, search, live_cast...).
  * **4 Bẫy tử huyệt Watchdog Tự Nạp (`farm_app_provision_watchdog.py`)**:
    1. `REQUIRED_APPS` bị hardcode chỉ 5 file split thay vì gom toàn bộ 65+ `.apk` trong thư mục version.
    2. `pm list packages` chỉ check tên gói mà không đếm `pm path com.ss.android.ugc.trill` (bắt buộc `>= 50` splits).
    3. Regex `\b(\d+)\b` trong file lock JSON bắt nhầm `"machine": N` thay vì `"pid": PID`.
    4. **Nghẽn băng thông USB Hub 20 cổng**: Nạp đồng thời 20+ máy gói 280MB làm nghẽn bus USB, sập socket ADB (`device offline`). BẮT BUỘC giới hạn `max_workers <= 5` khi nạp APK nặng.
    5. **Bẫy Rò Rỉ Ngôn Ngữ ROM & Cưỡng Chế vi-VN Liên Tục**: ROM của một số máy trên farm để mặc định tiếng Đức (`de-AT`) hoặc Anh (`en-US`), khiến TikTok tự đổi giao diện sang tiếng nước ngoài (xuất hiện header `+ Namen hinzufügen`, dialog `Add your preferred name`...). Watchdog tự nạp BẮT BUỘC bổ sung `["setprop", "persist.sys.locale", "vi-VN"]` và `["settings", "put", "system", "system_locales", "vi-VN"]` vào `POST_CONFIG_COMMANDS`. Kể cả máy đã đủ app, watchdog khi quét máy rảnh vẫn phải chạy `apply_post_config` để ép lại Tiếng Việt và tắt màn hình (`keyevent 223`).
  * **Triage O(1) & Nạp an toàn**:
    1. Kiểm tra XML/screenshot tại artifact: nếu thấy nút "Đóng hộp thoại cập nhật" hoặc "Tải xuống qua Play" -> Khẳng định tài khoản TikTok an toàn 100%, không bị logout.
    2. Kiểm tra số lượng split: `adb -s <serial> shell pm path com.ss.android.ugc.trill | wc -l`.
    3. Nạp an toàn giữ data: `adb -s <serial> install-multiple -r -d base.apk split_*.apk` (bắt buộc `base.apk` xếp đầu).
    4. Auto-dismiss trong runner: Handler `playcore_acquisition_dialog` (Priority 79) trong `benign_popup_registry.py` click nút đóng `content-desc="Đóng hộp thoại cập nhật"` hoặc BACK trong 1s.
    5. Sau nạp: BẮT BUỘC `am force-stop`, về HOME (`keyevent 3`) và tắt màn hình (`keyevent 223`).
    6. **Kỷ luật điều phối & Canary Gate**: Quyền tự nạp đã được ủy quyền sẵn, CẤM dừng lại hỏi xin phép ("Có muốn nạp không?"). Kích hoạt watchdog 5 phút/lần (`*/5 * * * *`) gửi alert Telegram tự hành. Sau khi vá lỗi popup/navigation, BẮT BUỘC chạy ngay 1 Canary test trên máy thật (`feed-swipe-smoke`), chụp ảnh `MEDIA:` và chạy WinRT OCR kiểm chứng 100% tiếng Việt chuẩn trước khi báo hoàn tất. Chi tiết: `references/tiktok-live-otp-and-playcore-popup-handlers.md`.
- `[Cross-Cluster App Version Alignment & Script Resilience (Admin v46 vs Kibe v47)]`: **CẢNH BÁO BẪY ĐỔ LỖI LỆCH PHIÊN BẢN APP**: Khi một cụm farm chạy phiên bản app khác với cụm còn lại (ví dụ Admin chạy v46.6.3, Kibe chạy v47.0.3), TUYỆT ĐỐI CẤM vội kết luận kịch bản bị crash hay lỗi do đổi phiên bản app.
  * **Bản chất kỹ thuật (Version-Agnostic Architecture)**: Runner TikTok sử dụng nhận diện mềm dựa trên text/regex đa ngôn ngữ (`Hồ sơ / Profile / Tôi`, `Home / Trang chủ / Für dich`), widget class Android generic (`TextView`, `FrameLayout`), và tọa độ vuốt tương đối theo tỷ lệ màn hình máy (`1440x2560`), do đó hoàn toàn không phụ thuộc vào ID nội bộ của riêng bản app nào.
  * **2 Bẫy Dừng Runner Thường Bị Hiểu Nhầm Do Đổi Bản App & Căn Nguyên Lệch Hàm Đã Viết**:
    1. **Bẫy va chạm nút `+ Thêm tên` & Lệch ngôn ngữ trong hàm `_detect_edit_name` (M213, M268)**: User đã viết sẵn hàm `make_tiktok_name` và `_detect_edit_name` nhưng hàm chỉ kiểm tra chuỗi tiếng Việt (`"thêm tên bạn mong muốn"`). Khi nick chưa có Display Name và app chạy tiếng Anh (`"Add your preferred name"`, `"Your name can only be changed once every 7 days"` / tiếng Đức `+ Namen hinzufügen`), hàm detect trả về `False` -> văng `unknown TikTok state` -> `manual-needed`. (Khắc phục: Thêm từ khóa tiếng Anh/Đức vào `_detect_edit_name` và `is_excluded_name`).
    2. **Bẫy Khám phá bạn bè trong Tab "Bạn bè" & Lệch vị trí kích hoạt Fallback (M232, M249)**: User đã viết sẵn hàm `_has_friends_feed_content` và `empty_feed_fallback_for_you` nhưng đặt ở trong vòng lặp vuốt (`swipe loop`). Khi chuyển tab, bước `switch_friends_N_navigation_confirm` thấy banner bạn bè rỗng bị `classify_screen` gắn nhãn `manual-needed:popup` (`contact_follow_suggestion`). Sau khi dismiss popup bị rơi về For You, `navigation_confirm` so sánh lệch expected/detected nên dừng ngay trước khi kịp bước vào swipe loop để gọi fallback. (Khắc phục: Cho phép `switch_friends_N_navigation_confirm` chuyển hướng thẳng sang `empty_feed_fallback_for_you` khi gặp content bạn bè rỗng).
  * **Kỷ luật nâng cấp Remote Cluster qua LAN ADB**: CẤM tự ý nạp đè APK qua Remote ADB LAN (`192.168.110.119:5037`) khi bản hiện tại vẫn chạy ổn định (tỷ lệ thành công >= 85%). Chi tiết: `references/tiktok-live-otp-and-playcore-popup-handlers.md`.
- `[login/account screen detected on TikTok LIVE stream (resource-id OTP false positive)]`: **RẤT THƯỜNG LÀ FALSE POSITIVE** cho "mất phiên / văng account" khi lướt feed. Khi swipe vào phòng LIVE, TikTok có thể render view nội bộ mang resource ID chứa chuỗi `"otp"` (ví dụ: `com.ss.android.ugc.trill:id/otp` với text="1" cho rank/vote). Nếu bộ phân loại kiểm tra `strong_terms = ("manual_challenge", "captcha", "otp")` trên toàn bộ giá trị (gồm cả resource-id) trước khi kiểm tra màn hình LIVE, nó sẽ ngộ nhận đây là màn hình nhập mã OTP và dừng feed với nhãn `manual-needed:login`.
  * **Triage O(1)**: Kiểm tra XML tại artifact `swipe_X_after`. Nếu màn hình đang hiển thị livestream và text không chứa từ khóa đăng nhập thật sự ("đăng nhập", "mật khẩu", "sign in", EditText) -> Tài khoản hoàn toàn bình thường, chỉ là false positive detector.
  * **Giải pháp cốt lõi (Text-Only Regex Gate)**: Trong `automation-core/src/automation_core/tiktok/benign_popup.py`, hàm `has_sensitive_marker()` BẮT BUỘC chỉ quét từ khóa nhạy cảm trên visible text / content-desc (`element.text`, `element.content_desc`), tuyệt đối không quét trên obfuscated resource-id hash ngẫu nhiên của TikTok (như `id/otp`, `id/otq`), và bắt buộc dùng regex `\botp\b` cho từ khóa OTP. Chi tiết: `references/tiktok-live-otp-and-playcore-popup-handlers.md`.
- `[manual-needed-popup: User Profile Mutual Friends False Positive vs Share Sheet Loop]`:
  * **Hiện tượng**: Farm alert báo `[BATCH ALERT: LỖI HỆ THỐNG]` nhiều máy bị `manual-needed-popup:manual-needed:popup remained after allowed shared dismiss attempts; swipe recovery (2 swipes) still stuck`.
  * **Căn nguyên cốt lõi**: Khi lướt feed gặp gợi ý tài khoản hoặc tap profile, app điều hướng vào trang Profile người dùng khác (`@username`). Trên profile có text bạn chung (`"Bạn bè với..."`) và nút `"Follow"`. Bộ nhận diện `detect_contact_follow_suggestion` trong `automation-core/src/automation_core/tiktok/benign_popup.py` nhận nhầm đây là popup gợi ý kết bạn danh bạ. Khi cố dismiss, do profile không có nút X đóng, cơ chế fallback `_close_candidate` chọn nhầm icon ImageView 3 chấm menu ở góc trên bên phải (`bounds=[948,96][1056,204]`), làm bật lên TikTok Share Sheet. Khi đóng Share Sheet bằng phím Back, máy quay lại profile và lại bị nhận nhầm là popup -> mở lại Share Sheet liên tục -> vượt quá số lần thử dismiss cho phép -> ném `manual-needed-popup`.
  * **Triage & Xử lý O(1)**:
    1. Trong `detect_contact_follow_suggestion`: Bổ sung điều kiện loại trừ dứt điểm trang Profile người dùng nếu phát hiện các chỉ dấu profile (`"follower"`, `"followers"`, `"người theo dõi"`, `"sửa hồ sơ"`, `"edit profile"`, `"chia sẻ hồ sơ"`, `"share profile"`).
    2. Bổ sung structured telemetry logging (`logger.debug("detect_contact_follow_suggestion: skipping profile screen matching marker")`) để theo dõi và đạt điểm Telemetry & Observability trong Sol Closeout Gate (>= 85/100).
    3. Bổ sung unit tests cho cả trường hợp Profile (loại trừ) và Contact Suggestion thật sự (giữ nguyên).
    4. **Kỷ luật Dispatch Subagent (`delegate_task`)**: Khi dispatch task điều tra/sửa chữa, BẮT BUỘC thêm vào context: `BUDGET: <= 5 tool calls, thời gian < 3 phút. Trả về kết luận/anchor rồi THOÁT NGAY` để tránh bị chặn bởi guardrail `[HARD GATE #3 - INVESTIGATE ROUTE]`.
    5. Chi tiết: `references/user-profile-mutual-friends-popup-loop.md`.
- `[Feed Video Caption / News Text Verification False Positive vs Captcha False Alert]`:
  * **Hiện tượng**: Telegram Farm Alert bắn `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện N máy gặp captcha/xác minh (chưa mất phiên)` kèm stop_reason `verification marker detected` hoặc `manual-needed:verification`, dù máy đang lướt feed bình thường.
  * **Căn nguyên cốt lõi (Bẫy từ khóa trong phụ đề / mô tả video tin tức & Heuristic độ dài chuỗi)**:
    - Khi lướt feed gặp video tin tức, phóng sự điều tra (ví dụ video về công an, tòa án, bạo hành: *"Quá trình điều tra xác minh, Cơ quan Công an đã tiến hành..."*).
    - Trong `classifier.py`, hàm `_is_manual_challenge_match(value)` quét thô trên toàn bộ mảng `texts` và `descs`. Node mô tả video (`com.ss.android.ugc.trill:id/tvw_desc`) dài hàng ngàn ký tự (như M251 dài 2.364 ký tự) chứa cụm từ `"xác minh"` -> ngộ nhận thành `manual_challenge_terms` và dừng feed với nhãn `manual-needed:verification`.
  * **Triage bắt buộc O(1) & Khắc phục chuẩn**:
    1. Trích xuất screenshot và chạy WinRT OCR (`from validate_evidence_screen import run_winrt_ocr` trên `screen.png`).
    2. Nếu OCR thấy xuất hiện 5 tab điều hướng dưới cùng (*Trang chủ, Cửa hàng, +, Hộp thư, Hồ sơ*) hoặc cấu trúc video player (icon Like, Comment, Share, hashtag `#xuhuong`): Khẳng định ngay **100% FALSE POSITIVE**, tài khoản hoàn toàn không bị captcha hay checkpoint.
    3. **Quy chuẩn Code Fix trong `classifier.py`**:
       - Captcha / Verification của TikTok chỉ là title dialog hoặc button ngắn (thường < 40–80 ký tự). CẤM TUYỆT ĐỐI cho phép chuỗi dài > 80 ký tự kích hoạt `manual_challenge`.
       - Riêng từ `"xác minh"` / `"Xác minh"` đơn lẻ nếu nằm trong câu dài > 40 ký tự thì bắt buộc bỏ qua (coi là caption/mô tả văn bản đời thường).
       - Bổ sung structured telemetry log: `logger.debug("[CLASSIFIER_CHALLENGE_BYPASS] event=challenge_keyword_bypassed reason=text_length_or_caption length=%d prefix=%s", len(value), value[:40])` để đảm bảo điểm Telemetry & Observability trong Sol Reviewer Gate (>= 85/100).
       - Bổ sung bộ đôi unit tests: test caption dài không bị match (tránh false positive) và test prompt xác minh ngắn ("Xác minh để tiếp tục") vẫn kích hoạt chuẩn (tránh false negative).
- `[Feed Session Failure vs Upload Hook Permission (Feed Fail Vẫn Cho Phép Upload)]`:
  * **Quy tắc thiết kế bất biến của Farm**: **CHO PHÉP UPLOAD VIDEO KỂ CẢ KHI FEED SESSION THẤT BẠI** (feed swipe dính timeout hay dừng sớm vẫn được quyền upload video theo lịch). TUYỆT ĐỐI CẤM chặn upload toàn bộ chỉ vì feed không đạt status success, và **CẤM TUYỆT ĐỐI thêm `manual-needed` vào `_SENSITIVE_STOP_WORDS`** (vì hầu hết feed thất bại đều dừng với stop_reason `manual-needed:...`, việc nhét `manual-needed` vào sensitive stop words sẽ bóp nghẹt quyền upload hợp lệ của các máy feed fail).
  * **Chốt chặn duy nhất ngăn Upload**: CHỈ KHI PROXY / VPN BỊ LỖI MẠNG (timeout, rớt kết nối) thì upload script mới được fail-closed ngay tại preflight (`require_android_vpn` trong `run_post.py`) để chống rò IP thật. Tránh tuyệt đối việc nhầm lẫn giữa lỗi feed và lỗi mạng proxy.
- `[Proxy / VPN Egress Timeout vs Fake Captcha/Challenge Alert Trap & Inline Error Formatting]`:
  * **Hiện tượng**: Telegram alert bắn mục `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện N máy gặp captcha/xác minh (chưa mất phiên)` kèm chuỗi lỗi `egress IP verification failed: ... GET /ip HTTP/1.1 Host: ifconfig.me ... context deadline exceeded`, xả nhiều dòng trống và raw HTTP headers làm loãng chat.
  * **Căn nguyên**:
    1. Trong `batch_aggregator.py`, `CHALLENGE_KEYWORDS` chứa từ khóa `"verification"`. Chuỗi `"egress IP verification failed"` bị khớp nhầm chữ `"verification"` nên bị phân loại thành lỗi Captcha/Challenge.
    2. Tin nhắn Telegram format trực tiếp `error_message` mà không gọt khoảng trắng / newlines khiến toàn bộ header HTTP dump bị in ra nhiều dòng.
  * **Xử lý chuẩn**:
    1. Bổ sung `"ip verification"`, `"verification failed"`, `"egress"`, `"proxy"`, `"vpn"` vào `CHALLENGE_EXCLUSIONS`.
    2. Dùng `_format_inline_error` gọt sạch newlines (`' '.join(text.split())`) và giới hạn độ dài `max_len=160`.
- `[Git Push Timeout via GitHub CLI Auth Helper (HTTPS_PROXY Env Workaround)]`:
  * Khi mạng trực tiếp từ host Windows tới `github.com` bị nghẽn/timeout, lệnh `git push` bị treo do `gh.exe auth git-credential` và kết nối git không thông.
  * Khắc phục tức thì: Export `HTTPS_PROXY="http://192.168.110.2:20012" HTTP_PROXY="http://192.168.110.2:20012"` trước khi chạy `git push` để cả `git` lẫn `gh.exe` đều đi qua proxy farm ổn định.

Ask only at the four gates above. Unrelated dirty files are not a reason to refuse an exact-scope commit/push; preserve and never stage them.

## Partial-diff recovery after worker timeout

A worker transport/API timeout is **TRANSIENT**, but the worker may have written a valid partial diff before timing out. Immediately after the timeout:

1. Inspect only the task allowlist with `git status --short`, `git diff --stat`, `git diff --numstat`, and the focused diff; never reset/revert the worker's changes or clean unrelated dirty paths.
2. Classify the diff before retrying: valid partial patch, incomplete/unsafe patch, or no files modified. `files_modified == 0` on a Fix Code task is structural failure; a bounded partial diff is not proof of correctness but is evidence for a narrower verification lane.
3. Do not dispatch a second implementer against the same owned files while the partial diff is unresolved. Use a read-only verifier first; if the diff is exact and within the L2 budget, use the prescribed escalation rules rather than overlapping workers.
4. Require independent focused offline verification (`pytest` mocked, or `py_compile` only for syntax-only changes) before calling the task DONE. A worker summary is not evidence.
5. Keep live canary separate from code verification. If the incident artifact is missing or stale, label the live root cause `UNPROVEN`; do not manufacture a retry or canary from the alert text alone.

This prevents a timed-out worker from being mistaken for a clean failure or from leaving an unreviewed patch silently in the shared workspace.

## Worker timeout discipline

### Timeout handoff and partial-diff verification

A worker timeout is not permission to wait indefinitely or to relaunch the same broad task. Immediately perform a coordinator-side bounded verification of the named allowlist: inspect `git status --short <paths>`, `git diff --numstat`, and the exact diff. Preserve valid worker changes and unrelated dirty paths; never revert a timed-out worker blindly. Classify the result explicitly:

- **No diff / no artifact:** structural failure; redispatch once with a narrower contract or escalate per the recovery ladder.
- **Partial diff + no test evidence:** incomplete, not DONE; run one focused offline check if the exact acceptance command is known.
- **Partial diff + focused failure:** structural regression; use the failure trace to write a different, smaller contract. Do not claim syntax success as logic success.
- **Existing fix already present in history:** verify the commit and focused test before proposing a duplicate patch; report that the incident remains live-UNPROVEN if current machine artifacts are missing.

Keep code-surgery and live-canary gates separate: offline green tests do not prove the named device incident. Do not spend repeated 15–20 minute worker lanes on a contract whose exact diff and acceptance command are already known; after the second structural timeout/failure, use L2 only when its exact-diff budget is satisfied, otherwise report evidenced BLOCKED.

### Concise status reporting

When the operator asks for a binary status (for example, “xong chưa?”), answer the status first in one line (`Chưa xong` or `Đã xong`), then list only the blocking evidence: files/diff, exact test result, live artifact/canary state, and next bounded action. Do not bury the answer in a long plan or present `py_compile` as proof of behavioral correctness.

Use the smallest lane that fits:

| Lane | Default wall clock | Contract |
|---|---:|---|
| Read-only evidence | 120s | named artifacts only; return facts/paths |
| Exact patch | 180s | one file/anchor, one focused check |
| Scoped code surgery | 300s | 1–2 files, focused test |
| Policy/docs | 240s | bounded sections, marker/diff check |
| Runtime/canary | 600s | canonical runner, one target, external evidence |
| Long batch | launcher + monitor | never one interactive worker |

A timeout is transient. First inspect the shared workspace for a partial valid diff before retrying. If unfinished, re-dispatch with a narrower contract and a different hypothesis; never repeat the same broad prompt. Require a fail-fast checkpoint within the first three iterations: anchor found, intended delta, acceptance command, or explicit abort.

## Focused verification

For policy/docs, use a deterministic offline test that reads the exact policy files and asserts state names, transition columns, bounds, gates, schema fields, closeout triggers, and scoped staging rules. Do not let a closeout runner fall back to the whole repository suite when only Markdown changed; pass the focused test explicitly or use its documented skip-test mode while preserving the independent reviewer gate.

For code, run the smallest mocked/offline test and `py_compile` where applicable before any canary. A live canary is required for device automation unless the project’s classification rule proves it is not applicable.

## Exact-scope closeout

When the user issues a command-form `chốt phiên`, `chốt`, `đóng phiên`, `xong phiên`, `kết thúc phiên`, `done`, or `wrap up`, automatically run exact-scope closeout; questions, proposals, quoted examples, status requests, and incidental mentions are not triggers. Inventory the worktree and classify each path/hunk as `OWNED`, `RELATED`, `RELATED_UNADOPTABLE`, `UNRELATED`, `EXCLUDED`, or `CONFLICT` using contract/receipt evidence; never adopt by filename, mtime, topic, or proximity alone. Resolve each owned/related group independently to DONE or evidenced BLOCKED; a blocked related group must not veto an independent completed group.

For each commit group, construct an exact candidate diff (temporary index where needed), bind the independent reviewer approval to its candidate patch SHA, recompute that SHA immediately before commit, and rehash the committed diff during reconcile. Use the configured-upstream overlap-checked SYNC/PUSH_VERIFY flow; never let the reviewer fall back to unrelated dirty diffs. Stage only the task allowlist, preserve unrelated dirty/staged/untracked paths, require reviewer exit 0 and score ≥85, then commit/push and verify remote SHA. A normal reviewed non-force allowlist push is not a paid/destructive gate.

See `references/timeout-and-closeout-recovery.md` and `references/user-profile-mutual-friends-popup-loop.md` for the incident-specific timeout, reviewer, popup loop, and closeout evidence patterns.
