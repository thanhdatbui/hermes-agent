# Farm Alert Codebase Fix & Canary Closeout Guidelines

## 1. Nguyên tắc Bắt Buộc Khi Nhận Alert [MÁY N]
1. **Cấm Can Thiệp Lệnh Shell/ADB Ngoài Chữa Cháy:**
   - Tuyệt đối không dừng lại ở việc gõ `adb reconnect`, `adb shell input`, sửa setting tay.
   - Mọi lỗi phải được bọc trong exception handling của codebase (`automation-core` / `python_runner`) để tự động nhận diện và self-heal.
2. **SCOPE LOCK (Tránh Lan Scope & Timeout):**
   - Lỗi ở đâu sửa đúng file/module gây lỗi ở đó (lỗi `automation-core` sửa `core`, lỗi flow sửa `flow`).
   - CẤM TUYỆT ĐỐI tiện tay refactor dạo sang các module không liên quan (watchdog, safety, classifier, cron...) làm phình diff và gây REJECT liên hoàn ở khâu Plan-Review.
3. **TEST LOCK (Cấm Quét Test Toàn Repo):**
   - CẤM TUYỆT ĐỐI chạy bare `pytest` trên toàn bộ monorepo (2000+ tests dính timeout 900s / 15 phút).
   - BẮT BUỘC CHỈ chạy focused tests (`pytest <test_file> -k <test_name>`) cho đúng file vừa sửa, đảm bảo thời gian test hoàn tất dưới 2 phút.
4. **Tuân Thủ Tuyệt Đối 5 Bước Recovery:**
   - **B1 (Inspect):** `python D:/Taadaa/tools/inspect_machine.py <N>`
   - **B2 (Root Cause):** Đọc log run & mở đúng flow/module phụ trách
   - **B3 (Patch Code):** Sửa codebase theo đúng SCOPE LOCK
   - **B4 (Canary Test):** Chạy canary test kiểm chứng script tự cứu máy thật. Lưu ý môi trường subprocess của Hermes Agent tự động inject `PYTHONPATH`/`VIRTUAL_ENV` trỏ vào venv của Hermes gây lỗi import binary PIL `_imaging`. Khi chạy canary test qua PowerShell/bash, bắt buộc dùng clean environment (`env -u PYTHONPATH -u VIRTUAL_ENV` hoặc `$env:PYTHONPATH=''; $env:VIRTUAL_ENV=''`) kèm cờ `-Python "C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe"`.
   - **B5 (Báo Cáo Phục Hồi Hiện Trường / Incident Recovery Report):** Báo cáo file/hàm đã sửa + kết quả canary test cho user. TUYỆT ĐỐI KHÔNG dùng nhãn "Closeout" làm user nhầm với việc đã chạy Chốt phiên 6 Gate (commit, review, rebase, push). Chỉ chạy quy trình Chốt phiên khi user ra lệnh rõ ràng.

## 2. Bài Học B3 Soft Reboot & Transient ADB Timeout Tại State CONNECT_DEVICE (Case 88)
- **Adapter Chưa Khởi Tạo Tại CONNECT_DEVICE:** Ở các state khởi tạo ban đầu, `context.adapter` chưa được khởi tạo (chỉ gán sau khi device startup thành công). Do đó các guard kiểm tra điều kiện recovery (như `_soft_reboot_recovery_allowed`) phải miễn trừ kiểm tra `self.context.adapter` cho riêng state `CONNECT_DEVICE` (chỉ yêu cầu `self.context.adb_client`), tránh vô hiệu hóa B3 Soft Reboot và đẩy máy sang `MANUAL_REVIEW` vô cớ.
- **Lazy Fallback Adapter Trong Recovery:** Khi thực thi soft reboot tại state chưa có adapter, cần lazy fallback khởi tạo `TikTokAdapter(adb_client=self.context.adb_client, ...)` và truy cập an toàn `getattr(adapter, "_adb", None) or self.context.adb_client` để các bước verifier sau reboot không crash `AttributeError`.
- **Phân Loại Đúng Transient ADB Timeout vs Keyguard Secure:** Lỗi kết nối ADB (`dumpsys power` timed out) là transient I/O delay, không phải màn hình khóa PIN/mật khẩu. Bắt buộc kiểm tra `"timed out" in str(startup.stop_reason).lower()` để phân loại sang `DEVICE_STARTUP_FAILED` (cho phép recovery ladder tự cứu) thay vì gán nhầm thành lỗi vĩnh viễn `DEVICE_STARTUP_MANUAL`.

