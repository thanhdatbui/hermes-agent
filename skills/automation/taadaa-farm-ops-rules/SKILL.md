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
- **Task ngầm / Cronjob:** Hook `guard_cronjob_safety.py` tự động ép cứng `CREATE_NO_WINDOW (0x08000000)` và `Hidden`, cấm pop console cướp focus.

## 2. Chu Trình Điều Phối Farm (Coordinator vs Worker)
- **T0 (Hiện trường):** Đọc log, inspect ADB O(1), restart process, kiểm tra proxy. Tự do thực thi.
- **T1 (Vá hiện trường <= 15 dòng):** Sửa trực tiếp O(1) 1 file, verify < 30s, chạy Canary trên 1 máy thật đại diện (chụp ảnh `MEDIA:` + OCR sạch).
- **T2 (Thi công lớn > 15 dòng):** Dispatch qua Single Dispatch Gateway `python D:/Taadaa/tools/dispatch_worker.py "<contract O(1)>" --workdir <repo>`.
- **Chốt phiên:** `python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base origin/main --json-output` (Hook `pre-push` tự động chặn nếu điểm < 80).

## 3. Quy Chuẩn Báo Cáo Telegram Farm Alert
- Báo cáo sự cố kèm ảnh nghiệm thu nằm trong **cùng 1 tin nhắn duy nhất**:
  - Dòng 1: `MEDIA:<đường_dẫn_tuyệt_đối>` (không bọc markdown).
  - Dòng 2: `### [MÁY XX] - <Tên màn hình / Nhóm lỗi>`
  - Dòng 3+: Mô tả OCR readback và đề xuất xử lý. Caption tổng <= 1024 ký tự.
- Bắt buộc bọc `html.escape()` cho các biến động trong alert HTML.

## 4. Danh Mục Tài Liệu Tra Cứu Chi Tiết (References)
- Toàn bộ hồ sơ sự cố lịch sử & quy tắc cũ: [`references/historical-farm-incidents-and-rules-archive.md`](references/historical-farm-incidents-and-rules-archive.md)
- Downloader & Cleanup: [`references/dual-scope-downloader.md`](references/dual-scope-downloader.md) & [`references/account-cleanup-and-banned-handling.md`](references/account-cleanup-and-banned-handling.md)
- Single Source of Truth Tools: [`references/single-source-of-truth-tools-ops.md`](references/single-source-of-truth-tools-ops.md)
- Device Lock & Reaper: [`references/device-lock-cadence-and-reap-timeout.md`](references/device-lock-cadence-and-reap-timeout.md)
- Claude CLI Bounded Review Loop: [`references/claude-cli-bounded-review-loop.md`](references/claude-cli-bounded-review-loop.md)
