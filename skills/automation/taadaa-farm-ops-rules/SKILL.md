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
- Bẫy Cắt Số Đuôi Account Switcher & Khởi Chạy SplashActivity Đích Danh: [`references/account-switcher-trailing-digits-and-explicit-launch-focus.md`](references/account-switcher-trailing-digits-and-explicit-launch-focus.md)
