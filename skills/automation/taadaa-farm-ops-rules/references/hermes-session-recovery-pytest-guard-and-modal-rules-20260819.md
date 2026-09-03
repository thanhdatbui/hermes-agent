# Quy Chuẩn Hermes Session Direct Recovery, Chặn Alert Pytest & Modal Live Popups (19/08)

## 1. Kiến Trúc Hermes Session Direct Recovery (Tắt Subprocess Agent)
- **Vấn đề cũ**:
  - Khi máy kẹt, `alerts.py` tự động spawn subprocess `python_runner/ai_recovery/agent.py` chạy ngầm.
  - Subprocess này không có tools, dễ lỗi parse JSON khi LLM trả về markdown block ` ```json `, fallback cứng về text `"Đã gửi phím Back để đóng màn hình"` và tự ý gửi phím BACK làm mất hiện trường.
  - Đọc nhầm comment `# OPENROUTER_API_KEY=` trong `.env` dẫn đến báo lỗi thiếu API key giả.
- **Quy chuẩn mới**:
  - **TẮT HOÀN TOÀN subprocess `agent.py` trong `alerts.py`**: Khi kẹt máy, script producer chỉ làm 1 việc: Chụp ảnh hiện trường + vẽ banner đỏ + gửi tin nhắn 1 cảnh báo về nhóm Telegram Farm Alerts.
  - **Hermes Agent trong active session Telegram trực tiếp đảm nhận điều tra**:
    - Dùng `vision_analyze` đọc ảnh thật, dùng ATX/XML đọc layout cây giao diện.
    - Sửa code tận gốc trong repo, chạy `pytest` test suite, gọi model `plan-review` qua 9Router audit diff.
    - Gửi lệnh tương tác chính xác (tap nút, vuốt lướt, swipe recovery) lên thiết bị.
  - **Xóa bỏ vĩnh viễn fallback bấm Back mù quáng**: Trong `vision_client.py`, thay `_FALLBACK_RESULT` bằng `_EMPTY_DECISION` (`action_type: none`). Nếu không phân tích được thì giữ nguyên hiện trường, tuyệt đối không gửi phím Back bừa bãi.

## 2. Chặn Gửi Cảnh Báo Telegram Khi Chạy Pytest (`PYTEST_CURRENT_TEST`)
- **Nguyên nhân**: Khi chạy unit test `pytest` (như `test_multi_machine_feed_session.py`), các test case giả lập lỗi mock `Máy 11` (`user11`) kích hoạt hàm `send_farm_machine_alert` làm spam hàng loạt tin nhắn giả lên nhóm Telegram thật.
- **Giải pháp chuẩn trong `automation_core/alerts.py`**:
  ```python
  if "PYTEST_CURRENT_TEST" in os.environ:
      return False
  ```
  Chặn 100% việc gửi cảnh báo ra Telegram khi đang chạy trong môi trường kiểm thử tự động.

## 3. Cách Ly Cooldown Nhả Follow Riêng Từng Nick (`account_row_index`)
- **Hiện tượng thực tế**: Cùng trên 1 máy, Nick ở Row 1 có thể follow thành công 6–8 người bình thường nhưng Nick ở Row 3 lại bị TikTok nhả follow (do độ trust/lịch sử tài khoản riêng).
- **Cơ chế cách ly độc lập**:
  - File state lưu theo từng nick cụ thể: `follow_state_{machine}_row_{account_row_index}.json`.
  - Cờ `follow_failed_date = "YYYY-MM-DD"`: Chỉ đánh dấu dừng follow trong ngày cho ĐÚNG NICK bị dính nhả follow.
  - Các nick khác trên cùng thiết bị (Row 1, Row 2, Row 4...) vẫn chạy lướt Feed và Follow chéo bình thường.
  - Phân biệt rõ lỗi nhả follow thật (`FOLLOW_FAILED`) với lỗi điều hướng mạng/chậm app (`MANUAL_REVIEW`), không gán cờ cooldown oan khi chỉ bị lag mạng.

## 4. Fallback Vuốt Cứu Kẹt Ở Cả Phase `before_swipe` & `after_swipe`
- **Vấn đề trên Máy 34 (Quảng cáo Enfagrow A+ / CTA popup)**:
  - Popup quảng cáo hoặc overlay xuất hiện ngay từ lúc vừa mở app (`before_swipe`).
  - Code cũ chỉ gắn `_swipe_recovery_on_stuck` ở vòng lặp sau khi đã bắt đầu vuốt video (`after_swipe`), dẫn đến `before_swipe` khi gặp popup lạ bị dừng phiên ngay lập tức.
- **Khắc phục**:
  - Gắn `_swipe_recovery_on_stuck` vào cả phase `before_swipe` trước khi gọi `manual_guard.record(...)` và `finalize_feed_session_cleanup`.
  - Khi gặp popup lạ / CTA overlay ở đầu phiên, script tự động thực hiện 1–2 cú vuốt lướt (`input swipe 540 1600 540 400 300`) để vượt qua màn hình và tiếp tục lướt Feed.

## 5. Modal Policy Popups Trên Phòng Live (Máy 05 - "Chính sách Phần thưởng và Vật phẩm ảo")
- **Đặc tính kỹ thuật**:
  - Khi lướt trúng phòng TikTok Live, TikTok có thể hiển thị Modal popup thông báo cập nhật chính sách ("Chính sách Phần thưởng và Chính sách vật phẩm ảo") với nút "Đã hiểu".
  - **Phím BACK hoàn toàn vô tác dụng đối với Modal này** (không làm tắt popup).
- **Quy trình xử lý chuẩn**:
  1. Tính toán tọa độ chính xác của nút "Đã hiểu" ở đáy popup box (trên màn hình 1080x1920, dialog từ $y \approx 457 \rightarrow 1533$, nút "Đã hiểu" nằm tại $x=540, y \approx 1490$).
  2. Gửi lệnh tap vật lý `input tap 540 1490` để đóng popup.
  3. Sau khi đóng popup về lại phòng Live: Dừng xem tự nhiên vài giây rồi tap nút `X` ở góc trên bên phải ($x=1020, y=78$) để thoát phòng Live về Feed Trang chủ.
