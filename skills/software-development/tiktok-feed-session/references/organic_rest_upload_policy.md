# Quy Tắc Dưỡng Sinh & Upload Hook (Chốt Ngày 2026-10-11)

## 1. Cơ Chế Upload Hook Cả 2 Phiên (Opportunistic Upload)
- **Quy tắc:** Cờ `-AllowUploadHook` trong `tiktok_runner.py` BẮT BUỘC mở ở CẢ 2 PHIÊN (Session 1 và Session 2) của mỗi ca.
- **Lý do:** Giữ cơ chế cơ hội (Opportunistic Upload) để tối đa khả năng đăng video khi nick sẵn sàng và có video trong kho.
- **Chống trùng:** Hệ thống đã có sổ cái ca `shift_upload_history.json` tự động ghi nhận và chặn đăng trùng trong cùng ca/ngày (nếu Phiên 1 đã đăng thành công thì Phiên 2 tự động bỏ qua). CẤM Coordinator tự ý sửa `tiktok_runner.py` để hạn chế upload chỉ ở Phiên 2.

## 2. Bỏ Tỷ Lệ Dưỡng Sinh Tự Nhiên Ngẫu Nhiên (Organic Rest ~33%)
- **Chỉ đạo:** BỎ hoàn toàn việc tính toán hash MD5 ngẫu nhiên (`int(hash[:8], 16) % 3 == 0`) khiến 1/3 dàn nick tự động rơi vào ngày nghỉ dưỡng sinh.
- **Trạng thái mới:**
  - `_is_account_organic_rest_day` mặc định trả về `False`.
  - CHỈ trả về `True` khi nick nằm trong danh sách dưỡng sinh phục hồi cụ thể (`force_rest_ledger`).
- **Phân định rõ rệt:**
  - Ngày nghỉ/dưỡng sinh KHÔNG chặn upload video nếu tài khoản đủ điều kiện đăng (1 video/ngày vẫn bảo toàn).
  - Không tự ý tái lập cơ chế random dưỡng sinh toàn farm khi chưa có yêu cầu từ User.
