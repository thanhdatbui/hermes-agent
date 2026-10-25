Cronjob on-demand/helper kích hoạt batch ngầm BẮT BUỘC cờ deliver='local' để chống Hermes scheduler tự động đổ stdout (telemetry/log) spam vào Telegram chat.
§
Khi TikTok Switcher thiếu account (ACCOUNT_MISSING), BẮT BUỘC kích hoạt auto-login / Thêm tài khoản (recovery_handler=tiktok_login); CẤM phân biệt máy trắng acc hay viện cớ an toàn / lệch nhịp farm để dừng máy fail-closed.
§
Khi nhận cảnh báo pool degraded/error, cấm chỉ báo cáo cô lập is_active=0; bắt buộc test trực tiếp endpoint, fix proxy/config để cứu và reactivate acc nếu token còn sống.
§
Khi pool OmniRoute (ChatGPT-Web/Codex) lỗi: BẮT BUỘC đối soát proxy_registry (credentials port) và test trực tiếp /api/providers/{cid}/test trước khi kết luận; token còn sống phải bật is_active=1 ngay thay vì chỉ thụ động cô lập.