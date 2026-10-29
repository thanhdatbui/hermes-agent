---
name: taadaa-farm-ops-rules
description: "Taadaa farm safety, close-session, and multi-machine operations."
---

# Taadaa Farm Operations Rules & Invariants

## 1. Nguyên Tắc Cốt Lõi (Invariants)
- **Tra cứu O(1):** Khi nhận Farm Alert `[MÁY N]`, chạy duy nhất `python D:/Taadaa/tools/inspect_machine.py <N>`. (Hook `guard_broad_grep.py` chặn đệ quy).
- **Chụp ảnh trước Teardown (Capture-Before-Cleanup):**
  1. Chụp ảnh hiện trường (`MEDIA:<path>`).
  2. WinRT OCR / Vision kiểm chứng chữ trên màn hình.
  3. Chỉ thực hiện `am force-stop` và `input keyevent KEYCODE_HOME` sau khi đã có ảnh. CẤM chụp ảnh màn hình HOME làm nghiệm thu.
- **Cấm tap tay qua ADB:** Không chạy `input tap`, `input keyevent`, `input swipe` để bấm qua màn hình lỗi. Sửa code trong script để cả dàn máy tự động vượt qua.
- **Task ngầm / Cronjob:** Hook `guard_cronjob_safety.py` tự động ép cứng `CREATE_NO_WINDOW (0x08000000)` và `Hidden`, cấm pop console cướp focus. Mọi lệnh subprocess trên Windows bắt buộc OR-merge `creationflags |= 0x08000000`.
- **Cấm quét đĩa diện rộng (Anti-Scan Guard):** CẤM chạy `search_files` trên root `D:/Taadaa` hoặc `D:/Taadaa/tools`, cấm script có `os.walk` / `glob recursive`. Bắt buộc chỉ định đích danh file hoặc thư mục con hẹp.
- **Khóa thiết bị JIT (Device Lock Mandatory):** Mọi can thiệp ADB vào máy thật bắt buộc giữ JIT device lock (`inspect_machine.py <N>` hoặc `with_device_lock.py --machine <N> -- ...`), cấm can thiệp trần.
- **Kỷ Luật Thực Thi Sau Auto-Resume / Compaction (Anti-Stalling Invariant):** Khi hệ thống vừa khôi phục phiên (context compaction / reconnect / restart) mà lệnh của User đang dở dang (ví dụ: 'Đổi ava kênh này', 'Chuẩn hoá kênh này', 'Fix máy N'), CẤM TUYỆT ĐỐI dừng lại hỏi User 'Bạn muốn tiếp tục không hay làm việc khác?'. Phải tự động đọc context gần nhất, xác định target O(1), tiếp tục thực thi dứt điểm toàn bộ pipeline và nghiệm thu bằng chứng thật (ảnh MEDIA, OCR, diff). Hỏi xin phép hoặc đùn đẩy trách nhiệm khi lệnh gốc đã rõ ràng là vi phạm nghiêm trọng kỷ luật O(1).
- **Phân định Auto-Wiring vs Active Pivot (Anti-Paralysis):** Task điều tra read-only tự động gắn `BUDGET: <= 8 calls`. Task sửa code CẤM dùng `delegate_task` (bị `subagent_edit_blocked`), bắt buộc dùng Active Pivot: copy lệnh mẫu `python D:/Taadaa/tools/dispatch_worker.py ...` chạy ngay ở turn kế. Worker cấm dừng hỏi input (`NEEDS_INPUT`).
- **Guidance Chống Chặn Terminal & ADB (Anti-Scan & Bulkhead Invariants):**
  1. `GUARD_SEARCH_FILES_ROOT`: CẤM gọi `search_files` trên root thư mục (`D:/Taadaa`, thư mục gốc repo); BẮT BUỘC chỉ định `path` đến thư mục con hẹp và `file_glob` cụ thể.
  2. `GUARD_DANGEROUS_ROOT` & `GUARD_FIND_SCAN`: CẤM `os.walk`, `rglob`, `glob(recursive=True)` hoặc lệnh shell `find`. Tra cứu máy dùng `python D:/Taadaa/tools/inspect_machine.py <N>`.
  3. `GUARD_DEVICE_FOREGROUND_TIMEOUT`: Mọi lệnh terminal thiết bị/ADB foreground bắt buộc đặt `timeout <= 60s` (trần an toàn). Tác vụ chạy dài bắt buộc dùng background (`background=True, notify_on_complete=True`).
  4. `GUARD_MANUAL_ADB_TAP`: CẤM TUYỆT ĐỐI chạy `adb shell input tap/swipe/keyevent` bấm tay qua popup/màn hình lỗi. Sửa trực tiếp logic tự động trong script runner.
  5. `GUARD_AMBIGUOUS_ADB_COMMAND`: Tránh dùng từ khóa `adb` trần trong commit message (`git commit -m`) hoặc lệnh `grep` không bọc kỹ; phân tách rõ lệnh git/grep với lệnh adb thật.
