# Quy Chuẩn Quản Trị Repo GPM Auto & Tracker Cooldown Tránh Gọi Nhầm

## 1. Phân Định Mã Nguồn & SSOT Repo GPM
- **Quy tắc bất biến:** Mọi script, tool, cấu hình liên quan đến GPMLogin (profile lifecycle, batch login, 2FA TOTP, OAuth qua GPM) BẮT BUỘC lưu trữ tập trung tại:
  `D:\Taadaa\GPM auto` (GitHub: `thanhdatbui/gpm-auto`).
- **CẤM:** Tuyệt đối không commit hay ném các tool điều khiển GPM sang `AI-Tools` hoặc các consumer repo khác. `AI-Tools` chỉ quản lý API OmniRoute/9Router backend.

## 2. Quản Trị Trạng Thái & Bộ Lọc Tự Động Chặn Gọi Nhầm (Cooldown Tracker)
Khi chạy batch nạp OAuth / GPM hàng loạt, Google kích hoạt nhiều cơ chế bảo vệ khác nhau. Để chống tình trạng worker lượt sau gọi đè làm cháy IP hoặc hỏng trust score của tài khoản:

### Cơ cấu file `config/oauth_pipeline_status.json`:
```json
{
  "updated_at": "2026-09-06T07:15:00",
  "omniroute_success": {
    "email@gmail.com": {"machine": 43, "port": 5105, "connection_id": "...", "status": "HTTP_200_OK"}
  },
  "cooldown_7days": {
    "email@gmail.com": {
      "machine": 20, "port": 5124,
      "reason": "signin/rejected?rrk=77 (Google 2SV sensitive cooldown 7 days)",
      "date_detected": "2026-09-06",
      "retry_after": "2026-09-13T00:00:00"
    }
  },
  "ip_cooling_recaptcha": {
    "email@gmail.com": {
      "machine": 10, "port": 5112,
      "reason": "Google reCAPTCHA image challenge, pause to cool down IP",
      "retry_after": "2026-09-07T00:00:00"
    }
  },
  "excluded_khoalee": ["khoalemagic@gmail.com", "khoaleemagic@gmail.com", "..."],
  "wrong_password_or_checkpoint": {"email@gmail.com": "WRONG_PASSWORD (M36)"}
}
```

### 3 Tầng Bảo Vệ Bắt Buộc Trong Mọi Batch Script:
1. **Kiểm tra trước khi mở Chromium/Browser:**
   ```python
   if email in status_data.get("omniroute_success", {}):
       return {"status": "ALREADY_SUCCESS"}

   if email in status_data.get("cooldown_7days", {}):
       item = status_data["cooldown_7days"][email]
       if datetime.now() < datetime.fromisoformat(item["retry_after"]):
           logger.warning(f"⏸️ Bỏ qua {email}: ĐANG CHỜ COOLDOWN 7 NGÀY (đến {item['retry_after']})!")
           return {"status": "SKIPPED_COOLDOWN_7DAYS"}

   if "khoale" in recovery.lower() or "khoale" in email.lower():
       logger.warning(f"🚫 Bỏ qua {email}: TÀI KHOẢN DÍNH KHOALEMAGIC (Loại trừ 100%)!")
       return {"status": "SKIPPED_KHOALEE"}

   if email in status_data.get("ip_cooling_recaptcha", {}):
       item = status_data["ip_cooling_recaptcha"][email]
       if datetime.now() < datetime.fromisoformat(item["retry_after"]):
           return {"status": "SKIPPED_IP_COOLING"}
   ```
2. **Đồng bộ song song vào Excel Master (`master_gmail_manager.xlsx`):**
   - Cột 14 (`Ghi Chú`): Ghi rõ `COOLDOWN_7DAYS (rrk=77 - Chờ sau YYYY-MM-DD)` hoặc `PAUSED_RECAPTCHA`, `OMNIROUTE_SUCCESS`.
   - Cột 15 (`Cập Nhật`): Cập nhật timestamp hiện tại.
3. **Tracking trong Git:**
   - Thêm `!config/oauth_pipeline_status.json` vào `.gitignore` để trạng thái này được push lên GitHub `gpm-auto`, giúp các máy/worker khác dùng chung dữ liệu.

## 3. Quy Chuẩn ADB Device Lock S7 Google Prompt 2 Giai Đoạn:
- **Nguyên tắc `finally` bắt buộc:**
  ```python
  with acquire_device_lock(machine=str(mid), serial=serial, project="gpm-login", bypass_proxy_readiness=True, force_preempt=True):
      try:
          # Thao tác thức máy (keyevent 224 + 82), duyệt prompt, chọn PIN
          pass
      finally:
          try:
              subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "3"], timeout=5)
          except Exception:
              pass
  ```
- **Không bao giờ gửi HOME ở giữa:** Sau khi bấm nút "Có"/"Vâng, đúng là tôi", BẮT BUỘC giữ màn hình chờ xuất hiện 3 số PIN, tap đúng số PIN khớp `target_pin` rồi mới gửi HOME.
