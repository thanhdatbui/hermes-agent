Cronjob batch ngầm đặt deliver='local' chống spam stdout; Watchdog có deliver='local' BẮT BUỘC tự dispatch Telegram (cấm chỉ print). Hàm nạp token BẮT BUỘC tự đọc trực tiếp từ hermes/.env chống rớt dependency/import automation_core.
§
Khi TikTok thiếu acc/mismatch: BẮT BUỘC auto-login/reconcile bù; máy Admin (>=200) nạp host config admin.yaml, socket 192.168.110.119:5037 & workbook Admin; Canary tái hiện lỗi BẮT BUỘC tra đúng --row <N> của nick vắng mặt (cấm test nhầm --row 1 có sẵn sinh pass ảo); timeout >= 720s.
§
Khi pool OmniRoute nạp acc ChatGPT: BẮT BUỘC lọc candidate qua supervisor state (chỉ lấy stage DONE/WAIT_7D hoặc có chatgpt_registered_at, cấm bốc profile mới ở HOTMAIL_LOGIN); gán đúng port proxy_assignments (trần tạm thời 2 acc/IP); cấm dùng base64 qua terminal.
§
Watchdog đối soát TikTok Web (SQLite snapshots) BẮT BUỘC đối chiếu theo Account ID / Username thay vì Row máy; runner khi gặp timeout BẮT BUỘC salvage follow từ state file thay vì gán 0.
§
Tool 2FA và cron xen ca chạy cả ngày BẮT BUỘC dùng Just-In-Time (JIT) lock từng máy (cấm bulk pre-reserve giữ lock hàng loạt trong queue) và bọc predicate né khung giờ reboot/đệm trước ca cron.
§
Tài khoản Gmail chuẩn clean_v2 đã tắt Google Prompt hoàn toàn chỉ dùng 2FA TOTP: login GPM 100% trên PC qua pyotp, không cần ADB hay máy S7; cấm chặn nhầm acc farm có recovery khoaleemagic khi đã có totp_secret.
§
Cron watchdog chạy batch (2FA, Gmail reg) BẮT BUỘC ghi nhận run_date độc lập với status success/fail; hàm already_ran cấm bọc điều kiện is_success để chống vòng lặp re-run spam Telegram khi có máy lỗi.
§
Ổ D Admin (192.168.110.119) lưu trữ phân tầng: local giữ clip 1..20, clip >=21 offload lên Google Drive; video gốc chỉ kéo bù khi tổng (local + gdrive) < 45. Game TFT Live cài ở D:\Riot Games, PBE ở C:\Riot Games.
§
Auto-Heal khép kín (incident-auto-heal-dispatcher): gom lỗi feed/follow/upload qua emit_if_needed, bắt buộc resolve_serial_and_args qua inspect_machine lấy serial phần cứng ADB thật; Canary failover --auto-device né kẹt lock ca nuôi; gom storm >= 3 lỗi blocked báo Farm Alert.