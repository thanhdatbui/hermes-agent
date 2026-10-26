Cronjob ngầm deliver='local' chống spam stdout; Watchdog deliver='local' tự dispatch Telegram (cấm chỉ print). Hàm nạp token đọc trực tiếp hermes/.env chống rớt import.
§
TikTok lệch/thiếu acc: auto-login/reconcile bù; Admin (>=200) nạp admin.yaml, socket 192.168.110.119:5037 & workbook Admin; Canary tra đúng --row lỗi (timeout >= 720s). Graph token hết hạn (AADSTS70000): đọc OTP qua GPM cổng 19995 (read_otp_gpm.py) kèm exclude_codes; cấm spam dump XML làm S7 quá tải văng offline (ép WinRT OCR). Switcher cấm strip số đuôi làm lẫn nick (khanhthu2275 vs khanhthu1609).
§
Nạp ChatGPT-Web: trần 2 acc/IP + proxy_assignments; worker <= 5; Hotmail là mail mua sẵn; màn /about-you = acc chưa reg; pass ChatGPT random độc nhất lưu Excel; script reg cấm exit 0 khi fail; lọc GPM GroupId!=0; pre-validate Graph token; cấm base64.
§
Watchdog đối soát TikTok Web (SQLite snapshots) BẮT BUỘC đối chiếu theo Account ID / Username thay vì Row máy; runner khi gặp timeout BẮT BUỘC salvage follow từ state file thay vì gán 0.
§
Tool 2FA và cron xen ca chạy cả ngày BẮT BUỘC dùng Just-In-Time (JIT) lock từng máy (cấm bulk pre-reserve giữ lock hàng loạt trong queue) và bọc predicate né khung giờ reboot/đệm trước ca cron.
§
Tài khoản Gmail chuẩn clean_v2 đã tắt Google Prompt hoàn toàn chỉ dùng 2FA TOTP: login GPM 100% trên PC qua pyotp, không cần ADB hay máy S7; cấm chặn nhầm acc farm có recovery khoaleemagic khi đã có totp_secret.
§
Auto-Heal: đào log/ảnh ca, cấm chụp máy tắt màn; WinRT OCR primary; Canary auto-device; storm>=3 alert. Claude CLI dùng khi user gọi/Strike 3. Gate chuẩn O(1): check đúng sự kiện tool thật (browser_vision), cấm OCR proxy đối soát ảnh/in chữ canvas; dẹp Security Theater (DACL/HMAC tự ký, SHA256 blockchain log gate_audit); safe_push bỏ duyệt ngược JSONL; Closeout delta rỗng = Vận Hành PASS < 0.2s.
§
Fix hạ tầng Hermes/Omni qua infra_regression_gate.py: retries 4, delay 6s (~90s headroom), cấm self-fallback 20129, deadlock [4,6], probe 5s, cấm fail-open. Omni SQLite cleanup 6h/lần trần <=3 ngày đủ 6 bảng. GuardGate rules.json scope repo/path độc lập + global invariants, cấm để chéo rule làm false deny.