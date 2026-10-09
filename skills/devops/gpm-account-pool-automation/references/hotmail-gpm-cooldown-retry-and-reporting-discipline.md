# Hotmail GPM Lifecycle Cooldown, Safe Retry & Reporting Discipline

## 1. Bản chất vấn đề
Trong pipeline vòng đời Hotmail -> GPM -> ChatGPT -> Codex -> Change Info:
- Khi đăng nhập Hotmail gặp sự cố (sai pass, challenge Microsoft, lỗi GPM API, timeout proxy), tài khoản được gán `status: BLOCKED` hoặc `FAILED`.
- Nếu scheduler/supervisor áp dụng luật cứng "CẤM retry tài khoản BLOCKED/FAILED", các tài khoản lỗi tạm thời sẽ bị kẹt vĩnh viễn (starvation), không bao giờ có cơ hội phục hồi.
- Ngược lại, nếu unblock ngay lập tức hoặc không kiểm soát, IP proxy và tài khoản sẽ bị Microsoft đánh dấu bot/spam và khóa vĩnh viễn (hard ban).

## 2. Quy tắc Cooldown & Auto-Unblock an toàn (48h)
Khi xây dựng logic quay vòng tự động cho `HOTMAIL_LOGIN`:
1. **Ngưỡng giãn cách an toàn**: Cooldown tối thiểu giữa các lần thử lại là **48 giờ (2 ngày)**. Đây là thời gian chuẩn để Microsoft giải phóng rate-limit / suspicious activity tạm thời trên IP và mailbox.
2. **Chống unblock mù (Fail-Safe Validation)**:
   - BẮT BUỘC kiểm tra timestamp thất bại từ `last_result.at` của chính stage `HOTMAIL_LOGIN` (`last_result.stage == 'HOTMAIL_LOGIN'` và `status in {'FAILED', 'ERROR', 'BLOCKED'}`).
   - BẮT BUỘC parse được datetime hợp lệ.
   - NẾU timestamp bị thiếu (`None`), rỗng, hoặc malformed: GIỮ NGUYÊN trạng thái `BLOCKED`, TUYỆT ĐỐI KHÔNG tự tiện unblock ngay.
3. **Cơ chế chống retry vô tận (Quarantine Gate)**:
   - Duy trì trường đếm `login_retry_count` trên từng profile.
   - Mỗi lần auto-unblock thử lại thất bại, tăng `login_retry_count += 1`.
   - Nếu `login_retry_count >= 3`, chuyển trạng thái sang `QUARANTINE` với lý do `Max login retries exceeded (3/3)`, không cho phép tự động unblock nữa để bảo vệ tài sản nick.
4. **Structured Telemetry**:
   - Khi unblock: ghi log telemetry `hotmail_login_cooldown_unblock` kèm machine, email, retry_count, proxy_port.
   - Khi fail: ghi log telemetry `hotmail_login_failed` kèm context lỗi chi tiết.

## 3. Kỷ luật Báo cáo Định kỳ (Anti-Truncation & Grouping)
- **CẤM cắt ngang danh sách lỗi phẳng (`[:15]`)**: Khi tổng số lỗi lớn (ví dụ 200+ nick), việc in top 15 theo thứ tự ngẫu nhiên sẽ làm nuốt trọn toàn bộ các nhóm lỗi khác (ví dụ Codex OAuth nuốt sạch Hotmail Login).
- **Phân nhóm bắt buộc theo Stage**: Báo cáo định kỳ (6h / 12h) bắt buộc phải gom nhóm theo từng Stage:
  - `[HOTMAIL_LOGIN] (N acc)`: Liệt kê máy, email đại diện và lỗi xác thực.
  - `[CODEX_OAUTH] (N acc)`: Liệt kê máy, email đại diện và tình trạng OTP/5SIM.
  - `[CHATGPT_REG] (N acc)`: Liệt kê lỗi tạo profile hoặc cloudflare.
- **Đối soát trạng thái DONE**: Bộ đếm hoàn tất chu kỳ phải kiểm tra cả `stage == "DONE"` và `status == "DONE"` để tránh bỏ sót các tài khoản đã hoàn thành toàn bộ các bước bảo mật.
