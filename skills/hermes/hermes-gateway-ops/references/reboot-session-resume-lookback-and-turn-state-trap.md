# Sự Cố Im Lặng Khi Reboot: Bẫy Lookback_Minutes và Bẫy Turn-Level State

## Bối Cảnh Thực Tế (2026-10-20)
Ca reboot định kỳ lúc 11:20:00 (chạy bởi Windows Task `Taadaa_Farm_Daily_Reboot_1135` gọi `farm_preflight_daily_reset.py`).
Sau khi máy chủ Kibe PC khởi động lại, topic Telegram của user bị im lặng hoàn toàn, bot không thức dậy làm tiếp task đang dang dở, khiến user bức xúc ("nãy reboot xong mày treo đéo tự làm tiếp session à?").

## Nguyên Nhân Gốc Rễ Đã Điều Tra (2 Tầng)

### 1. Bẫy Thời Gian Lọc `lookback_minutes = 20`
* Trong `farm_preflight_daily_reset.py`:
  ```python
  preserve_in_flight_sessions(lookback_minutes=20)
  ```
* Ca reboot diễn ra lúc **11:20:01**. Ngưỡng lọc 20 phút trước đó là **11:00:01**.
* Tin nhắn cuối cùng trong session trước reboot là lúc **10:49:50** (cách thời điểm reboot **30.2 phút**).
* Do `30.2 phút > 20 phút`, hàm quét bỏ qua session ngay lập tức, không kiểm tra nội dung và không đánh dấu `resume_pending=True`.

### 2. Bẫy Logic Turn-Level State (`last_role == 'assistant'`)
* Trong `farm_preflight_daily_reset.py` và `gateway/session.py`:
  ```python
  in_flight = last_role in ("user", "tool") or (
      last_role == "assistant" and _has_tool_calls(tool_calls)
  )
  if not in_flight:
      log_message(f"[RESUME] Bo qua {key}: tin cuoi la '{last_role}' (da tra loi xong).")
  ```
* Nếu lượt cuối cùng là Agent đã trả lời xong và đang đặt câu hỏi ngược lại cho User (ví dụ: *"sếp muốn làm tiếp hay chốt phiên?"*), Gateway coi phiên này là **IDLE / đã hoàn tất turn**.
* Người dùng vẫn coi task là "đang dở" (vì task tổng thể chưa chốt phiên), nhưng Gateway chỉ nhìn vào `last_role`. Khi `last_role == 'assistant'` không có tool call, Gateway bỏ qua để tránh spam tin nhắn khi khởi động lại.

## Quy Tắc Phòng Ngừa & Giải Pháp Khắc Phục

1. **Nâng `lookback_minutes` lên 60 phút**:
   - `preserve_in_flight_sessions(lookback_minutes=60)` trong `farm_preflight_daily_reset.py` để bao quát trọn vẹn toàn bộ phiên thảo luận trong vòng 1 tiếng trước chu kỳ reboot (05:20, 11:20, 17:20).
2. **Cơ chế PING chủ động trạng thái Awaiting Decision**:
   - Khi Gateway boot lại, nếu session có hoạt động gần nhất trong 60 phút nhưng đang chờ phản hồi từ user (tin cuối là `assistant` dạng câu hỏi/đề xuất), Gateway cần gửi 1 ping ngắn:
     `"🤖 Host vừa hoàn tất chu kỳ reboot định kỳ. Em đã nạp lại phiên, trước đó chúng ta đang dừng ở bước: [...]. Sếp muốn triển khai tiếp bước nào ạ?"`
   - Điều này tránh việc người dùng nghĩ bot bị treo hoặc đứt kết nối.
