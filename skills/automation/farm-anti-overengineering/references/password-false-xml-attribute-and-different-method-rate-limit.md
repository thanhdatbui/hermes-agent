# Android UI Automator password="false" Raw XML Pitfall & TikTok Different Method Rate-Limit

## 1. Pitfall: Chuỗi con 'password' trên raw XML dính thuộc tính password="false"
- **Nguyên nhân:** Khi tìm kiếm keyword mật khẩu trên raw XML dump (hoặc `strip_accents(raw_xml).lower()`), mọi node `EditText` / `TextView` trên Android UI Automator đều có thuộc tính `password="false"`.
- **Hậu quả:** Chuỗi `"password"` luôn xuất hiện trong raw XML $\rightarrow$ False positive nhận diện màn hình đã đăng ký / màn hình nhập password, khiến script bỏ qua luồng đăng ký mới.
- **Quy chuẩn:**
  1. Loại bỏ `"password"` khỏi danh sách keyword quét text thô (`reg_fallback`).
  2. Bắt buộc dùng parser bóc tách text/desc (`_tiktok_flat_xml`) thay vì raw XML.
  3. Kiểm tra node `EditText` chuyên biệt: `nodes = list_edittext_nodes(xml)` và chỉ xác nhận password khi `any(n.get("password") for n in nodes)`.

## 2. Nhận diện lỗi Rate-Limit / "Different Method"
- **Nguyên nhân:** Khi bị chặn hoặc rate-limit, TikTok hiển thị banner: *"Please try again or log in with a different method."* (hoặc tiếng Việt *"phương thức khác"*).
- **Hậu quả:** Không nhận diện được banner này khiến script chờ hết timeout 30s hoặc lặp vô hạn.
- **Quy chuẩn:**
  1. Bắt `"different method"` và `"phuong thuc khac"` trong `detect_after_continue` (trả về `"error_different_method"`) và `_post_auth_ui_state` (trả về `"rate_limited"`).
  2. Đưa `"rate_limited"` vào danh sách dừng sớm trong `wait_login_success` và `handle_post_auth_screens` để fast-fail và báo cáo trạng thái ngay lập tức.
