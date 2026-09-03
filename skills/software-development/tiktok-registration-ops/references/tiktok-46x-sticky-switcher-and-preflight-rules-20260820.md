# TikTok 46.x Sticky Account Switcher Pattern & Preflight Conventions

## 1. Định nghĩa "Máy rảnh chạy reg TikTok"
Khi user yêu cầu kiểm tra hoặc chạy máy rảnh reg TikTok, bắt buộc thỏa mãn đồng thời 3 điều kiện:
1. **Rảnh lịch Cron:** Không trùng ca nuôi và cách ca nuôi kế tiếp tối thiểu 60 phút.
2. **Có mail chờ reg:** Máy có tài khoản mail hợp lệ trong `gmail_clean_v2.xlsx` chưa có TikTok ID trong `taikhoan_dat_v2_updated .xlsx`.
3. **VPN / Live IP Passed:** Bắt buộc broadcast `vn.vichanger.app.GET_IP` trả về `result=200` và IP hợp lệ (không chạy trên máy `result=0` hay mất VPN để tránh lộ IP).

## 2. Xử lý mở Account Switcher (Profile Header Sticky Bar)
Trên TikTok phiên bản mới (46.x), giao diện Profile cá nhân thường không hiển thị mũi tên dropdown trực tiếp hoặc bấm vào username không mở được danh sách tài khoản:
- **Cơ chế:** Khi vuốt màn hình lên ~400px (`input swipe 540 1000 540 600 400`), thanh top header sẽ thu gọn thành **Sticky Switcher Bar** nằm ở đỉnh màn hình (`bounds` y <= 350px, ví dụ resource-id `com.ss.android.ugc.trill:id/pcs` hoặc `p01`/`p1j`/`qx0`/`qzr`).
- **Thực thi:**
  1. Kiểm tra node sticky bar ở vùng y <= 350px -> Tap trung tâm node (`(540, 150)`).
  2. Nếu chưa thấy, tự động vuốt lên 400px (`swipe(device_id, 540, 1000, 540, 600, 400)`) để kích hoạt sticky bar trước khi retry.
  3. Bấm vào sticky bar sẽ bung Bottom Sheet "Chuyển đổi tài khoản" kèm nút "Thêm tài khoản" chuẩn xác.
