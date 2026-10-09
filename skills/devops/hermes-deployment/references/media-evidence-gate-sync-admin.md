# Đồng Bộ Cấu Hình MEDIA Evidence Gate Từ Kibe Sang Admin

Ngày ghi nhận: 12/09/2026.
Tác nhân: Khóa cứng quy tắc bắt buộc gửi ảnh nghiệm thu `MEDIA:<path>` trên bot Admin.

---

## 1. MỤC TIÊU ĐỒNG BỘ
- Đảm bảo bot Admin (@taadaa_admin_hermes_bot) nhận đúng cấu hình `system_prompt` mới, loại bỏ hoàn toàn kẽ hở "khi cần" hay "khi có yêu cầu" để không bao giờ bỏ quên ảnh kết quả sau các ca chạy automation trên dàn máy 200+.
- Bảo toàn 100% `TELEGRAM_BOT_TOKEN` riêng biệt của bot Admin (không bị ghi đè gây xung đột getUpdates).

---

## 2. LỆNH 1-CLICK CHẠY TRÊN ADMIN
Chỉ cần gửi lệnh này vào khung chat của Bot Admin trên Telegram (hoặc chạy trong PowerShell trên máy Admin):

```powershell
git -C D:\Taadaa\Hermes pull --rebase fork main && powershell -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Hermes\deploy\sync-from-kibe.ps1
```

---

## 3. CƠ CHẾ TỰ ĐỘNG CỦA SCRIPT
1. `git pull --rebase fork main`: Kéo các commit mới nhất từ repository `D:\Taadaa\Hermes` (chứa `deploy/hermes-home/config.yaml` đã cập nhật).
2. `sync-from-kibe.ps1`:
   - Copy `deploy/hermes-home/config.yaml` sang `%LOCALAPPDATA%\hermes\config.yaml` của Admin.
   - Tự động thay thế `127.0.0.1` thành IP LAN của Kibe (`192.168.110.123`) để trỏ về OmniRoute (:20129) và 9Router (:20128).
   - Đồng bộ toàn bộ Skills từ repo vào `%LOCALAPPDATA%\hermes\skills\`.
   - Giữ nguyên `TELEGRAM_BOT_TOKEN` trong file `.env` của Admin.
   - Kích hoạt tiến trình ngầm `restart-when-idle.ps1` để tự động khởi động lại Gateway khi phiên làm việc rảnh rỗi.