- **Cấm Báo Cáo Hoàn Thành Mù Avatar (Avatar Visual Diff Invariant):** CẤM TUYỆT ĐỐI dựa vào exit code 0 của runner hoặc cờ `AVATAR_SMOKE_SUCCESS` / `FORCED_REPLACED_VERIFIED` để báo xong. BẮT BUỘC chụp ảnh Profile thật, cắt vòng tròn avatar và đối soát hình ảnh (perceptual diff / vision OCR) để đảm bảo không bị dính bẫy tap nhầm screenshot cũ trong Gallery Picker. Tọa độ chuẩn bottom sheet Sửa hồ sơ: 'Tải ảnh lên' `(224, 1637)`, 'Lưu' `(792, 1794)`.
- **Chống Ảo Giác Thuật Ngữ & Lệch Schema Đa Cụm (Terminology & Cross-Cluster Schema Invariant):**
  1. *Thuật ngữ trung thực*: Hotmail trên farm là mail MUA (Bought Mail), hoàn toàn KHÔNG CÓ script reg Hotmail; quy trình bắt đầu bằng `HOTMAIL_LOGIN` (login mail mua vào GPM), cấm dùng tiếng lóng "reg Hotmail" gây hiểu lầm và báo cáo sai lệch.
  2. *Nhận diện màn hình Onboarding*: Màn hình "Bạn bao nhiêu tuổi?" (`/about-you`) là luồng TẠO MỚI tài khoản của OpenAI, KHÔNG PHẢI phiên hết hạn. Thấy màn hình này là bằng chứng tài khoản chưa hề đăng ký xong trước đó; cấm tin vào timestamp supervisor state để phán đã reg.
  3. *Lệch schema Kibe vs Admin*: Kibe có cột 11 `PASS CHATGPT` (12 cột), Admin là schema TikTok legacy (10 cột, dừng ở `device ID`). Mọi script đọc workbook liên cụm BẮT BUỘC fallback sang mật khẩu mail (`cred['pwd']`) chuẩn hóa `normalize_password`, CẤM hardcode đường dẫn Kibe hoặc bỏ qua candidate khi thiếu cột.
  4. *Khế ước Exit Code*: Runner con BẮT BUỘC return 1 khi skip/fail, chỉ return 0 khi thành công thật; Supervisor cấm tin mù quáng vào exit code 0 để đóng dấu `chatgpt_registered_at` ảo.
- **Độc Lập Tuyệt Đối 3 Quy Trình (Feed — Follow — Upload):** Ba quy trình chính của nick farm chạy tuần tự nhưng hoàn toàn độc lập. CẤM TUYỆT ĐỐI cơ chế ép buộc Feed thành công mới được Follow/Upload. Quy trình trước fail thì quy trình sau vẫn BẮT BUỘC khởi chạy bình thường.
- **Chống Phạt Cooldown Oan (Single-Release Cooldown Ban):** Nút follow revert về 'Follow' sau tap chứng minh server TikTok đã từ chối lượt follow đó. Tuy nhiên, CẤM đóng băng tài khoản 24h (`cooldown_until_date`) chỉ sau 1 lần nhả đơn lẻ; chỉ dừng phiên hiện tại và chỉ phạt cooldown khi bị nhả liên tiếp trên các phiên khác nhau (Streak >= 2).
- **Độc Lập Lệch Pha 3 Ca (Shift-Pool Decoupled Phase Invariant):** Chu kỳ 3 ngày cày liên tục (bỏ hẳn ngày 4 dưỡng sinh). Ca 1 `{1,2,7}`, Ca 2 `{3,4,8}`, Ca 3 `{5,6}` (+ Dynamic slot `-1`). Việc 3 ca bị lệch pha (Ca 3 cạn pool trước hoặc Ca 1/2 bù lượt) là AN TOÀN VÀ HỢP LỆ vì pool tài khoản rời nhau 100% và gate cooldown 48h (`_is_account_follow_cooldown`) bảo vệ độc lập; cấm ép đồng pha cứng nhắc làm rối loạn nhịp xoay tua.
- **Khắc Phục Socket Concurrency Dashboard (Port 1905):** CẤM để nhiều tiến trình `tiktok_dashboard.py` cùng bind port 1905; dọn sạch startup duplicate và kill triệt để cả cây `pythonw.exe` / `python.exe` / watchdog ps1 khi socket bị kẹt.
- **Xử Lý Kênh Flop & Chống Bỏ Tài Khoản (Anti-Account-Abandonment Invariant):** Kênh flop view/tim kẹt đáy TUYỆT ĐỐI CẤM bỏ rơi, cấm xóa nick khỏi lịch upload, cấm giáng cấp nick làm seeding. Nick flop vẫn tiếp tục đăng video đều đặn theo farm ("kiểu gì cũng lên"); giải pháp duy nhất là xoay nguồn cào (Source Rotation) trong pool (`flop_channel_scanner.py`) và render tiếp nối từ `start_seq = video_da_dang + 1`.
- **Thiết Kế Sổ Bệnh Án Lâm Sàng (Clinical-First UX Invariant):** Tab `📜 Sổ Bệnh Án` (`follow_records`) là hồ sơ lâm sàng tra cứu từng nick (Bệnh trạng, Quota, Lịch sử UID); CẤM nhồi nhét bảng thống kê chu kỳ 4 ngày và thẻ cohort vĩ mô chiếm trọn nửa trên màn hình gây rối mắt và che khuất tra cứu. Thống kê vĩ mô chuyển sang tab Sức Khỏe hoặc gập gọn mặc định.
- **Kỷ Luật Chốt Phiên Closeout v2 O(1) Chống Bẫy Legacy Gate:** Chốt phiên BẮT BUỘC dùng `python D:/Taadaa/tools/closeout_v2.py --repo <repo> [--target-file <file>] --json-output` (kiểm tra deterministic: cú pháp + focused pytest). TUYỆT ĐỐI CẤM gọi tool cũ `closeout_gate.py` để tránh bẫy LLM Reviewer và lỗi rule GuardGate over-engineered (`case_invariant_require_step_by_step_structure`).

