# Pitfall: Phân biệt Nút Follow của 'Tài khoản được đề xuất' vs Trạng thái Profile Chính

## Bối cảnh & Hiện trường
Khi mở trang Profile TikTok (đặc biệt sau khi bấm follow hoặc khi profile đã được follow):
1. TikTok thường tự động bung khay **"Tài khoản được đề xuất ⓘ"** (Suggested Accounts) dạng thẻ ngang (carousel) nằm ngay dưới nút action chính (`Nhắn tin`, `Đã follow ▼`).
2. Trên mỗi thẻ tài khoản đề xuất có một nút màu đỏ **`Follow`**.
3. Nút chính của Profile mục tiêu lúc này đã chuyển sang `Đã follow ▼` (hoặc `Nhắn tin` + `Bạn bè`).

## Nguy cơ phân tích sai (Anti-pattern)
- **Nhầm lẫn trạng thái follow:** Nếu matcher/classifier gom toàn bộ node text có chữ `Follow` trên màn hình (hoặc `bounds[1] < 1200` & `id/fds`, `id/follow_button`), nó sẽ thấy xuất hiện cả node `Follow` màu đỏ lẫn `Đã follow`. Điều này khiến classifier trả về `"unknown"` hoặc `"not_followed"`, suy diễn sai rằng anchor bị nhả follow (`FOLLOW_FAILED`).
- **Thực tế:** Anchor **ĐÃ FOLLOW** thành công; chữ `Follow` đỏ thuộc về nick gợi ý bên dưới.

## Quy tắc xử lý chuẩn
1. **Lọc bỏ triệt để Suggested Accounts:**
   - Các nút `Follow` nằm trong container đề xuất (thường có layout con chứa `Tài khoản được đề xuất`, `Xem tất cả >`, hoặc subtext `Được follow bởi...`, `Bạn bè với...`) phải bị loại trừ khỏi tập node action header của profile chính.
2. **Xử lý Anchor có `0 Đã follow`:**
   - Nếu profile anchor có chỉ số `0 Đã follow` (hoặc 0 Following), không có danh sách người theo dõi để quét nick nội bộ. Cần nhận diện sớm để skip sang anchor kế tiếp thay vì bấm vào tab trống rồi timeout xác nhận RecyclerView.
