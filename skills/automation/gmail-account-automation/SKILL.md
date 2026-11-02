---
name: gmail-account-automation
description: "Automation workflows for Gmail accounts on the Taadaa farm: Playwright + GPM Chrome, Singbox proxies, Google 2FA/OAuth, and Excel sync."
---
# Gmail Account Automation (Taadaa Farm)

- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.
- Quy trình đăng ký tài khoản AI, vượt xác minh tuổi & Meta OIDC checkpoints: xem `references/meta-muse-ai-age-verification-and-oidc-flow.md`.
- Kỷ luật khai thác hòm thư Farm (Hotmail/Outlook) qua Microsoft Graph API tự động (Zero User-Prompt) & cấm đùn đẩy/khóc lóc bại liệt: xem `references/meta-muse-ai-age-verification-and-oidc-flow.md` (Mục 5, 7).
- Kỷ luật cách ly sạch Profile GPM + Proxy mới khi đổi acc test (chống dính vết cũ) & kiên định bám sát Geolocation User chỉ định: xem `references/meta-muse-ai-age-verification-and-oidc-flow.md` (Mục 4).
- Bẫy profile GPM rỗng proxy (gây Hard Phone Checkpoint), bệnh mù Email khôi phục trong Challenge Selection & kỷ luật điều tra chống làm đối phó: xem `references/gpm-login-empty-proxy-trap-and-challenge-selection-blindness.md`.
- Quy trình reg TikTok Lite qua Google SSO tích tuổi đời, bản chất cấm Hotmail manual vs Google SSO và kỷ luật BẮT BUỘC Preflight Check Live Gmail qua Google lookup: xem `references/tiktok-lite-google-sso-reg-and-preflight-checklive.md`.
- Kỷ luật phản hồi chống bẫy "Bị chặn khóc lóc" (Whining Trap) & cơ chế Receipt Guard vạch trần hứa suông: xem `references/tiktok-lite-google-sso-reg-and-preflight-checklive.md` (Mục 5).
- Bẫy số liệu lũy kế cả ngày gây báo cáo ảo trùng lặp lỗi giữa các ca (Sáng/Chiều/Tối) trong watchdog GPM login: xem `references/gpm-login-shifts-cumulative-fail-phantom-reporting.md`.
- Quy trình mở profile GPM qua API, điều hướng CDP đến màn hình quét mã QR và phối hợp camera phone thật: xem `references/gpm-profile-manual-qr-scan-handshake-workflow.md`.
- Quy trình cứu acc dính Phone Checkpoint (Cooldown 24h, QR Code challenge/iap SMS trap), đối soát ảnh thị giác Gate 6, giải mã chỉ số lũy kế ca & tra cứu kết quả batch reg Gmail Admin-PC (D:/CodexRuntime/.../summary.json): xem `references/gpm-login-shifts-and-admin-farm-onboarding-rules.md`.
- Kỹ thuật truy vấn remote `summary.json` từ Admin qua PowerShell không bị kẹt `admin_ssh` Allowlist & cơ chế đọc ảnh Phone Verify bằng WinRT OCR: xem `references/admin-ssh-powershell-allowlist-and-remote-summary-retrieval.md`.
- Kỷ luật kiểm thử Live Command qua Remote SSH (`admin_ssh.py`) & chống bẫy Mock Xanh ảo làm lọt lỗi Allowlist: xem `references/remote-ssh-live-command-validation-and-anti-mock-trap.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
