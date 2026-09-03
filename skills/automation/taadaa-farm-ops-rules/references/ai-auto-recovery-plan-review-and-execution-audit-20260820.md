# AI Auto-Recovery Execution & Plan-Review Audit (2026-08-20)

## 1. Bối cảnh & Hiện tượng
Khi các máy nuôi acc dừng phiên (ví dụ: Máy 50, Máy 53, Máy 29) và phát ra alert Telegram kèm ảnh hiện trường, nhưng không thấy phản hồi gỡ rối từ AI Auto-Recovery:
1. **Tiến trình ngầm `agent.py` bị chặn hoặc delay**:
   - `vision_client.analyze()` gọi qua 9Router (`ag/gemini-3.7-flash-high`) nếu gặp lỗi mạng hoặc unhandled exception sẽ làm crash subprocess trước khi tới bước gửi báo cáo Tin nhắn 2.
2. **Cơ chế Plan-Review Audit đối với Code Patch tự sinh**:
   - AI Vision sinh code patch (ví dụ hàm xử lý `d(text="Hủy")` kiểu cũ) khi đưa qua `plan_reviewer.audit_code_patch()` (`gpt-5.6-terra` / `plan-review`) bị REJECTED do vi phạm contract hoặc thiếu scoping container.
   - Khi patch bị REJECTED: Agent ghi nhận `audit_rejected`, KHÔNG commit code rác vào repo, và chuyển tiếp sang **Step 6: EXECUTE ACTION ON STUCK MACHINE** (dùng ADB tap/swipe giải phóng máy đang kẹt tại chỗ).
3. **Màn hình TikTok Location Permission Dialog**:
   - Tiêu đề: *"Xem nội dung phù hợp và địa điểm lân cận"* (`_LOCATION_EXACT_TITLES`).
   - Nút: *"Hủy"* (`android:id/button3`) và *"Mở cài đặt"* (`android:id/button1`).
   - Yêu cầu scoping: Phải xác thực cả 4 thành phần (title, message `android:id/message`, button1, button3) nằm trong cùng một modal container subtree thuộc package TikTok (`com.ss.android.ugc.trill`) trước khi bấm nút `Hủy` để tránh bấm nhầm button3 của dialog khác.

---

## 2. Các điểm sửa & Gia cố (Commits `812cbe5` & `10b2847`)
1. **Gia cố `agent.py`**:
   - Bọc `try-except` quanh `vision_client.analyze()` để đảm bảo agent luôn fallback an toàn về `_EMPTY_DECISION`, tiếp tục giải phóng thiết bị qua ADB và gửi báo cáo về Telegram.
2. **Kích hoạt gỡ rối trực tiếp**:
   - Test và chạy `agent.run()` thành công cho toàn bộ các máy kẹt (Máy 50, Máy 53, Máy 29), giải phóng thiết bị và cập nhật trạng thái `Farm Alerts`.
3. **Pytest Verification**:
   - Chạy 151 unit & regression tests trong `python_runner/tests/` với môi trường `python-envs/automation` (100% pass).
