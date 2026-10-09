# Unit Test Discipline: Mocking UI State Loops & Preventing StopIteration

## 1. Bối cảnh & Vấn đề (StopIteration Trap & Blind Counter Trap)
Trong các automation runner (TikTok Reg, TikTok Follow, TikTok Login, Google OAuth, ChatGPT Register...), các hàm xử lý màn hình sau auth (như `handle_post_auth_screens`, `dismiss_profile_overlays`, `poll_ui_state`, `register_chatgpt_on_device`) thường chạy dạng vòng lặp `for _round in range(max_rounds):` hoặc `while True:`.

Khi viết unit test, lập trình viên thường mock `get_ui_xml` bằng một danh sách hữu hạn hoặc bộ đếm số lần gọi tuyến tính:
```python
# NGUY HIỂM 1: Dễ gây StopIteration!
with patch.object(social, "get_ui_xml", side_effect=[screen_a_xml, screen_b_xml]):
    social.handle_post_auth_screens("fake_dev", "test@test.com")

# NGUY HIỂM 2: Dễ gãy khi hàm có nhiều lần gọi get_ui_xml trong cùng 1 vòng lặp (Blind Counter Trap)!
calls = 0
def xml_side_effect(device_id):
    nonlocal calls
    calls += 1
    if calls == 1:
        return email_screen_xml
    elif calls == 2:
        return otp_screen_xml  # BỊ BẪY: calls == 2 rơi vào get_ui_xml ngay sau khi gõ email chứ chưa bấm Tiếp tục!
    return empty_xml
```

### Tại sao bị crash `StopIteration` hoặc sai lệch logic?
1. **StopIteration**: Trong Python `unittest.mock.MagicMock`, khi truyền một `list` hoặc iterator vào `side_effect`, nếu hàm production gọi `get_ui_xml` nhiều hơn số phần tử, iterator bị cạn kiệt (exhausted) và ném ra `StopIteration`.
2. **Blind Counter Trap**: Một vòng lặp xử lý form thường gọi `get_ui_xml()` nhiều lần trong 1 round:
   - Check modal/cookie -> gọi XML lần 1 & 2
   - Gõ text vào ô input -> gọi XML lần 3
   - Bấm nút Submit -> gọi XML lần 4
   - Quay lại đầu vòng lặp để verify kết quả -> gọi XML lần 5
   Nếu mock dùng số đếm cứng `calls == 1`, `calls == 2`, các lần gọi refresh trung gian sẽ nuốt mất màn hình đích khiến hàm kết luận sai (ví dụ: `FAILED_AT_EMAIL_SUBMIT` thay vì chuyển sang OTP).

---

## 2. Giải pháp chuẩn: Dùng Dynamic Callable / State-Driven Mock

Thay vì truyền một danh sách cứng `[a, b]` hoặc bộ đếm số thứ tự đơn sơ, sử dụng các pattern sau:

### Pattern A: Counter với Fallback về Màn hình Đích (Khuyên dùng cho loop thăm dò đơn giản)
```python
def test_handle_post_auth_screens_password_late():
    pw_xml = '<hierarchy><node package="com.ss.android.ugc.trill" text="Tạo mật khẩu" /></hierarchy>'
    main_xml = '<hierarchy><node package="com.ss.android.ugc.trill" text="Dành cho bạn" /></hierarchy>'
    
    calls = [0]
    def fake_get_ui_xml(device_id):
        calls[0] += 1
        if calls[0] <= 2:
            return pw_xml
        return main_xml  # Sau các bước setup, luôn trả về màn chính an toàn

    with patch.object(social, "get_ui_xml", side_effect=fake_get_ui_xml), \
         patch.object(social, "maybe_save_login_info_prompt", return_value=False), \
         patch.object(social, "get_tracking_account_meta", return_value={"pass": "MetaPass123!"}) as mock_meta, \
         patch.object(social, "fill_password_and_login") as mock_fill, \
         patch.object(social.time, "sleep"):
        social.handle_post_auth_screens("fake_dev", "test@test.com", stt=74)
        mock_meta.assert_called_with("test@test.com")
        mock_fill.assert_called_with("fake_dev", "MetaPass123!", stt=74)
```

### Pattern B: Mock Triệt để các Check Phụ trong Loop
Trong vòng lặp xử lý UI, ngoài `get_ui_xml`, các hàm phụ như `maybe_save_login_info_prompt`, `_dismiss_tiktok_draft_resume_popup`, `_dismiss_tiktok_config_restore_dialog` có thể tự dump XML hoặc gọi ADB nếu không được mock.
- Luôn mock tường minh các prompt checker phụ để tránh nhánh rẽ không mong muốn:
  `patch.object(social, "maybe_save_login_info_prompt", return_value=False)`
- Mock `time.sleep` để test chạy tức thì (<1s thay vì chờ nhiều giây sleep).

### Pattern C: State-Driven Mocking (Khuyên dùng cho quy trình nhiều bước phức tạp)
Đối với flow tuần tự (như Đăng ký tài khoản: Dismiss dialog -> Cookie -> Nhập form -> Submit -> Nhận OTP -> Xác nhận -> Về Home):
Dùng biến trạng thái `state` để chuyển giao XML tương ứng với sự kiện tiếp theo, có fallback an toàn:
```python
state = "INIT"
def xml_side_effect(device_id):
    nonlocal state
    if state == "INIT":
        state = "AFTER_DISMISS"
        return "<node text='Bỏ qua Đăng nhập Địa chỉ email' bounds='[100,500][900,600]' clickable='true' />"
    elif state == "AFTER_DISMISS":
        state = "AFTER_TYPED"
        return "<node text='Địa chỉ email Tiếp tục' bounds='[100,500][900,600]' clickable='true' />"
    elif state == "AFTER_TYPED":
        state = "AFTER_SUBMIT"
        return "<node text='Tiếp tục' bounds='[100,500][900,600]' clickable='true' />"
    elif state == "AFTER_SUBMIT":
        state = "OTP_SCREEN"
        return "<node text='auth.example.com/email-verification Kiểm tra hộp thư đến' />"
    return "<node text='Hộp thư đến trống' />"
```
Pattern này không bị phụ thuộc vào số lượng lệnh refresh XML trung gian trong hàm thực thi, giúp unit test phản ánh chính xác luồng UI thực tế và luôn pass 100% trong thời gian siêu tốc (<1s).
