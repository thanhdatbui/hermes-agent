# Quy trình Rerun On-Demand các máy lỗi Reg TikTok theo lệnh User

## 1. Nguyên tắc cốt lõi
- **Hành động ngay lập tức:** Khi user ra lệnh "chạy lại các máy lỗi / lock lại chạy", agent BẮT BUỘC thực thi tool khởi chạy batch ngay trong lượt, tuyệt đối không dừng lại ở mức giải thích, chẩn đoán suông hoặc hỏi lại làm gián đoạn.
- **Không tự ý chạy khi chưa có lệnh:** Chỉ thực hiện rerun khi có chỉ đạo rõ ràng từ user ("chạy lại cho t", "rerun máy X").

## 2. Các bước thực thi chuẩn

### Bước 1: Kiểm tra trạng thái ADB & Loại trừ máy Offline
- Kiểm tra `adb devices` xem các máy yêu cầu chạy lại có đang `device` (ONLINE) hay không.
- Nếu máy bị rớt kết nối (`offline` / `device not found`), ghi nhận để báo cáo riêng, không đưa vào danh sách chạy.

### Bước 2: Quarantine Dead Blocked Locks
- Các máy lỗi ở batch trước giữ trạng thái `status=blocked` (TTL 90m) để bảo vệ hiện trường lỗi.
- Khi user trực tiếp chỉ đạo chạy lại, operator decision đã được xác lập. Di chuyển các file lock cũ của máy (với PID đã chết) sang thư mục quarantine:
  ```python
  import shutil
  from pathlib import Path
  from datetime import datetime, timezone
  
  root = Path.home() / ".codex" / "device-locks"
  quarantine = Path.home() / ".codex" / "device-locks-reaped" / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}_user_rerun"
  quarantine.mkdir(parents=True, exist_ok=True)
  
  target_machines = {10, 13, 28, 57, 60, 62, 63, 69, 71}
  for p in root.glob("*.json"):
      if p.name.startswith("."): continue
      # parse machine number and move if in target_machines
      shutil.move(str(p), str(quarantine / p.name))
  ```

### Bước 3: Cô lập danh sách chạy với `TIKTOK_REG_SKIP_STTS` & Khóa thiết bị
- Kiểm tra toàn bộ danh sách `pending` từ `_detect_clean.py`.
- Tập hợp danh sách các máy KHÔNG thuộc diện rerun vào `TIKTOK_REG_SKIP_STTS` (ví dụ: `export TIKTOK_REG_SKIP_STTS="75,76,77,78,79,80"`).
- Bật `export DEVICE_LOCK_ENABLED=1`.
- Khởi chạy batch bằng `python -u _run_all_targets.py` trong background với `notify_on_complete=True`.

### Bước 4: Tự động đồng bộ CSDL sau khi hoàn tất
- Sau khi `_run_all_targets.py` kết thúc, gọi `apply_tiktok_deferred_results()` hoặc:
  ```bash
  python -u D:\Taadaa\Tiktok_Reg\scripts\run_night_chain_pipeline.py
  # hoặc gọi trực tiếp apply_deferred_tracking_results.py với các tracking_result_*.json mới sinh
  ```
- Đồng bộ `taikhoan_dat_v2_updated .xlsx` sang `taikhoan_run_safe.xlsx`.

### Bước 5: Báo cáo kết quả gọn gàng
- Báo cáo rõ: Tổng số máy -> Số máy thành công (kèm STT) -> Số máy thất bại (kèm lý do phân loại cụ thể như OTP timeout, ATX dump timeout, ADB offline).
