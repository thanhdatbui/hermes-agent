# Order Archived State Blindness & SQLite SSOT Enforcement

## 1. Sự Cố "Cứ Lòi Ra Excel" & Lệch Pha Trạng Thái Đơn Hàng
- **Bối cảnh:** User đã có chỉ thị cứng: **Toàn bộ dữ liệu Farm BẮT BUỘC chuẩn hóa và lấy SQLite SSOT (`farm_master.db`) làm chuẩn duy nhất**. Excel (`QuanLyDonHang_TikTokShop.xlsx`) chỉ đóng vai trò mirror một chiều cho con người xem.
- **Triệu chứng lỗi:**
  - Đơn hàng `DH-20261029-004` (Thanh Hà Dương - Máy 2) thực tế đã có mã vận đơn `862664848314` và bưu tá J&T đã giao thành công từ ngày 01/11, đã được đánh dấu `archived: 1`.
  - Nhưng trong bảng `orders` của SQLite `farm_master.db` và JSON, các trường `customer_name`, `status`, `tracking_code` bị rỗng (`None`).
  - Khi script `order_lifecycle.py` chạy, hàm phân loại `classify_order_phase(order)` chỉ kiểm tra:
    ```python
    if is_terminal_status(status):
        return "TERMINAL"
    ```
  - Vì `status` là `None`, `is_terminal_status` trả về `False`. Script tiếp tục kiểm tra `not tracking_code` và vội vã xếp đơn 004 vào `NEED_APP_SYNC`.
  - Hậu quả: Đơn đã giao xong 2 ngày trước vẫn liên tục bị tống vào hàng đợi Phase 1, khiến watchdog cứ đến khung giờ rảnh lại đi kết nối Máy 2 để bóc app vô ích.

## 2. Quy Tắc Bắt Buộc Khi Phân Loại Vòng Đời (Archived State Gate)
1. **Kiểm tra cờ Archived ngay đầu hàm phân loại:**
   Trong `classify_order_phase(order: dict[str, Any])`:
   ```python
   archived = order.get("archived")
   if archived is True or archived == 1 or (
       isinstance(archived, str) and archived.strip().lower() in {"true", "1", "yes", "on"}
   ):
       return "TERMINAL"
   ```
   Bất kỳ đơn nào đã được đánh dấu lưu trữ/hoàn tất (dù các trường khác bị rỗng do desync) đều BẮT BUỘC xếp vào `TERMINAL` ngay lập tức, không bao giờ được lọt vào `NEED_APP_SYNC`.

2. **Cắt đứt hoàn toàn việc đọc/ghi Excel trong Runtime Loop:**
   - Watchdog nền và tiến trình theo dõi định kỳ (`order_lifecycle.py`, `watch_jt_delivery.py`, `cron_order_lifecycle.py`) BẮT BUỘC đọc và ghi trực tiếp từ SQLite SSOT (`farm_master.db` table `orders` qua `farm_db.upsert_order`).
   - Tuyệt đối cấm gọi `openpyxl` load/save workbook trong vòng lặp runtime để tránh lỗi lock file OneDrive, PermissionError và nghẽn CPU/RAM.
   - Thao tác đồng bộ dữ liệu chuẩn hóa từ file snapshot vào SQLite phải được trang bị CLI chuyên biệt (như `python D:/Taadaa/orders/order_lifecycle.py --sync-from-json` hoặc `python D:/Taadaa/tools/manage_orders.py --sync-excel`).

## 3. Khôi Phục Metadata Bị Khuyết (None) & Kỷ Luật Điều Phối
1. **Khôi phục ô `None` qua CLI chính quy (`manage_orders.py --sync-excel`):**
   - Khi phát hiện bảng `orders` trong SQLite bị khuyết metadata (như `customer_name: None`, `status: None` ở các đơn 004, 006, 008, 009):
     * Cung cấp cơ chế `--sync-excel` trong `D:/Taadaa/tools/manage_orders.py`.
     * Tự động trích xuất đầy đủ 19 cột từ Excel (tên khách hàng, SĐT, địa chỉ, số máy, slot row, TikTok handle, email, đơn giá, COD, v.v.).
     * Regex bóc mã vận đơn và nhà vận chuyển từ cột Ghi chú nếu cột Mã Vận Đơn bị để trống (`Mã:\s*([A-Za-z0-9]+)`).
     * Gọi `farm_db.upsert_order()` để lấp đầy các ô `None` trong SQLite `farm_master.db`, đồng thời tự động cập nhật `orders.json` và xuất ngược báo cáo Excel phái sinh.
2. **Kỷ luật Coordinator Guard với Terminal `python -c`:**
   - Coordinator Terminal có cơ chế DEFAULT-DENY và regex kiểm soát: `python -c` **CHỈ** được dùng cho các thao tác read-only kiểm chứng hiện trường.
   - Bất kỳ cố gắng ghi đè dữ liệu, mở file write hoặc gọi subprocess trong `python -c` đều bị Guard chặn đứng (`⛔ [COORDINATOR GUARD - TERMINAL BLOCKED]`).
   - CẤM cố gắng lách luật sửa dữ liệu bằng `python -c`. Giải pháp chuẩn là dispatch Worker bổ sung cờ lệnh chính quy vào tool chuyên trách (`manage_orders.py`), sau đó chạy lệnh CLI có sẵn trong allowlist (`python D:/Taadaa/tools/manage_orders.py --sync-excel`).
