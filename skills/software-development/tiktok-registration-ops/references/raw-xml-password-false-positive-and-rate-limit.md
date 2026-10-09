# PITFALL: Raw XML Attribute False Positive & Cascading Retry Rate-Limit

## 1. Bản chất sự cố (Sự cố Máy 34 - 07/09/2026)
Trong quy trình đăng ký TikTok (`Tiktok_Reg/social_reg_v1.py`), khi submit email ở Bước 7 (`fill_email_and_next`):
1. **Lỗi Raw XML Attribute Leak**:
   - Khi `detect_after_continue` timeout (do proxy/mạng nghẽn), script rơi vào khối `else: # unknown`.
   - Script chạy `flat_backup = strip_accents(xml_backup).lower()` trực tiếp trên **chuỗi XML thô**.
   - Mọi node trong dump XML của Android UI Automator đều có thuộc tính:
     `scrollable="false" long-clickable="false" password="false" selected="false"`
   - Danh sách nhận diện màn hình đã có tài khoản:
     `reg_fallback = ["da co tai khoan", "email nay da co", "mat khau", "password"]`
   - Vì `"password"` nằm trong thuộc tính `password="false"`, chuỗi `"password" in flat_backup` **LUÔN LUÔN là True trên 100% mọi màn hình Android**.
   - Hậu quả: Script kết luận sai rằng email đã có tài khoản (`registered`), cho đi tiếp luồng thay vì thử lại hoặc dừng.

2. **Hiện tượng Cascading Retries gây Rate-limit**:
   - Màn hình vẫn đứng ở form "Nhập địa chỉ email".
   - Bước 7c thấy vẫn còn chữ "Nhập địa chỉ email" và nút "Tiếp tục" -> tưởng là confirm email lần 2 -> gõ lại và bấm "Tiếp tục" lần 2.
   - Bước 8b thấy form vẫn còn -> gõ lại và bấm "Tiếp tục" lần 3.
   - 3 lần submit dồn dập trên cùng IP/thiết bị trong 2 phút kích hoạt bộ lọc spam của TikTok -> văng banner đỏ:
     `Please try again or log in with a different method.`

## 2. Quy tắc phòng chống bắt buộc (Defensive Rules)
1. **CẤM TUYỆT ĐỐI substring search "password" trên chuỗi XML thô**:
   - Chỉ tìm kiếm trên text đã qua lọc thuộc tính package (`_tiktok_flat_xml` hoặc `_package_flat_text` chỉ gom `text`, `content-desc`, `resource-id`).
   - Để kiểm tra có trường mật khẩu hay không, **bắt buộc** parse node qua `list_edittext_nodes(xml)` và kiểm tra thuộc tính boolean `any(n.get("password") for n in nodes)`.
2. **Nhận diện Fail-Fast các Error Banner của TikTok**:
   - Trong `detect_after_continue` và `_post_auth_ui_state`, bắt buộc kiểm tra:
     `if "different method" in flat or "phuong thuc khac" in flat:`
     $\rightarrow$ trả về `rate_limited` hoặc `error_different_method`.
   - Khi gặp `rate_limited`, dừng ngay lập tức (Fast Fail), không được để các handler phía sau (7c, 8b) tiếp tục gõ và bấm nút submit.
