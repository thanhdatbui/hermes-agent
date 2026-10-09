# Quy tắc bất khả xâm phạm về Device Lock & Bảo vệ tiến trình Farm (Hard Guard)

## 1. Nguyên tắc cốt tử: Ownership & Mutual Exclusion
- Mọi thiết bị trên Farm khi đang bị một tiến trình (script add 2FA, nuôi acc, feed session, register...) kiểm soát thì **TUYỆT ĐỐI CẤM** tiến trình khác hoặc Coordinator nhảy vào can thiệp.
- **Chỉ duy nhất tiến trình (PID) tạo ra lock** mới có quyền giải phóng (`release`) lock của chính nó.
- **CẤM TUYỆT ĐỐI** Coordinator hoặc Worker tự ý gọi `release_machine_reg_reservation`, bẻ lock, xóa file lock hoặc override cờ lock khi tiến trình chủ sở hữu còn sống (`owner_process_alive() == True`).

## 2. Cấm tự tiện force-stop & đưa về HOME
- Chỉ được phép `force-stop` hoặc bấm `HOME` trên máy mà chính tiến trình đó **ĐÃ ACQUIRE THÀNH CÔNG `device_lock`** (hợp lệ về quyền sở hữu).
- Tuyệt đối **CẤM** tự ý suy diễn màn hình lạ là "bị kẹt / treo" rồi vội vàng `force-stop` app và đưa máy về Home, làm giết chết các flow đang chạy hợp lệ (như flow Add 2FA, nhập OTP, checkpoint).
- Thao tác dọn dẹp máy bị kẹt quá hạn (>1h TTL) **ĐÃ CÓ CRON WATCHDOG RIÊNG (`reap-dead-owner-locks.py`)** đảm nhiệm tự động, Agent tuyệt đối không được tự ý can thiệp dọn dẹp ngoài luồng.

## 3. Bắt buộc Preflight Device Lock trước mọi task chạy tay
- Mọi script đơn lẻ (như `social_reg_v1.py`, batch reg, audit) **BẮT BUỘC** phải kế thừa kiểm tra lock toàn diện từ `automation_core.device_lock`.
- Cấm phụ thuộc vào biến môi trường lỏng lẻo (`DEVICE_LOCK_ENABLED`).
- Nếu máy đang có `machine_<N>.lock.json` của tiến trình khác còn sống -> **BẮT BUỘC FAIL-FAST**, Safe-Skip máy đó ngay lập tức. CẤM gửi bất kỳ lệnh ADB nào (`am start`, `am force-stop`, `input tap`, `input keyevent`).
