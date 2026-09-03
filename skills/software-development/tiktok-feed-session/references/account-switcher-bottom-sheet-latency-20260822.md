# Account Switcher Bottom Sheet & Switch-Anchor Tap Pitfall (TikTok 46.x)

## Bối cảnh & Hiện tượng
- **Lỗi:** `manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`
- **Tình huống:** Khi feed session chuyển sang tài khoản kế tiếp (profile preflight), script cố gắng mở popup/bottom sheet "Chuyển đổi tài khoản" bằng cách tap vào tên tài khoản (`switch_anchor`).

## Cơ chế hoạt động của TikTok 46.x
1. **Vị trí tên tài khoản trên Profile:**
   - Khi ở đầu trang Profile (chưa cuộn), tên hiển thị / username nằm ở vùng giữa màn hình (bounds khoảng `[302,489][778,555]`, tâm `(540, 522)`).
   - Khi vuốt cuộn màn hình lên (`_profile_scroll`), tên tài khoản sẽ thu nhỏ dính lên thanh tiêu đề trên cùng (Sticky Header, Y < 300-400).
   - **Tap vào tên tài khoản (dù ở giữa Y=522 hay trên sticky header) đều mở bảng trượt "Chuyển đổi tài khoản" (Bottom Sheet)**.

2. **Nguyên nhân gây lỗi giả (`account-switcher-not-open`):**
   - **Animation & Render Latency:** Sau khi tap vào tên tài khoản `(540, 522)`, bảng trượt mất khoảng 1.0 - 2.0s để trượt lên và hoàn tất render XML cây UI.
   - Nếu `_capture_xml_text` chụp quá sớm hoặc UI dump rơi đúng thời điểm đang chuyển cảnh, XML chưa có node tiêu đề `"Chuyển đổi tài khoản"` / `"Switch account"`.
   - Script tưởng nhầm là bị kẹt overlay/bàn phím nên bấm phím `Back` (keyevent 4) làm đóng luôn bảng switcher vừa mới mở, sau đó fail-closed báo lỗi `manual-needed:account-switcher-not-open`.

## Quy trình xử lý & Khắc phục
1. **Kiểm tra hiện trường:**
   - Chụp ảnh màn hình (`screencap -p`) để xem bảng "Chuyển đổi tài khoản" thực tế có mở ra hay không.
   - Nếu bảng đã mở (có danh sách nick và "Thêm tài khoản"): xác nhận nick đã đăng nhập trên máy.
2. **Khắc phục trong script:**
   - Tăng thời gian settle/sleep sau khi tap `switch_anchor` (tối thiểu 1.5s - 2.0s) trước khi dump XML kiểm tra `_is_profile_account_switcher_xml`.
   - Bắt buộc kiểm tra `_looks_like_titleless_account_switcher_xml` hoặc các item tài khoản con (dấu tích chọn, avatar con, nút "Thêm tài khoản") để nhận diện switcher sheet ngay cả khi tiêu đề render chậm.
