# Chẩn Đoán Watchdog 2FA Đêm Bỏ Qua (Skip) & Bẫy Lệch Cột Workbook Admin (18/10/2026)

## 1. Hiện Tượng & Câu Hỏi Thường Gặp
- **Triệu chứng:** Báo cáo định kỳ 6H của watchdog `night-tiktok-2fa-watchdog` (job `2029d4224662`) ghi nhận số lượng `Bỏ qua` (skip) rất lớn, ví dụ:
  * Farm Kibe: Hoàn tất 21 | Bỏ qua 16 | Lỗi 35
  * Farm Admin: Hoàn tất 0 | Bỏ qua 146 | Lỗi 7
- **Câu hỏi của Operator:** "Lí do bỏ qua cả đống?"

## 2. Bản Chất Kiến Trúc Khiến Số Lượng Bỏ Qua Lớn
1. **Thiết kế Deduplication O(1) Bắt Buộc (Mỗi máy tối đa 1 nick / batch):**
   - Mỗi máy vật lý chứa từ 6 đến 8 accounts (tương ứng các slot 1–8).
   - `freeze_targets()` trong `run_batch_live_2fa.py` bắt buộc deduplicate theo máy:
     `if target.machine in machines or serial_key in serials or target.source_row in rows: continue`
   - Do đó, trong 1 batch 80 máy, tối đa chỉ có 80 accounts được đóng băng (freeze) để chạy song song. Toàn bộ các nick còn lại trên các máy này (thường từ 200–500 nick) bắt buộc phải đợi các đợt cuốn chiếu tiếp theo chứ không thể chạy dồn, tránh đụng độ màn hình và lock thiết bị.
2. **Device Lock Contention & Cooldown:**
   - Khi runner bắt đầu phân bổ thiết bị, nếu máy đang vướng `reboot_cooldown` (sau các mốc reboot 05:20, 11:20, 17:20), hoặc đang được các watchdog khác giữ lock (`feed_session_watchdog`, `clear-tiktok-cache`), runner sẽ đánh dấu `status="skipped"`, `reason="DEVICE_LOCK_UNAVAILABLE"`.
3. **Preflight Kiểm Tra An Toàn VPN / Proxy ViChanger:**
   - Runner kiểm tra `serial_is_mapped_in_workbook(proxy_mapping, target.serial)` và `require_android_vpn(...)`.
   - Nếu thiết bị chưa kết nối VPN hoặc serial chưa có trong mapping `PROXYgandienthoai.xlsx`, runner chủ động skip (`VICHANGER_VPN_NOT_CONNECTED`) để bảo vệ tài khoản khỏi lộ IP gốc.

## 3. Cạm Bẫy Lệch Cột (Column Drift) Trên File Workbook Admin
- **Hồ sơ sự cố:** Kiểm tra trực tiếp file `D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx` phát hiện **167 dòng bị dời cột**:
  * Chuỗi timestamp tạo nick (dạng `2026-09-25 08:06:55`) bị ghi nhầm vào cột `device ID` (cột thứ 10).
  * Chuỗi serial thật của máy (ví dụ `988678393355475942` hoặc `ce0516...`) bị đẩy sang cột thứ 11 (`None` header).
  * Cột `PASS` bị trống (`None`).
- **Hậu quả:**
  * Runner đọc `serial = _clean(values[serial_col - 1])`, nhận chuỗi `2026-09-25...`.
  * Khi preflight gọi ADB hoặc map proxy với serial dạng ngày tháng này, bước preflight thất bại và runner đánh dấu `skipped` ngay lập tức.
- **Biện pháp xử lý & Phục hồi:**
  * Không sửa tay trên file Excel.
  * Chạy script rà soát và dịch chuyển lại dữ liệu về đúng vị trí: nếu cột 10 có pattern `^\d{4}-\d{2}-\d{2}` và cột 11 chứa serial hợp lệ, swap/shift lại đúng cột `NGÀY TẠO` và `device ID`.
