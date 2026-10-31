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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
