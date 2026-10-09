# Pitfalls & Patterns: Mocking Multi-Step UI Automation Tests

## 1. Vấn Đề: Cumulative Sleeps vs. Test Timeout
Khi viết unit tests mock cho các hàm tự động hóa Android/device multi-step (như đăng ký tài khoản, OAuth, login), logic thực tế thường có:
- Các lệnh `tap(..., wait=2.0)` hoặc `tap(..., wait=3.0)` chứa `time.sleep(wait)`.
- Các vòng lặp polling `while time.time() < deadline and (time.time() - start_t < timeout):` kèm `time.sleep(2)`.

### Triệu Chứng Lỗi
Khi test case muốn kiểm tra failure tại một bước sâu (ví dụ Bước 3 OAuth consent lỗi, hoặc Bước 5 final verification lỗi):
- Nếu test case truyền `timeout=5` hoặc `timeout=6` hoặc `timeout=30`, nhưng tổng thời gian `sleep()` tích lũy ở các bước trước (Bước 1, Bước 2, Bước 4...) vượt quá `timeout`.
- Vòng lặp verify ở bước trước chưa kịp hoàn tất hoặc vừa hết thời gian sẽ khiến hàm trả về mã lỗi của **bước trước đó** (ví dụ `FAILED_AT_ACCOUNT_SELECT` thay vì `FAILED_AT_OAUTH_CONSENT`, hoặc `FAILED_AT_ABOUT_YOU` thay vì `FAILED_FINAL_VERIFICATION`).
- Test fail với assertion mismatch khó hiểu dù mock XML đã được xếp đúng.

## 2. Giải Pháp Chuẩn

### Cách 1: Tăng `timeout` trong test call cho các kịch bản sâu
Nếu không mock `time.sleep`:
- Tính tổng các khoảng `time.sleep()` tối thiểu mà hàm phải trải qua từ Bước 1 đến bước cần test.
- Đặt `timeout` đủ lớn (ví dụ: `timeout=30` cho Bước 3, `timeout=60` cho Bước 4-5).
- Ví dụ:
  ```python
  # Bước 5 cần vượt qua Bước 1 (2s+2s) + Bước 2 (3s+1s) + Bước 3 (1.5s+3s) + Bước 4 (0.5s*3 + 3s + 2s*2):
  # Tổng sleep tích lũy ~20-25s -> timeout phải >= 60s
  res = register_step_workflow("dev1", "user@gmail.com", timeout=60)
  assert res["status"] == "FAILED_FINAL_VERIFICATION"
  ```

### Cách 2: Mock `time.sleep` khi muốn test chạy tức thì (Fast Tests)
Nếu muốn test chạy mili-giây và không phụ thuộc đồng hồ thực:
- Mock `time.sleep` bằng `@patch("time.sleep")` hoặc `@patch("module_name.time.sleep")`.
- Lưu ý: nếu hàm dùng `time.time() - start_t < timeout`, việc mock `time.sleep` không làm thay đổi `time.time()`, nên `timeout=5` vẫn đủ chạy qua toàn bộ các bước mà không bị timeout.

## 3. Quy Tắc Khảo Sát Test: Tiết Kiệm Tool Budget
- Khi user giao nhiệm vụ sửa test case với ngân sách tool hẹp (<= 3 calls):
  1. Tránh gọi nhiều lệnh `read_file` rời rạc để đọc từng đoạn code.
  2. Dùng 1 lệnh `patch` trực tiếp cập nhật test case.
  3. Dùng 1 lệnh `terminal` chạy `pytest` để xác minh ngay.

## 4. Pitfall Lệch Nhịp Call-Count khi Mock `get_ui_xml` (`calls += 1`)
Khi mock `get_ui_xml(device_id)` bằng biến đếm `calls += 1`:
```python
calls = 0
def xml_side_effect(device_id):
    nonlocal calls
    calls += 1
    if calls == 1: return "<node text='Email' />"
    elif calls == 2: return "<node text='Lỗi' />"
    ...
```
### Triệu chứng & Nguyên nhân
- Trong hàm thực tế, một bước (như nhập email, submit OTP) thường gọi `get_ui_xml` nhiều lần (ví dụ: lấy XML ban đầu để click input, lấy lại XML sau khi gõ để tìm nút Tiếp tục hoặc check lỗi tức thì).
- Biến đếm `calls += 1` rất dễ bị lệch: một lệnh gọi phụ trong nội bộ bước trước sẽ tiêu thụ mất XML dự định cho bước sau.
- Hậu quả:
  - Mock XML của bước kỳ vọng bị nuốt ở bước trước hoặc bị trôi qua.
  - Các nhánh logic tương ứng (ví dụ: reset email bằng `keyevent 29` (Ctrl+A) + `67` (DEL), hoặc bước Voice onboarding `tap(device_id, 540, 1780)`) không bao giờ được kích hoạt.
  - Test fail assertion dạng `AssertionError: shell('dev1', 'input', 'keyevent', '29', ...) call not found` hoặc `AssertionError: tap('dev1', 540, 1780, ...) call not found`.

### Giải pháp
- **Dùng State-Machine Mock thay vì Call Counter:** Theo dõi trạng thái tiến trình (ví dụ `state = "EMAIL_INPUT"`, `"EMAIL_ERROR"`, `"OTP"`, `"ONBOARDING"`) và chuyển trạng thái dựa trên các hành vi thực tế hoặc thứ tự logic.
- **Trace chính xác số lần gọi nội bộ:** Nếu bắt buộc dùng counter, cần kiểm tra tất cả các vị trí `get_ui_xml()` trong toàn bộ hàm (kể cả sau `time.sleep`, sau khi gõ text, trong vòng lặp chờ) để gán đúng chỉ số call tương ứng cho từng màn hình.

