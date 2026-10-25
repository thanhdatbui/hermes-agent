Cronjob batch ngầm đặt deliver='local' chống spam stdout; Watchdog có deliver='local' BẮT BUỘC tự dispatch Telegram (cấm chỉ print). Hàm nạp token BẮT BUỘC tự đọc trực tiếp từ hermes/.env chống rớt dependency/import automation_core.
§
Khi TikTok Switcher thiếu account (ACCOUNT_MISSING), BẮT BUỘC kích hoạt auto-login / Thêm tài khoản (recovery_handler=tiktok_login); CẤM phân biệt máy trắng acc hay viện cớ an toàn / lệch nhịp farm để dừng máy fail-closed.
§
Khi pool OmniRoute (ChatGPT-Web/Codex) lỗi: BẮT BUỘC đối soát proxy_registry (credentials port) và test trực tiếp /api/providers/{cid}/test trước khi kết luận; token còn sống phải bật is_active=1 ngay thay vì chỉ thụ động cô lập.
§
Watchdog đối soát TikTok Web (SQLite snapshots) BẮT BUỘC đối chiếu theo Account ID / Username thay vì Row máy; runner khi gặp timeout BẮT BUỘC salvage follow từ state file thay vì gán 0.
§
Tool 2FA và cron xen ca chạy cả ngày BẮT BUỘC dùng Just-In-Time (JIT) lock từng máy (cấm bulk pre-reserve giữ lock hàng loạt trong queue) và bọc predicate né khung giờ reboot/đệm trước ca cron.
§
Thang luân chuyển worker tự động: Sol (Tier 1) -> Agy (Tier 2) -> Claude (Tier 3 fallback tự động khi T1/T2 fail thật sự, cấm dựng thêm lớp hỏi rườm rà). Sàn timeout cứng cho Sol & Agy trong dispatch_worker là SOL_AGY_TIMEOUT_FLOOR = 360s, cấm Coordinator tự ý truyền timeout < 360s làm chết tiến trình. Sửa Telegram adapter ở D:/Taadaa/Hermes bắt buộc sync sang venv site-packages và restart gateway mới có hiệu lực. Cấm dùng LaTeX \textbf, \longrightarrow trong chat Telegram.
§
Tài khoản Gmail chuẩn clean_v2 đã tắt Google Prompt hoàn toàn chỉ dùng 2FA TOTP: login GPM 100% trên PC qua pyotp, không cần ADB hay máy S7; cấm chặn nhầm acc farm có recovery khoaleemagic khi đã có totp_secret.
§
Cron watchdog chạy batch (2FA, Gmail reg) BẮT BUỘC ghi nhận run_date độc lập với status success/fail; hàm already_ran cấm bọc điều kiện is_success để chống vòng lặp re-run spam Telegram khi có máy lỗi.