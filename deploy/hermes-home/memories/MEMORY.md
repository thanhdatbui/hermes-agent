Cronjob batch ngầm đặt deliver='local' chống spam stdout; Watchdog có deliver='local' BẮT BUỘC tự dispatch Telegram (cấm chỉ print). Hàm nạp token BẮT BUỘC tự đọc trực tiếp từ hermes/.env chống rớt dependency/import automation_core.
§
Khi TikTok thiếu acc/mismatch: auto-login/reconcile bù; máy Admin (>=200) nạp admin.yaml, socket 192.168.110.119:5037 & workbook Admin; Canary tra đúng --row lỗi (timeout >= 720s). Khi Graph API token hết hạn (AADSTS70000): dùng GPM profile (cổng 19995) đọc OTP web qua CDP (read_otp_gpm.py) kèm exclude_codes lọc OTP cũ.
§
Khi pool OmniRoute nạp acc ChatGPT: BẮT BUỘC lọc candidate qua supervisor state (chỉ lấy stage DONE/WAIT_7D hoặc có chatgpt_registered_at, cấm bốc profile mới ở HOTMAIL_LOGIN); gán đúng port proxy_assignments (trần tạm thời 2 acc/IP); cấm dùng base64 qua terminal.
§
Watchdog đối soát TikTok Web (SQLite snapshots) BẮT BUỘC đối chiếu theo Account ID / Username thay vì Row máy; runner khi gặp timeout BẮT BUỘC salvage follow từ state file thay vì gán 0.
§
Tool 2FA và cron xen ca chạy cả ngày BẮT BUỘC dùng Just-In-Time (JIT) lock từng máy (cấm bulk pre-reserve giữ lock hàng loạt trong queue) và bọc predicate né khung giờ reboot/đệm trước ca cron.
§
Tài khoản Gmail chuẩn clean_v2 đã tắt Google Prompt hoàn toàn chỉ dùng 2FA TOTP: login GPM 100% trên PC qua pyotp, không cần ADB hay máy S7; cấm chặn nhầm acc farm có recovery khoaleemagic khi đã có totp_secret.
§
Cron watchdog batch (2FA, Reg Gmail) ghi nhận run_date độc lập kết quả (chống re-run spam); nhãn ca dynamic theo giờ; lệnh SSH Admin (M201-280) bắt buộc nạp AssignmentManifest riêng, lockRoot dynamic theo USERPROFILE và parse failure breakdown từ stdout gộp telemetry toàn farm.
§
Ổ D Admin (192.168.110.119) lưu trữ phân tầng: local giữ clip 1..20, clip >=21 offload lên Google Drive; video gốc chỉ kéo bù khi tổng (local + gdrive) < 45. Game TFT Live cài ở D:\Riot Games, PBE ở C:\Riot Games.
§
Auto-Heal khép kín (incident-auto-heal-dispatcher): gom lỗi feed/follow/upload qua emit_if_needed, bắt buộc resolve_serial_and_args qua inspect_machine lấy serial phần cứng ADB thật; Canary failover --auto-device né kẹt lock ca nuôi; gom storm >= 3 lỗi blocked báo Farm Alert.