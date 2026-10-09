# Kỷ luật Chống Báo Cáo Ảo (Stubbed Success) & Chặn Leak Stdout Cronjob

## 1. Bản chất sự cố 16/09/2026 (Bật 2FA Gmail on-device)
- **Hiện tượng**: Cronjob `post-morning-gmail-2fa-watchdog` báo cáo thành công 86/86 máy, nhưng kiểm tra màn hình farm thì toàn đứng ở trang "Mã dự phòng" / "Bảo mật", đối soát `gmail_clean_v2.xlsx` cột `2fa` hoàn toàn trống trơn. Đồng thời, hàng loạt dòng log điều hướng chi tiết bị xả thẳng lên Telegram group.
- **Nguyên nhân kép**:
  1. **Báo cáo ảo từ stub dở dang**: Tool con `enable_gmail_2fa_device.py` chỉ viết đến bước mở tab Bảo mật rồi hardcode `return {"status": "SUCCESS"}`. Watchdog gọi hàm chỉ kiểm tra status string thay vì kiểm tra kết quả thực tế (artifact Secret Key / ghi Excel).
  2. **Leak Stdout trong Cron no_agent=True**: Tool con dùng `print()` khắp nơi khiến toàn bộ log từng bước bị Hermes Cron gom vào stdout và deliver thẳng về Telegram.

---

## 2. Kỷ luật Bắt Buộc (Mandatory Rules)

### A. Kỷ luật Báo Cáo & Artifact-First Verification
1. **SUCCESS CHỈ ĐƯỢC CÔNG NHẬN KHI CÓ ARTIFACT CUỐI CÙNG**:
   - Đối với tác vụ bật 2FA: Bắt buộc phải có Secret Key Base32 sinh OTP hợp lệ, mã xác thực đã submit thành công và Excel đích đã được ghi nhận giá trị khác rỗng.
   - Các bước điều hướng (mở app, vào tab, bấm button) TUYỆT ĐỐI chỉ coi là `IN_PROGRESS` hoặc `INTERMEDIATE_STEP`. CẤM gán nhãn `SUCCESS` cho code dở dang.
2. **Fail-Closed khi flow chưa hoàn chỉnh**:
   - Bất kỳ script nào chưa hoàn thiện luồng e2e phải trả về `status: "INCOMPLETE"` hoặc `status: "NOT_IMPLEMENTED"`. Cấm return stub đánh lừa caller.

### B. Kỷ luật Chống Spam Log Cronjob (`no_agent: true`)
1. **Tool con câm tuyệt đối trên stdout**:
   - Trong môi trường cron `no_agent: true`, `sys.stdout` là kênh giao tiếp duy nhất gửi tin nhắn Telegram.
   - Mọi hàm con, tool bổ trợ BẮT BUỘC dùng `sys.stderr.write()` hoặc ghi file log cho các log tiến độ, cấm tiệt `print()` ra stdout.
2. **Watchdog chỉ in bảng tổng kết**:
   - Script watchdog cấp cao nhất chỉ `print()` duy nhất 1 lần khi có bảng báo cáo tổng kết cuối cùng.
   - Khi không có việc hoặc chưa đủ điều kiện: `sys.exit(0)` trong im lặng tuyệt đối (Silent Watchdog).
