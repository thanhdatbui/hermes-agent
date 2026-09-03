# Upload Hook Concurrency & Batch Watchdog Dynamic Budget (2026-08-27)

## 1. Bối Cảnh Sự Cố (Watchdog 75m Timeout Hàng Loạt)
- **Hiện tượng**: Trong các phiên chạy có hook Upload (phiên 3 của ca), hàng loạt máy (~40/57 máy) bị watchdog tổng ngắt với lỗi `hard outer watchdog timeout exceeded (75.0m > 75.0m)` và kích hoạt lock giữ hiện trường 2 giờ, dù thực tế các máy đã hoàn tất 10/10 lượt lướt feed và đối soát profile thành công.
- **Nguyên nhân gốc rễ**:
  1. Giới hạn `DEFAULT_UPLOAD_MAX_CONCURRENCY` trước đây là 16.
  2. Công thức timeout cũ tính cố định budget cho 1 máy đơn lẻ (`feed 2100s + follow 900s + upload 1200s + buffer 300s = 4500s = 75.0m`) rồi áp làm `hard_deadline` chung cho cả batch.
  3. Với đàn 57–74 máy chạy đồng thời, toàn bộ máy xong feed cùng lúc và xếp hàng chờ slot upload theo 3–4 đợt nối tiếp. Các máy ở đợt sau bị kẹt trong queue vượt quá mốc 75 phút và bị watchdog chém oan.

## 2. Quy Chuẩn Kỹ Thuật Đã Cập Nhật (User Approved 2026-08-27)

### A. Upload Concurrency = 20 Worker
- `DEFAULT_UPLOAD_MAX_CONCURRENCY = 20` (quản lý qua 20 OS slot lock `slot-0.lock` .. `slot-19.lock` tại thư mục tạm).
- Được phép điều chỉnh qua config: `upload_max_concurrency`.

### B. Dynamic Batch Watchdog Budgeting
Ngân sách watchdog tổng cho phiên phải được tính động theo số lượng máy thực tế trong batch:
```python
upload_waves = math.ceil(total_machines / float(upload_concurrency)) if upload_eligible else 0
worker_hard_timeout = feed_timeout + follow_budget + (upload_waves * upload_budget) + 300.0
```
- **Phiên 1 & 2 (Không upload)**: `2100s + 900s + 300s = 3300s (55.0 phút)`.
- **Phiên 3 (Có upload, đàn 57–74 máy, 20 workers/đợt = 3–4 waves)**:
  - 57 máy (3 waves): `2100s + 900s + (3 * 1200s) + 300s = 6900s (115.0 phút)`.
  - 74 máy (4 waves): `2100s + 900s + (4 * 1200s) + 300s = 8100s (135.0 phút)`.
- Đảm bảo các máy ở đợt upload cuối có đủ thời gian chờ queue và thực thi mà không bị watchdog cắt ngang.

### C. Độc Quyền Xuất Bản Kết Quả (Election Fence)
- Cơ chế atomic election `_claim_watchdog_terminal` vs `_claim_child_publication` đảm bảo:
  - Nếu worker thắng quyền xuất bản trước hạn, worker được phép hoàn tất toàn bộ chuỗi hook an toàn.
  - Nếu watchdog giành quyền xuất bản khi hết hạn, worker muộn bị fence hoàn toàn, không được ghi đè artifact hỏng hay log sai lệch.
