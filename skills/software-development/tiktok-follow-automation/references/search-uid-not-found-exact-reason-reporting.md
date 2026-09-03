# Search UID Not Found Exact Reason Reporting

## Bối cảnh & Hiện tượng
Khi chạy `tiktok-follow` (Mode 1 Search-Follow hoặc Mode 2 Search Seed Anchor), nếu một UID trong danh sách không tồn tại trên TikTok (do gõ sai chính tả từ workbook nguồn, nick đã đổi tên hoặc nick bị xóa/ban):
- Runner tìm kiếm trên thanh Search, đã kiểm tra cả tab **Top** và tab **Người dùng** nhưng không có kết quả khớp 100%.
- Trước đây, runner fallback về chuỗi generic: `MANUAL_REVIEW: search navigation fail sau ladder (lần 2)`.

## Hậu quả & Anti-Pattern
- **Báo sai bản chất lỗi:** Báo lỗi kỹ thuật điều hướng uiautomator (`search navigation fail`) thay vì báo lỗi dữ liệu tài khoản (`ID không tìm thấy / không tồn tại`).
- **Gây khó khăn cho vận hành:** Operator không biết lỗi do script bị hỏng hay do nick trong danh sách sai để đối soát lại workbook.

## Quy tắc xử lý chuẩn
1. Khi kiểm tra xác nhận màn hình hiện tại là màn hình kết quả tìm kiếm (`_is_search_screen_or_results(final_xml) is True`) mà không có UID mục tiêu:
   - Trả về lý do rõ ràng: `ID không khớp sau search (không tìm thấy @{uid} trong kết quả tìm kiếm) — bỏ qua`.
   - Nếu trong chế độ Mode 1: Đánh dấu `skipped`, thêm vào `failed_ids` để báo cáo chi tiết về Telegram, tự động tiếp tục duyệt UID tiếp theo mà không làm crash phiên.
   - Nếu trong chế độ Mode 2 (Seed Anchor): Bỏ qua anchor này, chuyển sang anchor tiếp theo trong pool.
2. Mọi thông báo alert / log phải ghi rõ chính xác UID bị lỗi để operator đối soát sheet nguồn ngay lập tức.
