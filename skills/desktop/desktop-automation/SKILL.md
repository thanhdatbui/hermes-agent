---
name: desktop-automation
description: Best practices and safety patterns for using computer-use and desktop automation.
---
# Desktop Automation Best Practices

This skill captures learnings and pitfalls for driving the user's desktop via tools like `computer_use`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.

- [Meta Muse AI Registration & Geoblock Bypass](references/meta-muse-ai-registration-and-geoblock-bypass.md): Kinh nghiệm bypass Geoblock US/Canada, nạp ảnh selfie và điền form Next.js Meta OIDC.
- [GPM Antidetect & Meta/Instagram Auth Automation Quirks](references/gpm-meta-auth-and-proxy-quirks-202610.md): GPM profile creation key ('Profile_name'), proxy formatting, Playwright Next.js input traps, and Instagram/Meta 2FA TOTP automation.
- [Running Chrome Background Automation Without CDP](references/running-chrome-background-automation-without-cdp.md): Điều khiển Chrome đang chạy ngầm bằng `computer_use` (SOM + `set_value` UIA ValuePattern) khi không mở port CDP 9222.

