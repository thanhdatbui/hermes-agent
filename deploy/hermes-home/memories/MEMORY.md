Cronjob batch ngầm đặt deliver='local' chống spam stdout; Watchdog có deliver='local' BẮT BUỘC tự dispatch Telegram (cấm chỉ print). Hàm nạp token BẮT BUỘC tự đọc trực tiếp từ hermes/.env chống rớt dependency/import automation_core.
§
Khi TikTok thiếu acc/mismatch: BẮT BUỘC auto-login/reconcile bù; máy Admin (>=200) nạp host config admin.yaml, socket 192.168.110.119:5037 & workbook Admin; Canary tái hiện lỗi BẮT BUỘC tra đúng --row <N> của nick vắng mặt (cấm test nhầm --row 1 có sẵn sinh pass ảo); timeout >= 720s.
§
Khi pool OmniRoute lỗi: đối soát proxy_registry & test /api/providers/{cid}/test; token sống bật is_active=1 ngay. Acc ChatGPT reg xong dùng ngay; gán >= 2 acc/proxy kèm proxy_assignments.
§
Watchdog đối soát TikTok Web (SQLite snapshots) BẮT BUỘC đối chiếu theo Account ID / Username thay vì Row máy; runner khi gặp timeout BẮT BUỘC salvage follow từ state file thay vì gán 0.
§
Tool 2FA và cron xen ca chạy cả ngày BẮT BUỘC dùng Just-In-Time (JIT) lock từng máy (cấm bulk pre-reserve giữ lock hàng loạt trong queue) và bọc predicate né khung giờ reboot/đệm trước ca cron.
§
Tài khoản Gmail chuẩn clean_v2 đã tắt Google Prompt hoàn toàn chỉ dùng 2FA TOTP: login GPM 100% trên PC qua pyotp, không cần ADB hay máy S7; cấm chặn nhầm acc farm có recovery khoaleemagic khi đã có totp_secret.
§
Cron watchdog chạy batch (2FA, Gmail reg) BẮT BUỘC ghi nhận run_date độc lập với status success/fail; hàm already_ran cấm bọc điều kiện is_success để chống vòng lặp re-run spam Telegram khi có máy lỗi.
