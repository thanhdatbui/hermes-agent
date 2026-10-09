# Quy Trình Đối Soát & Tự Động Đồng Bộ Excel Sau Batch Reg (17/09/2026)

## 1. Nguyên nhân lệch pha Excel ↔ Máy thật
- Khi chạy batch reg qua `_run_all_targets.py` với cờ `--defer-tracking-write`, mỗi worker con chỉ tạo file JSON kết quả `tracking_result_stt*.json` để tránh tranh chấp ghi đồng thời.
- Nếu launcher không tự động sync, nick đã tạo thành công nằm trên máy thật (8/8 nick) nhưng Excel vẫn trống.
- Khi đến ca nuôi: Ca nuôi đọc Excel thấy trống ID → Báo thiếu slot → Trigger chạy reg đè lên máy đã kịch trần 8 nick.

## 2. Quy tắc bắt buộc khi hoàn thành batch reg
- Ngay sau khi batch tiến trình reg hoàn tất: Runner BẮT BUỘC tự động gom toàn bộ `result_json` của các máy thành công và gọi `write_deferred_results_sequential` để ghi khóa độc quyền vào file Excel `taikhoan_dat_v2_updated .xlsx`.
- Bắt buộc tạo bản sao lưu workbook (`backup_tracking_workbook`) trước khi thực hiện ghi.
- Trong trường hợp dòng mong muốn (`tracking_row`) bị lệch hoặc file JSON thiếu tọa độ: Bắt buộc dùng `resolve_tracking_slot(ws, stt, email)` để tự động dò tìm dòng trống tiếp theo của máy thay vì block nhầm.

## 3. Nhận diện trần cứng 8 tài khoản TikTok
- App TikTok obfuscate danh sách tài khoản: `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"]`.
- Khi đếm đủ 8 nick trên giao diện bottom sheet: Nút "Thêm tài khoản" biến mất. Code phải raise ngoại lệ `MACHINE_FULL_8_ACCOUNTS`, gửi phím Back thoát sheet và phím Home. CẤM raise lỗi sai cấu trúc `[04_add_account] Không tìm thấy`.