## 2. Chu Trình Điều Phối Farm (Coordinator vs Worker)
- **T0 (Hiện trường):** Đọc log, inspect ADB O(1), restart process, kiểm tra proxy. Tự do thực thi.
- **T1 (Vá hiện trường <= 15 dòng):** Sửa trực tiếp O(1) 1 file, verify < 30s, chạy Canary trên 1 máy thật đại diện (chụp ảnh `MEDIA:` + OCR sạch).
- **T2 (Thi công lớn > 15 dòng):** Dispatch qua Single Dispatch Gateway `python D:/Taadaa/tools/dispatch_worker.py "<contract O(1)>" --workdir <repo>`.
- **Chốt phiên (Closeout v2 O(1)):**
  - **Phiên Vận Hành (farm, nick, device, excel - không có code delta):** `python D:/Taadaa/tools/closeout_v2.py --repo <repo> --operational --json-output` (PASS ngay trong < 0.1s; TUYỆT ĐỐI CẤM gọi LLM Reviewer chấm điểm hay Sol Repair sửa code ma).
  - **Phiên Sửa Code:** `python D:/Taadaa/tools/closeout_v2.py --repo <repo> --json-output` (Kiểm tra cơ học deterministic: `py_compile` cú pháp + chạy `pytest` focused; test PASS -> APPROVED; không dùng LLM chấm điểm cảm tính 85/100).

## 3. Quy Chuẩn Báo Cáo Telegram Farm Alert
- Báo cáo sự cố kèm ảnh nghiệm thu nằm trong **cùng 1 tin nhắn duy nhất**:
  - Dòng 1: `MEDIA:<đường_dẫn_tuyệt_đối>` (không bọc markdown).
  - Dòng 2: `### [MÁY XX] - <Tên màn hình / Nhóm lỗi>`
  - Dòng 3+: Mô tả OCR readback và đề xuất xử lý. Caption tổng <= 1024 ký tự.
- Bắt buộc bọc `html.escape()` cho các biến động trong alert HTML.

