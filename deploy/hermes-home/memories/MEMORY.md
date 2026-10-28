Guard_media_vision_gate chặn DIRTY_AVATAR_EVIDENCE, cấm leak DEGRADED ra chat; kiểm tra contradiction phổ quát cho mọi loại ảnh để chống AI bịa đặt thành công khi ảnh hiển thị lỗi.
§
Nạp ChatGPT-Web: trần 2 acc/IP + proxy_assignments; worker <= 5; Hotmail là mail mua sẵn (mail kp smvmail.com/fviainboxes có public API đọc OTP, cấm than thở thiếu mail kp); pass ChatGPT random độc nhất lưu Excel; script reg cấm exit 0 khi fail; lọc GPM GroupId!=0; pre-validate Graph token; cấm base64.
§
Watchdog đối soát TikTok Web: Chu kỳ farm 3 ngày/acc (1 ca/buổi gồm 2 phiên cách nhau >= 120m); Quota max cap 40 fl/ngày; used>0 streak luôn=1 (cooldown 24h xả sạch trước vòng sau), chỉ used=0 (phát đầu fail) mới tăng streak; không có nhả ngược; 3 quy trình Feed-Follow-Upload độc lập; Quota [cap-2, cap], bóp trần = last_failed - 2; verify profile pull-to-refresh bắt nhả thật (sleep_after 3.5s + polling 2 nhịp).
§
Tool 2FA và cron xen ca: JIT lock từng máy (cấm bulk pre-reserve); freeze_targets bọc retry 5 nhịp backoff + dọn lock mồ côi ~$*.xlsx né xung đột cron sync 5m; Batch 2FA Admin qua SSH bắt buộc --adb-path r"C:\Program Files (x86)\xiaowei\tools\adb.exe"; sau sửa 2FA bắt buộc chạy sync_2fa_to_admin.py.
§
GuardGate (D:/Taadaa/tools/guardgate) là Protection Regression Gate cơ giới hóa cho code diff repo (Closeout Step 2.5); infra_regression_gate.py chỉ kiểm tra riêng 4 file config hạ tầng Hermes/OmniRoute.
§
OpenWrt R3G (MT7621/DSA): Cổng xanh br-lan nối PC; Access Concentrator / Service Name để TRỐNG. Cắm line tốt mà PADO timeout là do switch/VLAN/cổng nội bộ, cấm đổ thừa MAC/ISP/hạ tầng. Tắt IPTV trên profile WAN H196A. Nhắn tin kỹ thuật dẫn ICMP !C và account ID.
§
Cooldown pool OmniRoute: Dùng rate_limited_until dạng ISO UTC (+30m), giữ nguyên is_active=1 và 100% models trong combo; cấm set is_active=0 hoặc xóa entry làm cụt pool; cron chatgpt-web-pool-healer-watchdog sẽ tự động quét hồi sinh.