---
name: logged-in-chrome-cdp-marketplace
description: Use the user's already-configured, logged-in Hermes Chrome CDP profile for Shopee and other marketplace research, as well as browser automation via Chrome CDP (127.0.0.1:9222). Trigger whenever the user says to search Shopee/marketplaces via the saved Chrome/CDP account, or asks to automate/interact with websites via Chrome CDP ("dùng chrome CDP").
version: 1.0.0
author: Hermes Agent
platforms: [windows]
tags: [chrome, cdp, shopee, marketplace, logged-in-profile]
---
# Logged-in Hermes Chrome CDP for Marketplace Research & User Browser Inspection

## User-specific profiles & CDP setup

1. **User Main Chrome Profile (Kal - `jinrakal@gmail.com`):**
   - User Data Dir: `C:\Users\Kibe\AppData\Local\Google\Chrome\User Data`
   - Profile Subdirectory: `Profile 4`
   - Chứa toàn bộ phiên đăng nhập thật của User (BoxTaiKhoan, Shopee, mạng xã hội, lịch sử mua hàng cá nhân).
   - **Khi User yêu cầu dùng Chrome chính của User qua Remote Debugging / CDP:**
     - Đóng các tiến trình Chrome cũ: `powershell.exe -Command "Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue"`
     - Khởi chạy lại Chrome chính đính kèm cổng CDP 9222:
       `powershell -Command "Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--remote-debugging-port=9222', '--user-data-dir=\"C:\Users\Kibe\AppData\Local\Google\Chrome\User Data\"', '--profile-directory=\"Profile 4\"'"`
     - Kết nối CDP qua `http://127.0.0.1:9222/json/version` để tương tác trực tiếp trên profile chính của user.

2. **Hermes Isolated Browser Profile:**
   - User Data Dir: `C:\Users\Kibe\AppData\Local\hermes\browser_profile`
   - Profile Subdirectory: `Default`
   - Dùng cho các tác vụ crawl/tách biệt không đụng chạm đến profile cá nhân.

## Mandatory operating rule

When the user asks to search Shopee or another marketplace:

1. **Prioritize CDP immediately:** Connect directly to the user's running Chrome CDP session (`127.0.0.1:9222`) first. Do NOT run external web search / curl search or guess snippets when the user asks for Shopee marketplace items.
2. Check the live CDP endpoint first:
   - `curl -s http://127.0.0.1:9222/json/version`
   - `curl -s http://127.0.0.1:9222/json/list`
3. Connect to the existing non-headless Hermes Chrome instance over CDP. Use its current context/profile and reuse/create a tab in the authenticated session (`jinrakal`).
4. Never create a separate headless Chrome, temporary profile, or regular Chrome profile for the task. Never use Google snippets as a substitute while claiming the data came from Shopee.
5. Never read, decrypt, export, or print cookies, passwords, tokens, or account credentials. Use the live authenticated browser context only.
6. Do not close the user's browser or browser context. Close only a temporary tab created by this task after verification, unless the user asks to leave it open.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
