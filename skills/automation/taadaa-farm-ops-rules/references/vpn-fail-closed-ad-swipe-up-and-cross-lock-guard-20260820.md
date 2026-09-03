# VPN Fail-Closed, Ad Swipe-Up, and Cross-Project Device Lock Guard (20/08/2026)

## 1. QUY TẮC SỐNG CÒN: MẤT VPN / PROXY = DỪNG HẲN MÁY, CẤM LƯỚT TIẾP
- **Hiện tượng**: App ViChanger báo kết nối hoặc `tun0` UP trong `ifconfig`, nhưng cổng proxy (ví dụ port 10004) bị ngắt kết nối / từ chối (`target machine actively refused it`), hoặc lệnh broadcast `vn.vichanger.app.GET_IP` thất bại / không lấy được IP hợp lệ.
- **Quy tắc bắt buộc**:
  - Dù `tun0` có UP, nếu không xác thực được live proxy IP thật ra ngoài $\rightarrow$ **FAIL-CLOSED NGAY LẬP TỨC**.
  - **TUYỆT ĐỐI CẤM** gửi lệnh ADB mở TikTok, lướt tiếp hoặc auto-resume trên các máy mất VPN để tránh lộ IP mạng gốc của farm làm chết dàn nick.
  - Tầng `automation_core/preflight.py` (`check_android_vpn`) bắt buộc return `allowed=False` nếu `ip_verified=False`.
  - AI Auto-Recovery (`agent.py`) bắt buộc kiểm tra lỗi VPN/Proxy ở ngay **Bước 0** và DỪNG HẲN máy, không thực thi bất kỳ lệnh ADB nào.

---

## 2. QUY TẮC QUẢNG CÁO / SPONSORED ADS: VUỐT LÊN QUA LUÔN
- Khi gặp các video/màn hình quảng cáo TikTok (Sponsored brand ad, CTA mua ngay/tìm hiểu thêm, popup khảo sát quảng cáo):
  - **Hành động chính**: **VUỐT LÊN (Swipe Up)** như lướt video bình thường để chuyển sang video tiếp theo.
  - Nút "Đóng / Hủy / Bỏ qua" chỉ đóng vai trò là **fallback phụ** khi vuốt không qua được.

---

## 3. QUY TẮC VUỐT RETRY 2 LẦN CỨU KẸT (SWIPE UP RETRY)
- Khi đang lướt nuôi mà gặp màn hình lạ, không xác định hoặc script báo lỗi không có trong allowlist (trừ các màn hình nhạy cảm như Login, OTP, Captcha, Verification):
  - Hệ thống phải tự động thực hiện **VUỐT LÊN tối đa 2 lần retry** để thử thoát màn hình lạ và tiếp tục phiên nuôi trước khi dừng phiên / báo alert.

---

## 4. BẢO VỆ CROSS-PROJECT DEVICE LOCK (BOTMAIL / REG ACC / 2FA...)
- Khi một máy đang bị tiến trình khác kiểm soát (ví dụ Botmail / Hotmail login / Reg Gmail / Reg TikTok / Add 2FA) có file lock active trong `~/.codex/device-locks/`:
  - AI Auto-Recovery và Feed Runner **TUYỆT ĐỐI KHÔNG CAN THIỆP**, dừng ngay lập tức để tránh xung đột tài nguyên và làm hỏng luồng của tiến trình đang chạy.

---

## 5. PHÂN BỔ CA NUÔI & CƠ CHẾ CATCH-UP BUỔI TỐI
- **Ngày chẵn (Lane A)**:
  - Ca 1 (06:00 - 11:00): Row 2 (Acc chính).
  - Ca 2 (12:00 - 17:00): Row 4 (Warm acc).
  - Ca 3 (18:00 - 23:30): Row 2 (Acc chính).
- **Cơ chế Catch-up 18:00**: Mốc 18:00 nếu thấy máy chạy Row 4 là do cơ chế grace period tự động bù nốt phiên bị trễ của ca trưa cho các máy chưa hoàn thành trước khi chuyển giao 100% sang ca tối (Row 2).
