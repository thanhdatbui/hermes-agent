# Ad Fast-Skip (Sponsored Videos) Pattern

## Mục tiêu
Tối ưu hóa thời gian chạy feed và bảo vệ tài khoản tránh tương tác nhầm vào các video quảng cáo/được tài trợ (Sponsored).

## Chi tiết cơ chế
1. **Dấu hiệu nhận diện (`SPONSORED_TEXTS`):**
   - Tiếng Việt: `"Được tài trợ"`
   - Tiếng Anh: `"Sponsored"`
   - Kiểm tra cả thuộc tính `text` lẫn `content-desc` trong UI XML hierarchy.

2. **Hành vi xử lý (Fast-Skip):**
   - Bỏ qua tương tác: không like, không comment, không follow.
   - Giảm thời gian chờ: thay vì xem đủ thời lượng video (5s - 15s), chuyển sang `fast-skip` chỉ delay 0.5s - 1.0s.
   - Swipe ngay lập tức sang video kế tiếp.
   - Không cộng dồn vào hạn mức / số lượng video feed hợp lệ cần tương tác trong session.
