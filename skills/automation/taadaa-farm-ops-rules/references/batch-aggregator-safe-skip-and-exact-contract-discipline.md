# Bóc Tách Safe-Skip Khỏi Failed & Kỷ Luật Exact Patch Contract Cho Worker

## 1. Bối Cảnh Sự Cố & Hiện Tượng Lỗi (17/09/2026)
- **Hiện tượng:** Ca nuôi acc TikTok / lướt feed chạy ca Row 7 (slot 7) phát cảnh báo đỏ toàn fleet: `[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG` với tổng tỷ lệ thất bại 62.5% (50/80 máy).
- **Cụm lỗi vượt ngưỡng kép:** `script-blocker:account row 7 is empty (no username) for <device>, skipping` (45/80 máy, chiếm 90% số máy lỗi).
- **Bản chất hiện trường:** Các máy trên farm có số lượng nick khác nhau (1–6 nick/máy). Khi chạy ca sâu như Row 7 hoặc Row 8, những máy chưa có nick ở row đó sẽ được script feed thực hiện **Safe-Skip** theo đúng thiết kế (không phải lỗi thực thi).
- **Lỗi hệ thống (Anti-Pattern):** Bộ tổng hợp `batch_aggregator.py` trước đây gom toàn bộ kết quả không phải `succeeded` vào nhóm `failed`, khiến 45 máy skip hợp lệ bị biến thành 45 máy fail với signature `script-blocker`, kích hoạt cảnh báo sai lệch.

## 2. Quy Tắc Bóc Tách Safe-Skip Trong Telemetry & Batch Aggregator
- **Nguyên tắc bất biến:** *"Watchdog & Aggregator bóc tách skip thay vì gom Khác"*.
- **Các chuỗi nhận diện Safe-Skip bắt buộc:**
  - `is empty (no username)`
  - `does not have valid row`
  - `account workbook does not have valid row`
  - `skipped-empty`
  - `skipped-device-locked`
  - `deferred_locked`
- **Mô hình hóa dữ liệu chuẩn:**
  - `MachineResult`: Phải có trường `skipped: bool = False`.
  - `BatchAggregationReport`: Phải có trường `skipped_count: int = 0`.
  - Phân loại rõ ràng 3 nhóm:
    1. `succeeded = [r for r in results if r.succeeded]`
    2. `skipped = [r for r in results if r.skipped or contains_safe_skip_pattern(r)]`
    3. `failed = [r for r in results if not r.succeeded and r not in skipped]`
  - Dòng scale line: `Quy mô batch: N máy | Thành công: S | Bỏ qua: K | Thất bại: F`. Chỉ khi `failed` thực sự vượt ngưỡng kép mới kích hoạt Alert.

## 3. Kỷ Luật Điều Phối Worker Subagent (Circuit Breaker & Exact Contract)
- **Hiện tượng Worker Timeout (Gate 3):**
  - Khi Coordinator dispatch prompt dạng yêu cầu logic chung (dù có liệt kê 6 bước), Worker subagent có xu hướng đọc nhiều file, thử nghiệm hoặc bị nghẽn API $\rightarrow$ dẫn đến cạn budget hoặc timeout 600s với 0 files modified.
- **Giải pháp Circuit Breaker & Exact Patch:**
  - Khi Worker fail hoặc timeout ở lần 1, CẤM retry prompt cũ.
  - Coordinator phải tự grep O(1), xác định anchor duy nhất (`c == 1`), soạn **EXACT PATCH CONTRACT** gồm đúng khối `old_string` $\rightarrow$ `new_string` cụ thể cho từng file.
  - Worker ở lần 2 chỉ việc áp dụng đúng patch và chạy unit test focused ($<30s$). Kết quả thực tế: Worker hoàn thành toàn bộ trong 145s, 38/38 tests passed 100%.
