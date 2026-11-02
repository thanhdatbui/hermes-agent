---
name: canary-watchdog-gate-protocol
description: Cơ chế watchdog canh nhả lock khi chạy Gate 6 Canary, chống đứng im chờ máy và chống block toàn farm.
---

# Canary Watchdog Gate Protocol & Anti-Stall Enforcement

## 1. Bối cảnh & Nguyên tắc tối cao
- Khi pipeline sửa code kích hoạt **Gate 6 Canary**, nếu thiết bị farm đang bận hoặc kẹt reservation lock của ca nuôi feed:
  - **CẤM TUYỆT ĐỐI** Agent đứng im trong chat, phát biểu "đang chờ máy nhả lock" rồi bỏ lơ không hành động.
  - **BẮT BUỘC** cơ giới hóa tự động: hoặc dùng vòng lặp watchdog retry (`unified_patch_pipeline.py`), hoặc cài cron canh nhả lock, hoặc chọn máy rảnh giữa các ca qua thuật toán thu hẹp shift buffer.

## 2. Quy tắc cơ giới hóa cốt lõi

### A. Watchdog Loop trong Pipeline (`unified_patch_pipeline.py`)
- Khi `canary_runner` trả về lỗi bận lock (`device lock active` hoặc `Không có máy rảnh hợp lệ`):
  - Tối thiểu 3 nhịp thử lại (`max_canary_attempts = 3`), mỗi nhịp ngủ 20–30s kiểm tra nhả lock trước khi quyết định rollback.
  - Cấm rollback mù quáng ngay nhịp đầu tiên khi máy chỉ vừa chuyển giao giữa 2 tiến trình.

### B. Quy tắc tính Shift Buffer máy Farm (`canary_runner.py`)
- **Sai lầm cần tránh:** Tính `now + SHIFT_BUFFER (60m)` quét toàn bộ manifest 640 slot sẽ chặn sạch 80 máy cả ngày (`candidates = []`).
- **Quy tắc chuẩn xác:**
  1. Chỉ block máy đang chạy đúng slot hiện tại (`start <= now <= end`).
  2. Block máy sắp chạy trong vòng $\le 5$ phút tới (`now < start <= now + 5m`).
  3. Mọi máy nằm ở khoảng nghỉ giữa các ca đều được coi là rảnh để `--auto-device` tự động chọn làm Canary.

### C. Cơ chế Dry-Run Canary cho Logic Code
- Với các task thuần thuật toán (như `follow_state.py`), khi chạy với cờ `--dry-run`:
  - `canary_runner.py` chỉ kiểm tra runner hoàn tất với `exit code == 0` và sinh ra `FOLLOW_PLAN` hợp lệ.
  - Cấm đòi hỏi parse kết quả live `FOLLOW_RESULT status='OK'` khi đang chạy chế độ giả lập dry-run.

## 3. Kiến Trúc Dữ Liệu: SQLite vs. Excel Ledger & Phân Biệt Kẹt Thật vs. Lệch Ca Nuôi
- **`tiktok_tracker.db` (SQLite):** Đóng vai trò là Analytics Engine lưu lịch sử snapshots engagement, tăng trưởng tim/view/follow, phục vụ báo cáo và phân tích thuật toán.
- **`Tik1.xlsx` .. `Tik8.xlsx` (Excel):** Đóng vai trò là Operational Ledger định tuyến cứng máy, serial, folder raw, folder render và duy trì con trỏ upload sequence (`video_da_dang`). Worker upload trực tiếp phụ thuộc vào ledger này.
- **Phân biệt kẹt thật vs. lệch ca nuôi (Shift Cycle):** Farm vận hành chu kỳ 4 ngày x 3 ca (mỗi máy 8 row, mỗi ngày chỉ nuôi 2-3 row). Tài khoản chưa tới ca nuôi số video sẽ đứng im, không được nhầm lẫn là cron upload bị hỏng. Kiểm tra `run_manifest.json` và `summary.txt` tại runtime trước khi kết luận.
- **Flop Scanner Traps:** Chỉ kiểm tra flat run trên 3 snapshot gần nhất (`snapshots_history[-3:]`), cấm quét toàn bộ lịch sử 2 tháng làm hàng trăm nick bị gán nhãn flop sai.