## 3. Quarantine Unrelated Worker Scratch Edits Khi Chốt Phiên
- **Hiện tượng Worker Sửa Nháp Dở Dang:** Khi Coordinator dispatch worker subagent điều tra B2/B3, worker có thể phỏng đoán nhầm hướng và để lại uncommitted scratch edits trong working tree (ví dụ: tự ý thêm handler popup vào `benign_popup_registry.py` làm fail 10 test trong `test_benign_popup.py`) trước khi nhận ra root cause thực sự nằm ở module khác hoặc đã được giải quyết ở commit trước.
- **Quy Tắc Đối Soát Deliverable:** Khi chuyển sang Phase Closeout (Chốt phiên 6 Gate), Coordinator BẮT BUỘC kiểm tra `git status` và `git diff`, đối chiếu chặt chẽ với mục tiêu ban đầu của Farm Alert.
- **Kỹ Thuật Cô Lập An Toàn:** CẤM TUYỆT ĐỐI `git add` mù quáng các file sửa nháp làm gãy test suite hoặc phình diff. BẮT BUỘC dùng `git stash push -m "quarantine_worker_scratch_edits"` để cô lập các thay đổi ngoài lề, khôi phục working tree sạch và chạy focused test suite xác minh đúng candidate cần release.

## 4. Focused Package Unavailable Auto-Recovery & Dumpsys Bloat Prevention (Case 126 & 127)
- **Hiện tượng:** Thiết bị (đặc biệt các dòng Samsung Android cũ) đang mở TikTok ở màn hình Đề xuất / Feed bình thường nhưng phiên lướt feed bị dừng đột ngột với Farm Alert: `focused package unavailable`.
- **Nguyên nhân cốt lõi:**
  1. Lệnh `dumpsys window` đầy đủ sinh ra output nhiều Megabytes (hàng chục nghìn dòng), gây nghẽn buffer và dính ADB timeout 5.0s khiến `get_focused_activity` trả về `None`.
  2. `safety_check_attempt` không truyền `raw_xml` hoặc chỉ đọc `attempt.get("detected_screen")` mà bỏ qua `attempt.get("detected")`, khiến cờ `is_tiktok_xml` luôn là `False`.
  3. `safety_check` lập tức ném lỗi `SAFETY_FAILED: focused package unavailable` khi `focus_pkg is None` dù UI XML đã dump thành công và hiển thị rõ các thành phần TikTok.
- **Giải pháp chuẩn (Case Fix):**
  1. Trong `flows/observe.py`: Đưa `["dumpsys", "window", "displays"]` lên đầu danh sách candidates (nhẹ hơn 10-20 lần so với full `dumpsys window`), bổ sung regex `Window{...}` và fallback grep nhanh: `dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|mFocusedWindow'`.
  2. Trong `core/safety.py`: Mở rộng `is_tiktok_xml` với `KNOWN_TIKTOK_PACKAGES`, resource IDs và feed tabs ("Đề xuất", "Bạn bè", "Following", "For You"); khi `focus_pkg is None` nhưng có UI XML chứng thực thuộc TikTok (`has_xml_evidence and is_tiktok_xml`), tự động khôi phục `focus_pkg = expected`.

## 5. Gate 0.5 Case Catalog Verification Khi Lỗi Đã Được Ghi Nhận
- Khi xử lý Farm Alert mà phân tích kỹ thuật và hiện trường cho thấy nguyên nhân gốc rễ đã được xử lý và ghi nhận đầy đủ ở một Case trước đó (ví dụ Case 127):
  1. Coordinator KHÔNG tạo case trùng lặp hay commit rỗng vào `docs/farm-automation-cases.md`.
  2. Xác minh đối chiếu mã nguồn và sự hiện diện của Case trong catalog.
  3. BẮT BUỘC chạy Live Canary (Gate 0) trên chính thiết bị của alert hiện tại để kiểm chứng codebase tự phục hồi thành công trên máy thật.
  4. Nêu rõ số Case tương ứng (ví dụ: Case 127) trong báo cáo chốt phiên 6 Gate.