## 4. Danh Mục Tài Liệu Tra Cứu Chi Tiết (References)
- Báo Cáo & Quy Trình Đại Phẫu Cắt Tỉa Hệ Thống Gate / Guard Over-Engineered (2026-10-27): [`references/complete-farm-gate-pruning-and-hash-chain-eradication-20261027.md`](references/complete-farm-gate-pruning-and-hash-chain-eradication-20261027.md)
- Toàn bộ hồ sơ sự cố lịch sử & quy tắc cũ: [`references/historical-farm-incidents-and-rules-archive.md`](references/historical-farm-incidents-and-rules-archive.md)
- Downloader & Cleanup: [`references/dual-scope-downloader.md`](references/dual-scope-downloader.md) & [`references/account-cleanup-and-banned-handling.md`](references/account-cleanup-and-banned-handling.md)
- Single Source of Truth Tools: [`references/single-source-of-truth-tools-ops.md`](references/single-source-of-truth-tools-ops.md)
- Device Lock & Reaper: [`references/device-lock-cadence-and-reap-timeout.md`](references/device-lock-cadence-and-reap-timeout.md)
- Claude CLI Bounded Review Loop: [`references/claude-cli-bounded-review-loop.md`](references/claude-cli-bounded-review-loop.md)
- ChatGPT Web Pool & OmniRoute Cap: [`references/chatgpt-web-pool-feeding-candidate-filtering-and-omniroute-cap.md`](references/chatgpt-web-pool-feeding-candidate-filtering-and-omniroute-cap.md)
- ChatGPT Fake Reg Exit Code & Onboarding Pitfalls: [`references/chatgpt-fake-registration-supervisor-exit-code-and-onboarding-pitfalls.md`](references/chatgpt-fake-registration-supervisor-exit-code-and-onboarding-pitfalls.md)
- Auto-Wiring & Active Pivot: [`references/auto-wiring-active-pivot-and-gate-compliance-20261026.md`](references/auto-wiring-active-pivot-and-gate-compliance-20261026.md)
- Auto-Wiring vs Guidance & ADB Detector Invariants: [`references/auto-wiring-vs-guidance-and-detector-invariants.md`](references/auto-wiring-vs-guidance-and-detector-invariants.md)
- Dynamic Pool Row 0 vs Cron Rest-Day Parity: [`references/dynamic-pool-row0-vs-cron-runner-rest-day-flag-parity.md`](references/dynamic-pool-row0-vs-cron-runner-rest-day-flag-parity.md)
- Windows Large Directory Cold Cache I/O Pitfalls: [`references/windows-large-dir-cold-cache-io-pitfalls.md`](references/windows-large-dir-cold-cache-io-pitfalls.md)
- Gallery Picker Stale Tile & Avatar Bottomsheet: [`references/gallery-picker-stale-tile-and-bottomsheet-coords.md`](references/gallery-picker-stale-tile-and-bottomsheet-coords.md)
- Kỷ Luật Chốt Phiên Closeout v2 O(1) & Khai Tử LLM Reviewer: [`references/closeout-v2-o1-fast-gate-protocol.md`](references/closeout-v2-o1-fast-gate-protocol.md)
- Khế Ước Dò Quota Trần Động Follow (Biên Độ 2 & Hạ Trần Gãy -2): [`references/follow-dynamic-quota-tight-boundary-and-post-failure-reduction-20261028.md`](references/follow-dynamic-quota-tight-boundary-and-post-failure-reduction-20261028.md)
- Bẫy Cắt Số Đuôi Account Switcher & Khởi Chạy SplashActivity Đích Danh: [`references/account-switcher-trailing-digits-and-explicit-launch-focus.md`](references/account-switcher-trailing-digits-and-explicit-launch-focus.md)
- Audit & Purge ChatGPT GPM Đăng Nhập & Đồng Bộ Token: [`references/chatgpt-gpm-login-audit-and-purge-discipline.md`](references/chatgpt-gpm-login-audit-and-purge-discipline.md)
- Độc Lập 3 Quy Trình (Feed-Follow-Upload) & Chống Phạt Cooldown Oan: [`references/decoupled-pipeline-and-follow-cooldown-guard.md`](references/decoupled-pipeline-and-follow-cooldown-guard.md)
- Khế Ước Drop-Day Sổ Bệnh Án & Zero-Follow Failure: [`references/follow-detail-matrix-drop-day-zero-follow-invariant.md`](references/follow-detail-matrix-drop-day-zero-follow-invariant.md)
- Khế Ước Ghi Nhận Drop History & Đối Soát Khoảng Cách Ca Chạy Follow: [`references/follow-detail-streak-drop-history-and-gap-reconciliation.md`](references/follow-detail-streak-drop-history-and-gap-reconciliation.md)
- Chu Kỳ 3 Ngày Shift-Pool, Lệch Pha An Toàn & Socket Concurrency Dashboard: [`references/tiktok-farm-3day-shift-pool-phase-decoupling-and-dashboard-concurrency.md`](references/tiktok-farm-3day-shift-pool-phase-decoupling-and-dashboard-concurrency.md)
- Quét Kênh Flop & Xoay Nguồn Cào (Cấm Bỏ Acc, Render Nối Tiếp): [`references/flop-channel-detection-and-source-rotation-invariants.md`](references/flop-channel-detection-and-source-rotation-invariants.md)
- Quản Trị Quét Kênh Flop & Throttle Xoay Nguồn Cào Tự Động: [`references/flop-channel-detection-and-source-rotation-governance.md`](references/flop-channel-detection-and-source-rotation-governance.md)
- Xoay Nguồn Kênh Flop & Kỷ Luật UI Lâm Sàng Sổ Bệnh Án: [`references/flop-channel-source-rotation-and-dashboard-clinical-ux.md`](references/flop-channel-source-rotation-and-dashboard-clinical-ux.md)
