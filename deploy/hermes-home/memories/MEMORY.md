Cronjob batch ngầm đặt deliver='local' chống spam stdout; Watchdog có deliver='local' BẮT BUỘC tự dispatch Telegram (cấm chỉ print). Hàm nạp token BẮT BUỘC tự đọc trực tiếp từ hermes/.env chống rớt dependency/import automation_core.
§
Khi TikTok Switcher thiếu account (ACCOUNT_MISSING), BẮT BUỘC kích hoạt auto-login / Thêm tài khoản (recovery_handler=tiktok_login); CẤM phân biệt máy trắng acc hay viện cớ an toàn / lệch nhịp farm để dừng máy fail-closed.
§
Khi pool OmniRoute (ChatGPT-Web/Codex) lỗi: BẮT BUỘC đối soát proxy_registry và test trực tiếp /api/providers/{cid}/test trước khi kết luận; token còn sống phải bật is_active=1 ngay. Acc ChatGPT reg xong dùng ngay (chỉ ngâm acc mail, cấm ngâm ChatGPT); mỗi proxy gán tối thiểu 2 acc kèm proxy_assignments.
§
Watchdog đối soát TikTok Web (SQLite snapshots) BẮT BUỘC đối chiếu theo Account ID / Username thay vì Row máy; runner khi gặp timeout BẮT BUỘC salvage follow từ state file thay vì gán 0.
§
Tool 2FA và cron xen ca chạy cả ngày BẮT BUỘC dùng Just-In-Time (JIT) lock từng máy (cấm bulk pre-reserve giữ lock hàng loạt trong queue) và bọc predicate né khung giờ reboot/đệm trước ca cron.
§
Tài khoản Gmail chuẩn clean_v2 đã tắt Google Prompt hoàn toàn chỉ dùng 2FA TOTP: login GPM 100% trên PC qua pyotp, không cần ADB hay máy S7; cấm chặn nhầm acc farm có recovery khoaleemagic khi đã có totp_secret.
§
Cron watchdog chạy batch (2FA, Gmail reg) BẮT BUỘC ghi nhận run_date độc lập với status success/fail; hàm already_ran cấm bọc điều kiện is_success để chống vòng lặp re-run spam Telegram khi có máy lỗi.
§
Watchdog & Cron report toàn farm tuân thủ chuẩn: vi phạm mới bắn ra, không vi phạm thì im lặng; riêng 09:00 sáng VN (02:00 UTC) phát 1 nhịp Heartbeat 24h xác nhận hệ thống sống khỏe.
§
Acc ChatGPT reg qua Hotmail sẵn sàng nạp pool dùng ngay (ngâm 7 ngày chỉ áp dụng cho Hotmail). Nạp pool ChatGPT-Web phân bổ tối thiểu 2 acc/IP và gán proxy_assignments đúng port proxy.
§
Watchdog audit compliance farm gates BẮT BUỘC lọc sạch test/mock artifacts (pytest, target.py) và chuẩn hóa timestamp local naive sang UTC; gate chặn có auto-rewire/tự sửa <= 1 turn tính là REWIRED, cấm đánh FAIL.