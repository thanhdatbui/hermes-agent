# Phase 1 Feed/Live Landing Trap & Quick Triage SOP

## 1. Triage Nhanh Tình Trạng Phase 1 (Zero ADB, Zero Code Mutation)
Khi user hỏi trạng thái đơn hàng / quét Phase 1 ("quét đơn phase 1 sao r?"), quy trình đối soát chuẩn:
1. **Kiểm tra trạng thái các đơn trong SQLite SSOT (`D:\Taadaa\data\farm_master.db`):**
   - Phân loại đơn: Đơn nào `TERMINAL` (đã ký nhận/hoàn thành), đơn nào `NEED_APP_SYNC` (chưa có mã vận đơn hoặc carrier 'Chờ chuyển phát').
2. **Kiểm tra lịch sử slot chạy gần nhất trong file state:**
   - `D:\Taadaa\data\order_phase1_sync_state.json`: xem `last_run_slot` và `last_run_iso`.
3. **Đối soát ảnh hiện trường (`D:\Taadaa\orders\images/`):**
   - Xem timestamp các file ảnh `order_YYYYMMDD_xxx_app.jpg`.
   - Dùng WinRT OCR qua `automation_core.ocr.ocr_screen_boxes` để đọc text/element thật trên ảnh đã chụp.
   - Tránh gọi các script nằm trong thư mục AppData/skills trực tiếp qua terminal vì sẽ bị kích hoạt Guard Self-Protection (`GUARD SOURCE BLACKLISTED`). Dùng module chuẩn `automation_core.ocr`.

## 2. Dấu Hiệu Nhận Biết Bẫy Feed / Live Landing Trap
- Các từ khóa OCR đặc trưng trên ảnh chụp:
  * `LIVE`, `Đang LIVE`, `Nhấn để xem LIVE`
  * `Đề xuất`, `Dä follow`, `Bình luận`, `Chia sẻ`
  * Khung chat trực tiếp / Tin nhắn nhóm: `Tin nhắn nhóm`, `Hoàng Chicago`, `GIF`
- Khi xuất hiện các từ khóa này mà không thấy `Đơn hàng của bạn` / `Chi tiết đơn hàng`:
  * Script điều hướng đã gặp màn hình feed phức tạp hoặc overlay live.
  * Quá 38s timeout (`ORDER_NAV_TIMEOUT_SECONDS`), hàm chụp ảnh hiện trường lưu lại màn hình feed và thoát với mã `NO_TRACKING_ON_SCREEN`.

## 3. 4 Khung Giờ Máy Rảnh Chuẩn Của Farm (Bất Biến)
Phase 1 chỉ chạy đúng 1 lần trong 4 khung giờ:
1. `04:30 – 05:00` (Sau dọn cache 04:00, trước Ca 1).
2. `10:30 – 11:00` (Sau Ca 1, trước Ca 2).
3. `16:30 – 17:00` (Sau Ca trưa, trước Ca 3).
4. `22:30 – 23:00` (Sau Ca tối, trước Ca 4).

Khi trả lời User, bắt buộc tuân thủ: Trả lời thẳng CÓ/CHƯA/ĐÚNG kèm số liệu rõ ràng ngay đầu câu theo quy định giao tiếp.
