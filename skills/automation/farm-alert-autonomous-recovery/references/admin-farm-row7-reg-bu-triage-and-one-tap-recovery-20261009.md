# Chi Tiết Điều Tra & Phục Hồi Reg Bù Row 7 Farm Admin (Máy 255, 266, 267) - 2026-10-09

## 1. Hiện Trường Lỗi & Nguyên Nhân Gốc Rễ
1. **Máy 255 (ADB offline / device not found)**:
   - Serial `9885e649474f315532` mất kết nối vật lý trên host Admin (`192.168.110.119`).
   - PnP Device status: `CM_PROB_PHANTOM`, `Present: False`.
   - Kết luận: Lỏng cáp USB hoặc sập nguồn phần cứng tại rack. Khóa trạng thái **L3 BLOCKED** theo Invariant Farm Safety.
2. **Máy 267 (OTP không về hòm thư Graph API)**:
   - TikTok báo gửi OTP tới `barrettmyrnajames1685@hotmail.com` và đếm lùi trên UI.
   - Kiểm tra trực tiếp Graph API: Token LIVE (HTTP 200) nhưng hòm thư chỉ có 3 thư cũ từ 30/09/2026, TikTok không hề gửi thư mới.
   - Nguyên nhân: Cơ chế "Silent Drop" của TikTok với email này (từng bị ngày 30/09).
   - Giải pháp: Ghi nhận `skip_otp_timeout` vào `gmail_clean_v2.xlsx`, đưa vào `registered_emails_blacklist.json`, chuyển sang mail dự phòng `tracyeta04062000@hotmail.com` -> Reg thành công `@anhloan2000` (Row 7 / Slot 7).
3. **Máy 266 (Lỗi mở account dropdown `[03_dropdown]` & văng phiên)**:
   - Trên Máy 266 có 2 nick cũ: `bongbong02892` và `letam2502`.
   - Cả 2 nick đều bị hết hạn token/văng phiên và chuyển vào danh sách One-tap Login (*"Chào mừng bạn trở lại"*).
   - Khi ở trạng thái này, header Profile chỉ là view tĩnh rỗng, Account Switcher hoàn toàn bị liệt, không bung ra khi tap vào tên hoặc sticky bar.
   - Thao tác phục hồi: Từ Profile đăng xuất an toàn -> mở One-tap Login -> chạm trực tiếp từng nick để kích hoạt lại token (zero OTP / zero password). Cả 2 nick đều active thành công 100%.

## 2. Kỹ Thuật Vá Code O(1) & Tránh Bẫy Cụm Admin
1. **Bổ sung Admin Target Inventory Fallback (`tiktok_login_v1.py`)**:
   - `resolve_device(stt)` nguyên bản chỉ tra cứu cứng `ACCOUNTS` (chỉ gồm máy 1–80 Kibe). Khi chạy máy cụm Admin (201–280) bị crash `RuntimeError: Khong co STT trong ACCOUNTS`.
   - Sửa O(1): Fallback sang `load_machine_devices(TARGET_INVENTORY_WORKBOOK)` (`taikhoan_run_safe.xlsx`) để lấy serial chuẩn cho cụm Admin.
2. **Bắt buộc cấu hình socket ADB Admin**:
   - Khi chạy CLI trên cụm Admin từ xa, bắt buộc truyền:
     ```bash
     ADB_SERVER_SOCKET="tcp:192.168.110.119:5037" TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml" python -u D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <stt> ...
     ```
   - Tránh việc ADB client rơi về `localhost:5037` gây timeout và kích hoạt `VPN GATE BLOCKED: device is offline or ADB/USB disconnected`.
