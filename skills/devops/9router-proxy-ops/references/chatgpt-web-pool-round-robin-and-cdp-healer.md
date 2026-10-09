# ChatGPT-Web Pool Round-Robin & CDP Cookie Auto-Healer

## Bối cảnh & Hiện trạng
- **Provider `chatgpt-web`** trên OmniRoute (`:20129`) dùng cơ chế Reverse-Proxy duyệt qua web session cookie (`__Secure-next-auth.session-token`).
- **Khả năng Tool Calling (Tay chân)**: Hỗ trợ 100% qua cơ chế Web Tools Prompt Emulation (`open-sse/executors/chatgpt-web.ts`). Hermes hoặc bất kỳ OpenAI client nào đều có thể gửi schema `tools` và nhận về `tool_calls` chuẩn chỉnh.
- **Tử huyệt Priority Dồn Tải**:
  - Nếu cấu hình gọi model `chatgpt-web/gpt-5.6-sol-high` đơn lẻ trong combo Priority, request dồn vào acc P01/P02 $\rightarrow$ dính 502 Rate Limit $\rightarrow$ kích hoạt 403 Sentinel (Cloudflare Turnstile) $\rightarrow$ đứt gãy vòng lặp `api/auth/session` refresh $\rightarrow$ token hết hạn tự nhiên (`ChatGPT session expired`).

## Giải pháp Chuẩn Hóa
1. **Combo Round-Robin `chatgpt-web-pool`**:
   - Gắn toàn bộ các `connectionId` của tài khoản live vào combo riêng biệt với `strategy: round-robin`, `stickyRoundRobinLimit: 1`, `failoverBeforeRetry: true`.
   - Cắm `combo-ref: chatgpt-web-pool` làm Tier 0 trong combo `review` / `plan` và Tier fallback trong `omni-worker`.
   - Giúp chia đều tải cho 15-17 accs, triệt tiêu nguy cơ dồn tải kích hoạt Cloudflare Sentinel.

2. **Cơ chế Khôi Phục Cookie Tự Động qua GPMLogin CDP (`refresh_chatgpt_web_cookies.py`)**:
   - Khi token hết hạn, không cần đăng nhập lại từ đầu nếu profile GPM đã lưu phiên.
   - **Quy trình tuần tự**:
     1. Khởi động profile GPM qua Local API: `GET http://127.0.0.1:19995/api/v3/profiles/start/{pid}?win_scale=0.8`.
     2. Lấy `remote_debugging_address` (CDP port).
     3. Kết nối websocket CDP đến tab `page`, điều hướng `https://chatgpt.com`, đợi 5-6s.
     4. Gọi `Network.getCookies` cho domain `https://chatgpt.com`.
     5. Ghép cookie header: `"; ".join([f"{c['name']}={c['value']}" for c in cookies])`.
     6. Validate qua OmniRoute: `POST http://127.0.0.1:20129/api/providers/validate` với `{"provider": "chatgpt-web", "apiKey": cookie_str}`.
     7. Nếu `valid == True`: cập nhật SQLite `C:\Users\Kibe\.omniroute\storage.sqlite` bảng `provider_connections` (`is_active=1`, `test_status='active'`, xóa lỗi) và đồng bộ vào `combos`.
     8. **BẮT BUỘC**: Luôn đóng profile GPM trong khối `finally`: `GET http://127.0.0.1:19995/api/v3/profiles/close/{pid}` để không treo RAM.

3. **Cron Watchdog Định Kỳ Báo Cáo Farm Alert**:
   - **Tần suất**: Chạy 1 lần/ngày vào lúc `05:00 AM` (`0 5 * * *`) qua script `cron_chatgpt_web_pool_watchdog.py`.
   - **Cơ chế**: Thăm dò lướt (Zero-cost API check) $\rightarrow$ Chỉ bật GPM hồi sinh nếu phát hiện có acc bị rớt session $\rightarrow$ In stdout để Hermes cron (`deliver='telegram:-5373649734'`) tự động gửi báo cáo tóm tắt về nhóm Farm Alert.
