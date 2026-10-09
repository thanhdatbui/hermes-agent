# Pitfall: Post-Auth Late Password Handling & Unit Test Mocking

## 1. Lỗi NameError `fill_password` trong `handle_post_auth_screens`
- **Hiện tượng:** Trong quá trình reg TikTok tại `social_reg_v1.py`, nếu gặp màn hình tạo mật khẩu muộn (late password) trong `handle_post_auth_screens()`, code từng gọi nhầm `fill_password(device_id, email, stt=stt)` dẫn đến crash:
  `NameError: name 'fill_password' is not defined`
- **Cách xử lý đúng:**
  Hàm chuẩn trong `social_reg_v1.py` là `fill_password_and_login(device_id, password, stt=None)`.
  Cần trích xuất password từ metadata hoặc tự sinh nếu chưa có:
  ```python
  tracking_meta = get_tracking_account_meta(email)
  tiktok_pw = (tracking_meta.get("pass") or "").strip()
  if not tiktok_pw:
      tiktok_pw = make_tiktok_password()
  fill_password_and_login(device_id, tiktok_pw, stt=stt)
  ```

## 2. Pitfall khi mock test `handle_post_auth_screens`
- **Vấn đề:** Trong mỗi vòng lặp `for _r in range(max_rounds):` của `handle_post_auth_screens()`, code gọi:
  1. `xml = get_ui_xml(device_id)`
  2. `if maybe_save_login_info_prompt(device_id):` -> hàm này gọi tiếp `get_ui_xml(device_id)`.
- **Hậu quả:** Nếu mock `get_ui_xml` bằng danh sách `side_effect=[pw_xml, main_xml]`, mock sẽ bị cạn kiệt ngay ở vòng lặp đầu và raise `StopIteration`.
- **Giải pháp:**
  - Mock `maybe_save_login_info_prompt` return `False`:
    `patch.object(social, "maybe_save_login_info_prompt", return_value=False)`
  - Hoặc dùng dynamic callable cho `side_effect` của `get_ui_xml`.
