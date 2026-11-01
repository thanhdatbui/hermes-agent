---
name: local-app-operations
description: "Safely update and operate locally hosted web applications through their installed/runtime surface, keeping application management separate from source-repository maintenance."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [local-app, web-dashboard, app-update, browser-ui, proxy-import, credential-safety]
    category: desktop
---
# Local application operations

Use this skill when the user asks to update, configure, log into, or import data into a locally running application with a browser dashboard (for example, a gateway, proxy manager, or self-hosted admin UI).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
- `references/chatgpt-web-feeder-sso-vs-direct-triage.md`: Xử lý lỗi EMPTY_SESSION_TOKEN do lệch luồng Google SSO vs Direct Hotmail trong auto-feed ChatGPT-Web.
