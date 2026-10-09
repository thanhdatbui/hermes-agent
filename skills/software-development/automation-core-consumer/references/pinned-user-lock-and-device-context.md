# Pinned User Lock & DeviceContext Integration Guide (2026-09-19)

## 1. Bản Chất Vấn Đề
- Khi viết consumer, runner hoặc script ad-hoc thao tác trên farm, nếu chỉ gọi ADB trần mà không chiếm device lock:
  + Các cronjob tự động (TikTok feed runner, upload avatar, sync) sẽ quét thấy thiết bị rảnh và tự ý can thiệp, cướp foreground.
- Nếu chiếm lock thông thường (`user_authorized=False` hoặc không gắn cờ):
  + Các tiến trình khác có thể kích hoạt recovery/takeover ngầm.

## 2. Chuẩn Hóa Với `DeviceContext` (Lệnh Có Nguồn Gốc Operator / User)
Tất cả các runner, canary, hoặc script ad-hoc do Operator/User ra lệnh BẮT BUỘC dùng context manager `DeviceContext` từ `automation_core.device_lock`:

```python
from automation_core.device_lock import DeviceContext, DeviceLockNeedsUserDecision

# Tự động gắn user_authorized=True, pinned=True, ttl_seconds=3600
try:
    with DeviceContext(serial=serial, machine=str(stt), project="operator-task", user_authorized=True) as lease:
        # Thao tác độc quyền trên thiết bị
        ...
except DeviceLockNeedsUserDecision as exc:
    # Thiết bị đang bị một tiến trình khác giữ lock -> Cấm giẫm chân, bỏ qua hoặc chờ
    log.warning(f"Thiết bị đang bận: {exc}")
```

## 3. Đặc Điểm Kỹ Thuật Của Pinned Lock
- **Payload:** Tự động mang `"pinned": true`, `"user_authorized": true`, `"last_heartbeat": "<ISO>"`, `"ttl_seconds": 3600`.
- **Miễn Nhiễm Takeover Thường:** Toàn bộ background recovery scopes (`SAME_PROJECT_RECOVERY`, `FULL_SCOPE_TAKEOVER`) đều bị từ chối. Chỉ duy nhất `OPERATOR_PREEMPT` (`force_preempt=True`) mới có quyền reclaim.
- **Heartbeat:** Nếu tác vụ kéo dài, gọi `lease.heartbeat()` để làm mới timestamp sống.
- **Bảo Toàn Trần TTL 1 Giờ:**
  + `reap-dead-owner-locks.py` tôn trọng Pinned Lock trong vòng 3600s.
  + Nếu tiến trình chủ bị crash (`owner_alive is False`): Thu hồi ngay lập tức, không để zombie.
  + Nếu quá 1 giờ: Tự động thu hồi sang `quarantine` với lý do `pinned_1h_ttl` để chống deadlock qua đêm.

## 4. Quy Tắc Khi Lấy OTP Trên Farm (Multi-Account Pitfalls)
- Thiết bị farm luôn có sẵn nhiều tài khoản Google/TikTok cũ.
- Khi cần lấy OTP qua app Gmail:
  1. Bắt buộc kiểm tra tài khoản đang active trong Gmail có khớp với target email không.
  2. Nếu không khớp: Phải switch account qua avatar (`985, 138`) -> chọn đúng target email.
  3. Bắt buộc lọc người gửi (OpenAI / ChatGPT), tuyệt đối không quét regex mã 6 số mù quáng trên toàn màn hình để tránh lấy nhầm OTP của TikTok / Google đã nhận từ các ngày trước.
