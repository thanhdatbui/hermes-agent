# Chẩn đoán & Xử lý lỗi Cron Dynamic Healing Selector (TikTok Runner)

## Hiện tượng & Dấu hiệu nhận biết
Trong chu kỳ nuôi 4 ngày (Parity 96h: N1 lẻ, N2 chẵn, N3 R7/8 + tối dưỡng, N4 dưỡng sinh động toàn farm):
- Vào Ngày 4 (hoặc slot dưỡng sinh), runner luôn chạy cố định các Row:
  - Ca 1 (06h, 08h): Row 3
  - Ca 2 (12h, 14h): Row 4
  - Ca 3 (18h, 20h): Row 5
- Không thấy log event `healing_row_selected` trong stdout hoặc audit log `D:/Taadaa/runtime/audit_logs/healing_decision_audit.jsonl` không có bản ghi mới của ngày.
- Xuất hiện log `healing_row_fallback` trong stderr với lỗi `ImportError: healing_selector.py not found`.

## Nguyên nhân gốc rễ (Root Cause)
1. **Lệch đường dẫn thực thi của Cron:**
   - Khi Cron chạy script `no_agent`, file thực thi `tiktok_runner.py` nằm tại thư mục deploy độc lập trên ổ `C:` ngoài cây git repo.
   - Hàm `_load_determine_healing_row()` chỉ tìm kiếm `healing_selector.py` qua:
     1. Biến môi trường `os.environ.get("HERMES_CRON_TOOLS_DIR")` (mặc định chưa được set trong env của cron process).
     2. Cây thư mục cha `Path(__file__).resolve().parents` (nằm trên ổ `C:`, không thể chạm tới `D:/Taadaa/tools/healing_selector.py`).
2. **Cơ chế Fallback tĩnh nuốt lỗi (Silent Fallback Masking):**
   - Khối `except Exception as exc` trong `_determine_row()` bắt `ImportError` và gán cứng:
     - Slot 06h / 08h -> Row 3
     - Slot 12h / 14h -> Row 4
     - Slot 18h / 20h -> Row 5
   - Khiến cron vẫn chạy thành công và báo cáo bình thường, nhưng hoàn toàn bỏ qua việc tính điểm ưu tiên các nick yếu.

## Giải pháp chuẩn hóa (Canonical Pattern)
1. **Dual Discovery trong `_load_determine_healing_row()`:**
   - Ưu tiên đọc biến `HERMES_CRON_TOOLS_DIR` từ `os.environ`.
   - Nếu trống, đọc tiếp từ `repo_env_overrides().get("HERMES_CRON_TOOLS_DIR")` (`runtime/hermes-cron/env.json`).
   - Nếu vẫn trống, quét qua danh sách candidate roots dự phòng:
     `"D:/Taadaa/tiktok-luot nuoi acc"`, `"D:/Taadaa"`, `"D:/Taadaa/tiktok-follow"`, `"D:/Taadaa/automation-core"`.
2. **Khai báo trong `env.json`:**
   Tại `D:/Taadaa/tiktok-luot nuoi acc/runtime/hermes-cron/env.json`:
   ```json
   "HERMES_CRON_TOOLS_DIR": "D:/Taadaa/tools"
   ```
3. **Đồng bộ ngay sang Runtime:**
   Sau khi sửa code trong repo `scripts/hermes_cron/tiktok_runner.py`, bắt buộc kích hoạt `cron-sync-watchdog` để đồng bộ sang deploy runtime:
   ```python
   cronjob(action="run", job_id="2b5b608429c7")  # cron-sync-watchdog
   ```

## Kiểm chứng (Verification)
1. Chạy focused test:
   ```bash
   python -m pytest "D:/Taadaa/tiktok-luot nuoi acc/tests/test_tiktok_runner_healing.py" -q
   ```
2. Thử nghiệm hàm trực tiếp trong Python (không set biến môi trường):
   ```python
   from datetime import datetime
   from zoneinfo import ZoneInfo
   HCMC = ZoneInfo("Asia/Ho_Chi_Minh")
   import sys
   sys.path.insert(0, "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron")
   import tiktok_runner
   dt = datetime(2026, 10, 14, 6, 0, tzinfo=HCMC)
   row, sess, win, is_rest = tiktok_runner._determine_row(dt)
   assert is_rest is True
   print(f"Healing Row Selected: {row}")
   ```
