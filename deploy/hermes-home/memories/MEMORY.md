Cronjob batch ngầm đặt deliver='local' chống spam stdout; Watchdog có deliver='local' BẮT BUỘC tự dispatch Telegram (cấm chỉ print). Hàm nạp token BẮT BUỘC tự đọc trực tiếp từ hermes/.env chống rớt dependency/import automation_core.
§
Khi TikTok thiếu acc/mismatch: auto-login/reconcile bù; máy Admin (>=200) nạp admin.yaml, socket 192.168.110.119:5037 & workbook Admin; Canary tra đúng --row lỗi (timeout >= 720s). Khi Graph API token hết hạn: dùng GPM cổng 19995 đọc OTP qua read_otp_gpm.py kèm exclude_codes.
§
Khi pool OmniRoute nạp acc ChatGPT: BẮT BUỘC lọc candidate qua supervisor state (chỉ lấy stage DONE/WAIT_7D hoặc có chatgpt_registered_at, cấm bốc profile mới ở HOTMAIL_LOGIN); gán đúng port proxy_assignments (trần tạm thời 2 acc/IP); cấm dùng base64 qua terminal.
§
Watchdog đối soát TikTok Web (SQLite snapshots) BẮT BUỘC đối chiếu theo Account ID / Username thay vì Row máy; runner khi gặp timeout BẮT BUỘC salvage follow từ state file thay vì gán 0.
§
Tool 2FA và cron xen ca chạy cả ngày BẮT BUỘC dùng Just-In-Time (JIT) lock từng máy (cấm bulk pre-reserve giữ lock hàng loạt trong queue) và bọc predicate né khung giờ reboot/đệm trước ca cron.
§
Tài khoản Gmail chuẩn clean_v2 đã tắt Google Prompt hoàn toàn chỉ dùng 2FA TOTP: login GPM 100% trên PC qua pyotp, không cần ADB hay máy S7; cấm chặn nhầm acc farm có recovery khoaleemagic khi đã có totp_secret.
§
Cron watchdog batch ghi nhận run_date độc lập kết quả (chống re-run spam); nhãn ca dynamic; lệnh SSH Admin (M201-280) nạp AssignmentManifest riêng, lockRoot dynamic theo USERPROFILE và parse failure breakdown gộp telemetry toàn farm.
§
Ổ D Admin: local giữ clip 1..20, clip >=21 offload GDrive; kéo bù khi tổng < 45. Game TFT Live ở D:\Riot Games, PBE ở C:\Riot Games.
§
Auto-Heal khép kín: gom lỗi feed/follow/upload qua emit_if_needed, resolve_serial_and_args lấy serial ADB thật; Canary failover --auto-device né kẹt ca nuôi; storm >= 3 lỗi blocked báo Farm Alert.
§
Khi atx-agent báo UI_DUMP_INVALID do rớt stub com.github.uiautomator: chạy reset_atx_agent(dev) hoặc am instrument stub để phục hồi tiến trình trước khi dump lại; TikTok kẹt Splash đen thì force-stop và mở lại.