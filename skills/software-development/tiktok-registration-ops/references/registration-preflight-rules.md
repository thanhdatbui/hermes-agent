# Preflight & Filter Rules for TikTok Registration

Khi user yêu cầu kiểm tra hoặc chạy batch reg TikTok:
1. **Target Mail Eligibility:** Sử dụng `_detect_clean.py` để quét các máy có mail nguồn chưa đăng ký TikTok.
2. **VPN Gate:** Bắt buộc kiểm tra VPN qua broadcast `vn.vichanger.app.GET_IP` (`result=200`, data là IP hợp lệ). Tuyệt đối không reg trên máy chưa kết nối proxy/VPN (`result=0` hoặc direct IP).
3. **Cron Schedule Preflight:** Chỉ chọn các máy không vướng ca nuôi acc hiện tại và cách ca tiếp theo tối thiểu 60 phút (trừ khi user chỉ định chạy ngay và chấp nhận lock).
4. **Device Lock:** Khi user yêu cầu "lock máy lại chạy", kích hoạt `DEVICE_LOCK_ENABLED=1` để acquire device lock an toàn.
