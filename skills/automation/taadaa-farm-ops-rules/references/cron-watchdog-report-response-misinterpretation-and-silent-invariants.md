# Kỷ luật Xử lý Báo cáo Cron & Nguyên tắc Silent Watchdog Bất biến

## 1. Cấm Tự ý Xóa / Tạm dừng Cron khi User Forward Báo cáo

### Bối cảnh & Lỗi nguy hiểm
Khi một Cronjob (hoặc Silent Watchdog) gửi báo cáo ra Telegram dạng:
```text
Cronjob Response: <job_name> (job_id: <id>)
-------------
[BÁO CÁO ...]
- Thời gian: 11:00 -> 11:00 (0.0 phút)
- Tổng máy đủ điều kiện: 0
- Success (S): []
- Fail (F): []
```
Người dùng thường reply hoặc forward lại tin nhắn này với câu hỏi cộc lốc hoặc thắc mắc:
- *"Clmm t gửi cái báo cáo của add gmail 2fa mà"*
- *"Sao 0 máy?"*
- *"Lí do lỗi"*

### Sai lầm chết người của Agent
Agent vội vàng phỏng đoán: *"Chắc user đang bực vì bot spam tin nhắn"* -> tự ý gọi `cronjob(action='remove', job_id=...)` hoặc `cronjob(action='pause')` để xóa/tắt job của hệ thống!
Hậu quả:
- User không hề yêu cầu xóa cron, user gửi báo cáo để hỏi **tại sao lại ra 0 máy** hoặc **tại sao lại có kết quả bất thường**.
- Xóa cron làm đứt gãy toàn bộ chuỗi vận hành tự động của farm (ví dụ: mất watchdog 2FA, mất sync, mất watchdog dọn lock).

### Quy tắc Điều phối Bắt buộc
1. **CHỈ XÓA/PAUSE KHI CÓ MỆNH LỆNH RÕ RÀNG**:
   - CHỈ ĐƯỢC PHÉP gọi `action='remove'` hoặc `action='pause'` khi người dùng phát lệnh dứt khoát bằng văn bản: *"xóa cron X"*, *"tắt job Y"*, *"dừng reminder Z"*.
   - Mọi trường hợp user forward tin nhắn báo cáo, than phiền kết quả, hoặc chửi lỗi: BẮT BUỘC hiểu là **Yêu cầu đối soát hiện trường và giải thích nguyên nhân kỹ thuật**, CẤM đụng vào lifecycle của cron.
2. **KHI LỠ XÓA NHẦM**:
   - Phải nhận lỗi thẳng thắn, không biện minh vòng vo.
   - Khôi phục lại ngay lập tức bằng `cronjob(action='create')` với đúng tham số, lịch chạy, script và deliver channel.

---

## 2. Kỷ luật Thiết kế Silent Watchdog (`no_agent: True`)

### Bản chất Cơ chế Delivery
Trong Hermes cronjob với `no_agent: True`:
- Scheduler chạy trực tiếp script và bắt `stdout` để gửi vào channel chỉ định (`deliver`).
- **`stdout rỗng` (zero stdout)** = **SILENT** (Scheduler hoàn toàn im lặng, không gửi bất kỳ tin nhắn nào).
- **`stdout có nội dung`** = **DELIVERY** (Scheduler tự động chuyển tiếp toàn bộ chuỗi stdout lên Telegram).

### Pitfall: In Báo cáo Rỗng khi không có việc
Trong một số script như `post_morning_gmail_2fa_watchdog.py`:
```python
# LỖI: Khi online_devices = [] hoặc len(eligible_devices) == 0:
report = f"""
[BÁO CÁO 2FA GMAIL SAU CA SÁNG]
- Thời gian: {start_time.strftime('%H:%M')} -> {end_time.strftime('%H:%M')} ({duration_min} phút)
- Tổng máy đủ điều kiện: {len(eligible_devices)}
- Success (S): {success_list}
- Fail (F): {fail_list}
"""
print(report)  # <- PHÁ VỠ NGUYÊN TẮC SILENT WATCHDOG!
```
Hậu quả: Mỗi 5 phút watchdog thức dậy, thấy không có máy nào đủ điều kiện (hoặc do ADB nghẽn tạm thời trả về `[]`), script lại `print` bản tin trên -> Hermes scheduler chuyển tiếp vào group mỗi 5 phút một lần thành spam rác!

### Invariant Bắt buộc
1. **Silent on Zero Work**:
   ```python
   if not eligible_devices or len(eligible_devices) == 0:
       # Không có việc cần làm hoặc dependency tạm thời trống -> IM LẶNG TUYỆT ĐỐI
       return 0
   ```
   Chỉ in báo cáo ra stdout khi **ĐÃ CÓ ÍT NHẤT 1 THIẾT BỊ HOẶC HẠNG MỤC ĐƯỢC XỬ LÝ THỰC SỰ** (`len(success_list) + len(fail_list) > 0`).
2. **Đường dẫn Canonical ADB**:
   - Luôn dùng đường dẫn ADB chuẩn: `C:/Users/Kibe/.GemPhoneFarm/app/adb-tool/adb.exe`.
   - Cấm gọi lệnh `adb` trần không có path đầy đủ, vì trong môi trường sanitized subprocess của Hermes cron, `PATH` có thể bị trỏ sai binary ADB phụ của phần mềm khác (như Xiaowei) hoặc mất PATH.
