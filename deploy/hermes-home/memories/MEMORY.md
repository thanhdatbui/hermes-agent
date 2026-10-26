Cronjob batch ngầm đặt deliver='local' chống spam stdout; Watchdog có deliver='local' BẮT BUỘC tự dispatch Telegram (cấm chỉ print). Hàm nạp token BẮT BUỘC tự đọc trực tiếp từ hermes/.env chống rớt dependency/import automation_core.
§
Khi TikTok thiếu acc/mismatch: auto-login/reconcile bù; máy Admin (>=200) nạp admin.yaml, socket 192.168.110.119:5037 & workbook Admin; Canary tra đúng --row lỗi (timeout >= 720s). Khi Graph API token hết hạn: dùng GPM cổng 19995 đọc OTP qua read_otp_gpm.py kèm exclude_codes.
§
Nạp ChatGPT-Web Omni: trần 2 acc/IP kèm proxy_assignments; màn /about-you = acc CHƯA reg (Hotmail farm là mail mua, cấm bịa 'reg hotmail'); file admin/gmail_clean_v2.xlsx chứa 100% Hotmail Admin; pass ChatGPT cấm nối tĩnh @Taadaa2026 chống pattern ban, bắt buộc random độc nhất & lưu Excel; script reg cấm exit 0 khi empty/fail chống supervisor đóng dấu ảo; lọc GPM GroupId!=0; pre-validate Graph token; cấm base64.
§
Watchdog đối soát TikTok Web (SQLite snapshots) BẮT BUỘC đối chiếu theo Account ID / Username thay vì Row máy; runner khi gặp timeout BẮT BUỘC salvage follow từ state file thay vì gán 0.
§
Tool 2FA và cron xen ca chạy cả ngày BẮT BUỘC dùng Just-In-Time (JIT) lock từng máy (cấm bulk pre-reserve giữ lock hàng loạt trong queue) và bọc predicate né khung giờ reboot/đệm trước ca cron.
§
Tài khoản Gmail chuẩn clean_v2 đã tắt Google Prompt hoàn toàn chỉ dùng 2FA TOTP: login GPM 100% trên PC qua pyotp, không cần ADB hay máy S7; cấm chặn nhầm acc farm có recovery khoaleemagic khi đã có totp_secret.
§
Auto-Heal: đào log/ảnh ca, cấm chụp máy tắt màn; WinRT OCR primary; Canary auto-device; storm>=3 alert. Claude CLI bị hook guard_claude_cli_lock.py khóa cứng (chỉ mở khi có User Sudo/Strike 3). Avatar picker: visual match chống nhầm Tile 1; lifecycle_guard:260 bọc except null char.
§
Mọi fix hạ tầng Hermes/Omni bắt buộc qua Protection Regression Gate (infra_regression_gate.py): threshold 0.30, retries 4, delay 6s (headroom ~90s), cấm self-fallback 20129, watchdog deadlock failures [4, 6]; cấm sửa triệu chứng gây bão tải.