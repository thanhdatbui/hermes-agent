---
name: logged-in-chrome-cdp-marketplace
description: Use when the user asks to open, control, or automate Chrome CDP (127.0.0.1:9222) ("mở chrome cdp", "vào chrome cdp"). Automatically launches the user's dedicated CDP profile (Profile 4) if not running, or connects directly to active tabs without asking for flags or restarting.
version: 1.1.0
author: Hermes Agent
platforms: [windows]
tags: [chrome, cdp, automation, dedicated-profile]
---
# Dedicated Chrome CDP Profile Automation

## 1. Cơ Chế Khóa Cơ Học (Mechanical Lock)
- **Profile CDP:** Là profile riêng biệt `Profile 4` (`C:\Users\Kibe\AppData\Local\Google\Chrome\User Data`), chạy cổng cố định **`127.0.0.1:9222`**.
- **CẤM:** Tuyệt đối KHÔNG bao giờ hỏi User "đã bật cờ 9222 chưa" hay yêu cầu User restart Chrome.
- **QUY TRÌNH THỰC THI DUY NHẤT:** Khi User bảo "mở chrome cdp" hoặc yêu cầu thao tác qua CDP:
  1. Kiểm tra trạng thái cổng `http://127.0.0.1:9222/json/version`.
  2. Nếu CHƯA chạy: Tự động chạy script cơ giới hóa `scripts/ensure_chrome_cdp.py [url]` để khởi động đúng profile với flag `--remote-debugging-port=9222`.
  3. Nếu ĐÃ chạy: Đọc danh sách tab qua `http://127.0.0.1:9222/json/list` hoặc mở tab mới bằng `Target.createTarget` qua WebSocket (`scripts/ensure_chrome_cdp.py <url>`).
  4. Tương tác JS / DOM bằng `scripts/cdp_eval.py <ws_page_url> <expression>`.
