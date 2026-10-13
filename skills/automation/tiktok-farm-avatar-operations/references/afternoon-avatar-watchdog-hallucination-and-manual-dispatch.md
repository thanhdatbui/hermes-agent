# Bẫy Ảo Giác Watchdog Upload Avatar Buổi Chiều & Kỷ Luật Kích Hoạt Đơn Máy

## 1. Triệu chứng & Sự cố thực tế (13/10/2026)
- Coordinator hỗ trợ user chốt ảnh avatar mới cho Máy 67 (Tik 6) lúc 12:20.
- Do Farm đang chạy Ca 2 nuôi feed (Row 8), Coordinator đưa ra 2 lựa chọn và khuyên chọn: *"1. Chạy tự động: Ngay khi ca nuôi hoàn tất, watchdog tự động bốc hàng đợi PENDING để vào app up avatar"*.
- User chọn "1". Coordinator ghi DB `avatar_replace_queue` sang `PENDING` và Excel sang `PENDING` rồi dừng lại chờ đợi.
- **Hậu quả**: Suốt 5 tiếng từ 12:20 đến 17:40, hệ thống hoàn toàn im lặng, không có bất kỳ lượt upload hay báo cáo nào. User quay lại chất vấn gay gắt.

## 2. Nguyên nhân cốt lõi: Ảo giác cơ chế tự động (Hallucinated Watchdog)
- **Kiến trúc lịch Farm Taadaa**:
  - Toàn bộ các script tự động upload avatar (`post_evening_avatar_watchdog.py`, `avatar_post_feed_watchdog.py`) **CHỈ HOẠT ĐỘNG BAN ĐÊM**:
    * `is_post_evening_window`: Khung giờ 20:15 - 23:45 (sau Ca tối) và 03:15 - 05:45 (sau Ca đêm).
    * `avatar_post_feed_watchdog`: Khung giờ 22:30 - 00:45.
  - **HOÀN TOÀN KHÔNG CÓ** watchdog nào chạy upload avatar tự động vào buổi chiều giữa Ca 2 (trưa) và Ca 3 (chiều/tối).
  - Khi Coordinator hứa hẹn *"watchdog sẽ tự động bốc sau ca trưa"*, đó là suy diễn bịa đặt không có thực trên hạ tầng.

## 3. Quy chuẩn điều phối bắt buộc (Invariant)
1. **CẤM TUYỆT ĐỐI** Coordinator hứa hẹn với User rằng avatar sẽ được tự động upload vào buổi chiều sau Ca trưa.
2. **Quy trình xử lý khi chốt avatar giữa ngày**:
   - Bước 1: Đồng bộ file avatar chuẩn vào các thư mục `D:/video goc/<F_src>`, `D:/video goc/<F_out>`, và `D:/TIKTOK-videonuoinick/<F_out>`.
   - Bước 2: Kiểm tra lock máy bằng `inspect_machine.py <M>` và thư mục `~/.codex/device-locks`.
   - Bước 3: 
     * Nếu máy đang bận chạy ca nuôi: Báo rõ cho User máy đang trong ca nuôi (kèm PID và giờ dự kiến xong). Thiết lập lệnh chờ hoặc thông báo rõ sẽ chạy ngay khi nhả lock.
     * Ngay khi máy rảnh (không kẹt lock): **BẮT BUỘC CHỦ ĐỘNG KÍCH HOẠT RUNNER ĐƠN MÁY NGAY LẬP TỨC**:
       ```powershell
       echo RUN | powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1' -Tik <Tik> -ForceAvatarMachineList '<M>' -MaxParallel 1 -HostConfigPath 'D:\Taadaa\machine-config\kibe.yaml'
       ```
   - Bước 4: Chờ runner exit 0 (`verified=True`), soi mắt snapshot kết quả (`avatar-uploaded-confirmed.png`) qua `browser_vision`, sau đó mới cập nhật SQLite `DONE` và Excel `OK` rồi gửi báo cáo kèm ảnh cho User.