## 6. Transient ADB Input Swipe Failure Handling via Bounded Retry (Case 135)
- **Hiện tượng:** Máy farm dừng phiên với Farm Alert `feed swipe command failed` trên thiết bị đang mở màn hình TikTok Đề xuất bình thường.
- **Nguyên nhân cốt lõi:**
  1. Hàm `_perform_feed_swipe` trong `python_runner/flows/feed_swipe_smoke.py` gọi lệnh `input swipe` qua `ctx.adb.shell(cmd, timeout=swipe_timeout)`.
  2. Khi lệnh swipe trả về `result.ok == False` (non-zero exit code hoặc transient buffer glitch từ daemon ADB trên Android) hoặc ném ngoại lệ transient, hàm thiếu vòng lặp retry và trả về `False` ngay lập tức.
  3. Caller tại `run_feed_session_smoke` lập tức gán `status: failed`, `reason: "feed swipe command failed"` và dừng phiên nuôi acc mà không cho script cơ hội tự thử lại.
- **Giải pháp chuẩn (Case Fix):**
  1. Bổ sung vòng lặp retry có giới hạn (tối đa 3 lần thử) trong `_perform_feed_swipe` bao quát cả `not result.ok`, `ADBError` và ngoại lệ transient.
  2. Nghỉ 1.0s giữa các lần thử và log `result="retry"`, `error=f"attempt {attempt}/{max_attempts} failed: {last_error}"`.
  3. Chỉ khi toàn bộ 3 lần thử đều thất bại mới log `ExitStatus.FAIL.value` và trả về `False`.

## 7. Kế Thừa Active Device Lock Cho Subprocess Reconcile Tránh Lỗi "Cha Khóa Cửa Con" (Case 138 / LOCK-05 Pattern)
- **Hiện tượng:** Khi tiến trình cha `multi-machine-feed-session` (hoặc feed worker) phát hiện tài khoản trong row workbook không có trong switcher, nó khởi chạy subprocess `reconcile_tiktok_accounts.py` để tự động đăng nhập/nạp nick. Subprocess con gọi `acquire_device_lock` với `--full-scope-takeover`, nhưng `automation_core.device_lock` từ chối chiếm quyền từ tiến trình cha đang chạy (`owner_active: True`, PID alive). Con bị văng với `SKIPPED_LOCKED` (exit code 4), khiến cha fail `manual-needed` và giữ lock `blocked` (1h) hàng loạt máy.
- **Giải pháp chuẩn:**
  1. Trong `tiktok-log-in` (`account_reconcile.py`): Tạo proxy lease `InheritedDeviceLock(DeviceLockLease)` kế thừa đầy đủ lifecycle (`is_still_held=True`, `release_with_audit`, `finish`, `set_status`). Bổ sung CLI flag `--allow-parent-lock`. Khi lock exception do parent project (`PARENT_LOCK_PROJECTS = ("tiktok-luot nuoi acc", "tiktok-feed", "multi-machine-feed-session")`) sở hữu và có cờ `--allow-parent-lock`, cấp `InheritedDeviceLock` thay vì ném exception.
  2. Trong consumer repo (`tiktok-luot nuoi acc` / `feed_swipe_smoke.py`): Truyền `--allow-parent-lock` khi gọi `reconcile_tiktok_accounts.py`.
  3. Thứ tự chốt phiên đa repo: BẮT BUỘC test, commit, rebase, push và verify `tiktok-log-in` trước hoặc đồng bộ với consumer repo (`tiktok-luot nuoi acc`), đối soát `git ls-remote` cả 2 repo.

## 8. Quy Chuẩn Báo Cáo B5 Farm Alert vs Chốt Phiên 6 Gate (Tránh Hiểu Nhầm)
- Ở bước B5 của Farm Alert, TUYỆT ĐỐI KHÔNG dùng chữ `Closeout` đơn độc khiến user nhầm tưởng agent đã tự ý chạy quy trình Chốt phiên (Git commit/push).
- BẮT BUỘC ghi rõ: `B5 (Báo cáo phục hồi hiện trường / Incident Recovery Report)` và nêu rõ: thiết bị đã phục hồi, mã nguồn đã sửa ở local/canary pass, và chờ lệnh `chốt phiên` từ user trước khi thực hiện 6 Gate.

