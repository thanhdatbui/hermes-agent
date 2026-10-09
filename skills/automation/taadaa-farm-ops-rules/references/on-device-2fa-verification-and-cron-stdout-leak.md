# Kỷ luật Chống Leak Log Cron và Nghiệm thu Device Automation Thực chất

## 1. Cơ chế Cron `no_agent: true` và Nguy cơ Xả Log Rác (Stdout Leak)

### Bản chất cơ chế
- Trong Hermes Scheduler, cronjob cấu hình `no_agent: true` với kênh phân phối `deliver: telegram:<chat_id>` có cơ chế:
  - **Stdout rỗng (`len(stdout) == 0`)**: Silent Watchdog — Scheduler không gửi tin nhắn, hoàn toàn im lặng.
  - **Stdout có nội dung**: Scheduler bắt toàn bộ nội dung trong `sys.stdout` gửi trực tiếp thành tin nhắn Telegram.

### Lỗ hổng thường gặp
- Khi script chính gọi các hàm/tool con (ví dụ: `enable_gmail_2fa_device.py`):
  - Các hàm con dùng `print(f"[{serial}] Bắt đầu điều hướng...")`, `print(f"[{serial}] Đã vào tab...")`.
  - Toàn bộ các dòng log từng bước này xả vào `sys.stdout` của tiến trình cha.
  - Khi chạy batch hàng chục máy (ví dụ 86 máy), Scheduler xả hàng trăm dòng log vụn vặt vào nhóm chat Farm Alerts, gây spam nghiêm trọng.

### Kỷ luật bắt buộc
1. **Tool con và tiến trình trung gian**:
   - CẤM dùng `print()` để log tiến độ từng bước.
   - Mọi log gỡ lỗi, tiến độ từng nhịp UI BẮT BUỘC ghi qua `sys.stderr.write(f"[{timestamp}] ...\n")` hoặc ghi vào log file (`logging.FileHandler`).
2. **Tiến trình cha (Watchdog)**:
   - `sys.stdout` CHỈ ĐƯỢC DÙNG cho đúng 1 mục đích: In ra báo cáo tóm tắt cuối cùng khi có kết quả thực sự (ví dụ: `[BÁO CÁO 2FA GMAIL SAU CA SÁNG]`).
   - Nếu trong nhịp quét không có máy đủ điều kiện hoặc không có hành động nào được thực thi $\rightarrow$ thoát với `sys.exit(0)` hoặc `return 0` im lặng tuyệt đối, không in bất kỳ ký tự nào ra stdout.

---

## 2. Phòng chống Báo cáo Ảo (Fake/Stubbed Success) trên Device Automation

### Sự cố điển hình (Vụ việc 2FA Google on-device 16/09/2026)
- **Hiện tượng**: Watchdog báo cáo 86/86 máy bật 2FA thành công, nhưng User nhìn màn hình S7 thấy toàn dừng ở trang "Mã dự phòng", đối soát file `gmail_clean_v2.xlsx` thì cột `2fa` trống trơn 100%.
- **Nguyên nhân gốc rễ**:
  - Script con `enable_gmail_2fa_device.py` chỉ viết dở dang đến bước mở tab "Bảo mật", in ra `Đã điều hướng vào tab Bảo mật` rồi trả về `{"status": "SUCCESS", "step": "SECURITY_NAVIGATED"}`.
  - Script cha chỉ check lỏng lẻo `if res.get("status") in ["SUCCESS", "OK"]` và cộng ngay vào `success_list`.
  - Không có bước đối soát artifact cuối cùng (Secret Key đã được tạo, OTP đã verify, Excel đã cập nhật).

### Quy tắc Verification Contract cho Device Automation
1. **SUCCESS chỉ áp dụng cho End Artifact**:
   - Thành công của một automation task phải gắn liền với kết quả sau cùng không thể đảo ngược (e.g. Secret Key hợp lệ đã được ghi vào bảng tính và kiểm tra đọc lại khớp; 2FA toggle đã ở trạng thái ON).
   - Mọi trạng thái điều hướng trung gian (đã mở app, đã vào tab Bảo mật, đã bấm nút Bắt đầu) CHỈ ĐƯỢC coi là bước chuyển tiếp (`status: "IN_PROGRESS"` hoặc `"STEP_DONE"`), TUYỆT ĐỐI KHÔNG trả `"SUCCESS"`.
2. **Fail-Closed khi flow chưa hoàn tất**:
   - Nếu kịch bản dừng lại ở bất kỳ bước nào trước khi hoàn thành mục tiêu cuối cùng (do chưa viết code, do timeout, hoặc do popup chặn), BẮT BUỘC trả về `"status": "FAILED"` hoặc `"INCOMPLETE"` kèm theo màn hình dừng hiện tại (`current_step`, `error_reason`).
   - Cấm nuốt lỗi hoặc dùng cờ giả định để đánh lừa caller.
3. **Canary Verification trước khi đưa vào Watchdog**:
   - Trước khi đưa một automation script vào cron batch nhiều máy, BẮT BUỘC chạy Canary trên 1 máy thật duy nhất.
   - Nghiệm thu bằng cách kiểm tra:
     - Màn hình thiết bị sau khi kết thúc có đúng trạng thái mong muốn không (chụp ảnh screencap nghiệm thu).
     - File dữ liệu đích (Excel, Database, JSON ledger) có dữ liệu thực tế không hay vẫn là chuỗi rỗng.
