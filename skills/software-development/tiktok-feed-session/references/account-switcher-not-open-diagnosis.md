# Account Switcher Not Open Diagnosis & Handling

## Triệu chứng
Script dừng với lỗi:
`manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`

## Nguyên nhân
1. **Nick mục tiêu đã đăng nhập và đang active sẵn nhưng Profile bị cuộn khuất Header:**
   - Khi tài khoản cần nuôi (`target_account`) đã là nick đang hiển thị trên màn hình Profile, nhưng giao diện bị cuộn xuống lưới video (scrolled video grid), node `@username` biến mất khỏi viewport XML.
   - Script đọc profile identity không thấy `@username` nên tưởng nhầm chưa khớp và cố gắng tap vào anchor Display Name trên Top Bar để mở switcher modal.
   - Việc tap vào tên tài khoản khi nick đã active không mở sheet switcher -> kích hoạt lỗi `account-switcher-not-open`.
2. **Badge thông báo che anchor:**
   - Badge thông báo đỏ (`9+`) cạnh tên tài khoản che chevron hoặc làm lệch bounds của anchor chuyển đổi.
3. **Màn hình kẹt overlay / bàn phím:**
   - Profile đang có popup hướng dẫn hoàn tất hồ sơ, overlay phím ảo che mất vùng tap.

## Quy trình kiểm tra & xử lý (Evidence-Driven)
1. **Kiểm tra màn hình Profile hiện tại & phục hồi vị trí cuộn:**
   - Khi `read_profile_identity()` phát hiện màn hình Profile nhưng không thấy `@username`, thực hiện swipe down (`540 600 -> 540 1500`) để cuộn về đỉnh trang trước khi đọc lại identity.
   - Chụp màn hình (`screencap`) và dump UI XML để đọc username (`@handle`) đang active.
2. **Đối chiếu tài khoản:**
   - Nếu username trên màn hình **trùng khớp** với tài khoản cần chạy trong workbook (`taikhoan_run_safe.xlsx` / `taikhoan_dat_v2_updated .xlsx`):
     -> Kết luận nick đã sẵn sàng, bỏ qua bước đổi tài khoản và chuyển thẳng sang lướt feed.
   - Nếu username **khác** tài khoản mục tiêu:
     -> Kiểm tra xem nick mục tiêu đã đăng nhập vào thiết bị chưa bằng reconcile/login inventory (`tiktok-log-in`).
     -> Nếu chưa đăng nhập: Nạp tài khoản vào máy qua flow login.
     -> Nếu đã đăng nhập nhưng không mở được switcher: Gửi ảnh hiện trường báo user hoặc áp dụng recovery keyevent BACK + re-tap anchor.