## 9. Phòng Chống Sa Đà Over-Engineering & Bẫy Subagent Ngọng Khi Chạy Canary / Fix Alert (Case 141)
- **Bản chất kỹ thuật gây sa đà (45 phút ngâm phiên):**
  1. **DoD Misalignment (Goal Success-Biased):** Khi giao task runner "chạy X, lấy secret Y, xác nhận thành công", LLM coi `failed` là *chưa xong việc*. Do tính kiên trì (persistence) được huấn luyện, nó tự động chuyển vai thành Debugger: đọc source code, quét file, thử tool lạ và loop hàng chục tool calls.
  2. **DoD Report-Biased Chuẩn:** Với mọi task chạy lệnh/canary, **DoD phải là "Ghi nhận kết cục thực tế và THOÁT NGAY"**. Bất kể kết quả là `failed` hay `success` đều là **HOÀN THÀNH 100% NHIỆM VỤ**. Lỗi của lệnh chạy là *dữ liệu báo cáo về cho Coordinator*, không phải bài toán Runner được phép tự ý nhảy vào giải.
  3. **Bẫy Hard Block Guard & Counter Adversarial:** Việc dùng hook đếm `READ_BUDGET`, `MAX_WORKER_CALLS` hay cấm tool tùy tiện (`computer_use`) sẽ nhồi lỗi `⛔ [BLOCKED]` vào context, gây Context Poisoning và làm subagent bị "ngọng" (choked/lobotomized). Subagent cần được trao **toàn quyền công cụ** (full toolset) và điều hướng bằng **tiêu chí dừng khách quan (Stopping Criteria)** trong prompt.
  4. **Samsung Launcher Base32 False-Positive Trap:** Khi trích xuất mã OTP/Secret Key 16 ký tự Base32 (`[A-Z2-7]{16,64}`), BẮT BUỘC lọc theo package ứng dụng (`com.ss.android.ugc.trill`). Tránh bẫy quét trúng widget hệ thống trên màn hình chính Samsung (ví dụ widget `Galaxy Essentials` -> `GALAXYESSENTIALS` dài đúng 16 ký tự A-Z hợp lệ Base32), làm runner nhận nhầm secret rác và văng lỗi tìm nút tiếp tục ngay trên màn hình launcher.

## 10. Động Hóa Tham Số Row & Khắc Phục Hardcode Alert Báo Sai Nick/Row (Case 142)
- **Hiện tượng & Bẫy Cảnh Báo "Ngu":**
  1. Cảnh báo Farm Alert dừng phiên luôn báo nick mặc định và lệnh recovery B4 bị hardcode cố định `-Row 1` (`run-feed-session.ps1 -Machines <M> -Row 1...`).
  2. Khi máy gặp sự cố ở Ca 2 (Row 3, 12:30 ngày lẻ) hoặc Ca 3 (Row 5, 19:00 ngày lẻ), alert gây hiểu lầm tai hại và khiến worker khi chạy canary tự động bốc nhầm Slot 1 thay vì slot thực tế đang gặp lỗi.
- **Nguyên nhân cốt lõi:**
  1. Trong `automation-core/alerts.py`, hàm `_resolve_script_meta` và lambda `default_canary` chỉ nhận `m` và gắn chết chuỗi `-Row 1`.
  2. `send_farm_machine_alert` không nhận tham số `row`, khiến banner alert không in `Row` và call sites trong `multi_machine_feed_session.py` không truyền `account_row_index`.
- **Giải pháp chuẩn (Case 142 Fix):**
  1. Nâng cấp `send_farm_machine_alert` và `_resolve_script_meta` trong `automation-core/alerts.py` nhận tham số `row: int | None = None`. Lambda `default_canary` nhận `(m, row=1)` và sinh `-Row {row}`.
  2. Hiển thị rõ `• Máy: {machine} | Row: {row} | ...` trong banner Telegram.
  3. Tại các call sites kích hoạt alert trong `multi_machine_feed_session.py`, truyền `row=getattr(child, "account_row_index", None)`.
- **Quy Tắc Vận Hành & Phản Xạ Khi User Yêu Cầu Sửa Alert (User Correction 08/09/2026):**
  1. Khi user chỉ đạo: *"Sửa alert lại báo đúng nick. Không yêu cầu chạy canary."* -> BẮT BUỘC tôn trọng mệnh lệnh: CHỈ sửa code logic sinh alert và compile test cú pháp, **TUYỆT ĐỐI CẤM tự ý kích hoạt Canary Test trên máy thật** làm lãng phí thời gian và chạm thiết bị ngoài ý muốn.
  2. **Bẫy Windows Backslash `\r` Trong String Script:** Khi tạo chuỗi lệnh chứa đường dẫn Windows (ví dụ `scripts\run-feed-session.ps1`), ký tự `\r` sẽ bị hiểu nhầm thành carriage return làm ngắt dòng (`scripts\` + `un-feed-session.ps1`) gây lỗi `SyntaxError: unterminated string literal`. Bắt buộc sử dụng dấu gạch xuôi `scripts/run-feed-session.ps1` hoặc raw string `fr'...'`.




