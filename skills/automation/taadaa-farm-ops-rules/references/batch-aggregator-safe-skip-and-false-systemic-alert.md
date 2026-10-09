# Bóc Tách Safe-Skip Khỏi Failed Trong Batch Aggregator Chống False Systemic Alert

## 1. Hiện Tượng & Triệu Chứng
- **Cảnh báo Telegram:** `🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG` xuất hiện trong các ca chạy Slot sâu (Row 4, Row 7, v.v.).
- **Signature vượt ngưỡng:** `script-blocker:account row <N> is empty (no username) for <device>, skipping` chiếm tỷ lệ lớn (ví dụ 45/80 máy, ~56% batch).
- **Thực tế hiện trường:** Các máy này chưa được tạo hoặc gán nick ở Slot/Row đó trong workbook (trường username là `None`). Script runner chủ động thực hiện **SAFE SKIP** theo đúng thiết kế hệ thống, không phải lỗi thực thi hay lỗi phần cứng.

## 2. Nguyên Nhân Cốt Lõi (Anti-Pattern)
- `batch_aggregator.py` chỉ kiểm tra nhị phân: `succeeded = status in ('completed', 'success', 'ok')`. Mọi máy có `succeeded = False` đều bị ném vào danh sách `failed`.
- 45 máy skip hợp lệ bị gộp thành một cụm signature lỗi hệ thống duy nhất, vượt ngưỡng kép (rate >= 10% và count >= 3), kích hoạt cảnh báo đỏ lan rộng giả (False Alarm) làm nhiễu loạn điều phối farm.

## 3. Quy Tắc Bất Biến (Invariant Rules)
1. **Bóc tách 3 trạng thái độc lập:**
   - `succeeded`: Hoàn thành tốt nhiệm vụ.
   - `skipped`: Bỏ qua an toàn do điều kiện nghiệp vụ (chưa có nick, máy chưa đến ca, device lock hợp lệ).
   - `failed`: Thực thi thất bại thực sự (crash, timeout, navigation fail, captcha, offline).
2. **Kỷ luật tính Error Budget / Failure Rate:**
   - Tử số `failed_count` **TUYỆT ĐỐI KHÔNG** chứa các máy `skipped`.
   - Các máy `skipped` không bao giờ được tham gia vào việc tạo cụm signature lỗi hệ thống (`systemic_signatures`).
3. **Mẫu nhận diện Safe-Skip chuẩn:**
   - Status: `skipped`, `skipped-empty`, `skip`, `skipped-device-locked`.
   - Error/Reason keywords:
     - `is empty (no username)`
     - `does not have valid row`
     - `account workbook does not have valid row`
     - `skipped-empty`
     - `skipped-device-locked`
     - `deferred_locked`
4. **Định dạng hiển thị báo cáo Telegram:**
   - Khi có máy skip (`skipped_count > 0`):
     `• Quy mô batch: {total_machines} máy | Thành công: {succeeded_count} | Bỏ qua: {skipped_count} | Thất bại: {failed_count}`
   - Giữ tương thích ngược khi không có máy skip (`skipped_count == 0`):
     `• Quy mô batch: {total_machines} máy | Thành công: {succeeded_count} | Thất bại: {failed_count}`

## 4. Kỷ Luật Điều Phối GATE 3 (Circuit Breaker) Khi Sửa Batch Aggregator
- Khi dispatch worker subagent thực hiện sửa code trên các file cốt lõi (`batch_aggregator.py`, `results.py`):
  - Nếu worker subagent bị timeout hoặc trả về `0 files modified` (thất bại cấu trúc):
  - **CẤM** retry lại prompt mô tả tự do hoặc giao goal mở.
  - **BẮT BUỘC** Coordinator tự grep O(1) xác định anchor duy nhất tuyệt đối (`count == 1`), cấp **EXACT PATCH CONTRACT** (`old_string` -> `new_string`) hoàn chỉnh.
  - Worker ở lượt retry thứ 2 chỉ việc gọi đúng lệnh patch và chạy test suite verification (<30s).
