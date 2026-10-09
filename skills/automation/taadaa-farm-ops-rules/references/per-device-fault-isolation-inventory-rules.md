# Per-Device Fault Isolation vs Farm-Wide Crash (Kỷ Luật Cô Lập Thiết Bị Lỗi)

## Nguyên Tắc Cốt Lõi: "Sai Máy Nào Bỏ Qua Máy Đó, Tuyệt Đối Cấm Dừng Cả Farm"

Trong vận hành Phone Farm quy mô lớn (80 máy), một lỗi cấu hình hoặc xung đột dữ liệu cục bộ trên 1 máy (ví dụ: gõ nhầm 1 ô serial trong Excel, thiếu ngày tạo, lỗi format date, dính conflict) **TUYỆT ĐỐI KHÔNG ĐƯỢC PHÉP làm dừng toàn bộ 79 máy còn lại**.

### 1. Bẫy Thiết Kế Fail-Closed Quá Cứng Nhắc (Anti-Pattern)
- Trong các hàm nạp inventory / device map (như `load_device_map_from_excel`, `get_machines_ready`, `target_inventory`):
  ```python
  # SAI LẦM: Ném exception dừng khẩn cấp toàn bộ pipeline
  if conflicts:
      raise RuntimeError(f"Device map has conflicting valid serials for machine(s): {machines}")
  ```
- **Hậu quả**: Khi script launcher (`run_all.ps1`, `run_night_chain_pipeline.py`, `post_noon_chain_watchdog.py`) chạy preflight, `RuntimeError` khiến toàn bộ tiến trình ném `Exit Code 1`, tổng số máy chạy = 0, toàn farm bị tê liệt chỉ vì 1 dòng Excel bị gõ nhầm.

### 2. Quy Chuẩn Xử Lý Chuẩn: Graceful Exclusion & Logging (Pattern Chuẩn)
- **Cô lập lỗi theo từng máy**:
  ```python
  # CHUẨN: Log cảnh báo, loại riêng máy bị lỗi khỏi danh sách, cho phép các máy khác chạy bình thường
  conflicts = {
      stt: sorted(serials)
      for stt, serials in serials_by_machine.items()
      if len(serials) > 1
  }
  if conflicts:
      for stt, serials in conflicts.items():
          log(f"   [warn] Máy {stt:02d}: có nhiều serial khác nhau {serials} -> bỏ qua máy này để không dừng cả farm")

  device_map = {
      stt: next(iter(serials))
      for stt, serials in serials_by_machine.items()
      if stt not in conflicts
  }
  ```
- **Quy tắc cho mọi Repo Automation**:
  1. Kiểm tra tính hợp lệ của từng máy độc lập.
  2. Máy nào invalid / conflict / lock error / missing serial -> ghi log rõ ràng `[warn] Máy X: ... -> SKIP`.
  3. Lọc danh sách máy hợp lệ và tiếp tục thực thi batch cho các máy còn lại.
  4. Chỉ abort toàn pipeline nếu **TỔNG SỐ MÁY HỢP LỆ = 0** (`if len(valid_machines) == 0: exit 0 hoặc báo cáo`).
