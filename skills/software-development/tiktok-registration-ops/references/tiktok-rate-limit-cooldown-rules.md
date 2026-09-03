# Quy tắc Cooldown 2 ngày khi dính Rate Limit TikTok (2026-08-26)

## 1. Dấu hiệu nhận diện lỗi Rate Limit
- Màn hình popup hoặc Toast: *"Bạn truy cập dịch vụ của chúng tôi quá thường xuyên"* / *"Too many attempts"* / *"Too many requests"*.
- Thường xuất hiện sau các bước submit email, verify OTP hoặc submit DOB khi TikTok gắn cờ tần suất thao tác trên thiết bị/IP.

## 2. Quy tắc xử lý bắt buộc (User Rule 2026-08-26)
- **TUYỆT ĐỐI CẤM**: Không được cố bấm thử lại hoặc reg lại máy đó ngay lập tức (sẽ làm TikTok kéo dài thời gian phạt hoặc block vĩnh viễn thiết bị/IP).
- **Thời gian Cooldown**: Cho máy nghỉ **đúng 2 ngày (48 giờ)**.
- **Lưu trữ trạng thái**:
  - Ghi nhận vào file theo dõi: `D:\Taadaa\runtime\kibe\device_cooldowns.json`.
  - Cấu trúc:
    ```json
    {
      "<machine_id>": {
        "reason": "TOO_MANY_ATTEMPTS",
        "detail": "Bạn truy cập dịch vụ của chúng tôi quá thường xuyên",
        "blocked_at": "2026-08-26T08:05:00",
        "cooldown_days": 2,
        "cooldown_until": "2026-08-28T08:05:00"
      }
    }
    ```
- **Hành vi của Script chạy tự động (`_detect_clean.py`)**:
  - Khi quét tìm target để chạy batch, `_detect_clean.py` tự động đọc `device_cooldowns.json`.
  - Nếu `now < cooldown_until`: Tự động **BỎ QUA (SKIP)** máy đó ra khỏi danh sách chạy, in log: `STT=<N>: COOLDOWN_ACTIVE (until <time>)`.
  - Sau khi qua đủ 48 giờ: Tự động gỡ bỏ trạng thái cooldown để máy tiếp tục tham gia ca reg bình thường.
