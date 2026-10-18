# WinRT OCR Profile Edit State Machine & "Thêm tiểu sử" Variant Trap

## Hiện tượng & Ngữ cảnh (18/10/2026 - Máy 23 `@huynhdiem0806`)
Trong quá trình chạy script chuẩn hoá và đổi tên kênh TikTok bằng WinRT OCR (`do_rename_canonical_runner.py`), script đã chuyển thành công sang tài khoản đích nhưng bị kẹt vòng lặp 35 bước:
`UNKNOWN -> Back dong popup` rồi abort với kết quả `FAIL: vuot qua 35 buoc`.

## Nguyên nhân gốc (Root Cause)
1. **Biến thể giao diện Profile thiếu Bio:**
   - Với các tài khoản mới hoặc chưa từng thiết lập tiểu sử, TikTok không hiển thị nút chữ `Sửa hồ sơ`. Thay vào đó, nó hiển thị nút to `+ Thêm tiểu sử` (`bounds=[350, 825][730, 909]`).
   - Regex nhận diện nút sửa hồ sơ trong script chỉ tìm:
     `btn = find_box(boxes, r"(sua|chinh sua|edit)\s*h[o0]")`
     Do không khớp, `btn` trả về `None`.

2. **Bẫy tọa độ Fallback Top-Left (Collision với Find Friends):**
   - Khi `btn is None`, script nhảy vào fallback cứng:
     `xy = center(btn) if btn else XY_EDIT_PENCIL`
   - Hằng số `XY_EDIT_PENCIL` được gán cứng ở góc trên bên trái `(75, 150)`.
   - Trên phiên bản TikTok Samsung S7 (1080x1920), vị trí `(75, 150)` là biểu tượng **Tìm bạn bè** (`FindFriendsPageActivity`).
   - Tapping vào đây khiến máy nhảy sang màn hình danh bạ/mời bạn bè. Khi script thấy màn hình lạ, nó bấm Back để thoát, quay lại Profile, rồi lại tap `(75, 150)` tiếp. Vòng lặp lặp lại cho đến khi chạm giới hạn 35 bước.

## Giải pháp chuẩn hoá (Best Practice)
1. **Mở rộng nhận diện nút hành động trên Profile:**
   - Thêm regex phát hiện nút Bio:
     `btn = find_box(boxes, r"(sua|chinh sua|edit)\s*h[o0]|th[eê]m\s*ti[eê]u\s*s[uử]")`
   - Bấm vào `+ Thêm tiểu sử` sẽ dẫn thẳng vào trang chỉnh sửa thông tin hồ sơ (vừa nạp được Bio, vừa sửa được Tên hiển thị).
2. **Dời tọa độ Fallback an toàn:**
   - Tuyệt đối CẤM đặt fallback sửa hồ sơ ở góc trên `y < 200`.
   - Đặt `XY_EDIT_PENCIL` tại vùng khối nút dưới Bio/Stats: `(300, 985)` hoặc tap trực tiếp vào icon bút chì cạnh nickname ở `(904, 558)`.
