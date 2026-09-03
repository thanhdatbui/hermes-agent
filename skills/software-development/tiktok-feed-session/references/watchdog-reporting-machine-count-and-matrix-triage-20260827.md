# Quy tắc Báo cáo Watchdog Số Máy Chạy Thật & Phân Định Trạng Thái Ma Trận Màn Hình (2026-08-27)

## 1. Quy tắc Báo cáo Watchdog (User correction 27/08/2026)
- **CẤM hiển thị mẫu số cố định/gán cứng gây hiểu lầm** (Ví dụ `73 / 72 máy` do hardcode row 2 trong ngày lẻ chạy row 1):
  - User: *"Tự nhiên có mẫu số gì v. Phải hiện đúng theo số máy chạy chứ"*.
  - Báo cáo watchdog chỉ cần hiển thị số máy thực tế xử lý trong phiên: `• Tổng máy xử lý: X máy` (hoặc `X máy (Success Y, Fail Z)`), không tự chế mẫu số ước tính khi danh sách máy chạy theo ngày chẵn/lẻ biến động.

## 2. Nhận diện Trạng thái Ma Trận Màn Hình Farm (投工投屏 80 máy)
- **Màn hình Profile có Avatar + Nút đỏ / Bàn phím gõ / Danh sách nick:**
  - **KHÔNG PHẢI lỗi hàng loạt** mà là các máy **đang chạy Follow Hook** nối tiếp sau phiên lướt feed (đang search anchor, mở Following list, hoặc gõ UID).
- **Màn hình Home Samsung nền xanh:**
  - Là các máy **đã hoàn thành toàn bộ chu trình Feed + Follow và đã teardown về Home sạch sẽ**.
- **Khi user gửi ảnh ma trận màn hình hỏi lỗi:**
  - Kiểm tra tiến trình hệ thống (`follow_result.json`, `psutil`) để xác định các máy còn đang chạy follow dở hay đã kết thúc phiên.
