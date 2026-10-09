# ChatGPT Batch Automation Architecture: Subagent Timeout Pitfall vs Background OS Runner

## 1. Bản Chất Kiến Trúc
Khi thực hiện batch automation trên GPMLogin qua Playwright CDP (như đăng nhập hàng loạt ChatGPT Google SSO, cấp quyền OAuth, giải mã cookie session-token):
- **Bản chất công việc**: 100% Browser Automation & Network I/O trên PC Host (Local API Port 19995 + Playwright Chromium CDP + Proxy di động Mobi/MikroTik).
- **Hoàn toàn KHÔNG tiêu tốn token LLM / Quota AI** cho từng profile hay từng thao tác đăng nhập.

---

## 2. Cạm Bẫy Timeout Của Subagent (Subagent Budget Exhaustion)
- **Cơ chế**: Hermes Worker Subagent (`delegate_task`) có giới hạn vòng đời cố định: `timeout = 600s` (10 phút) hoặc `max_iterations = 15..20 calls`.
- **Thực tế vận hành qua Proxy 4G di động**: Mỗi profile GPM cần ~2.5–4 phút để:
  1. Gọi GPM API v3 khởi động profile (`/profiles/start/{id}`).
  2. Playwright kết nối CDP, mở `chatgpt.com/auth/login`.
  3. Xử lý banner cookie, click `Continue with Google`, chờ redirect qua Google SSO, click chọn tài khoản.
  4. Xử lý màn hình Onboarding (họ tên, năm sinh/tuổi) và chờ tải màn hình chính ChatGPT.
  5. Trích xuất cookie `__Secure-next-auth.session-token` hoặc `/api/auth/session` accessToken và nạp vào OmniRoute (Port 20129).
  6. Tắt profile (`/profiles/stop/{id}`).
- **Hệ quả**: Gom quá 2 tài khoản (ví dụ 3–5 tài khoản) vào 1 Worker Subagent sẽ chắc chắn vượt quá ngưỡng 600s $\rightarrow$ Worker bị runtime timeout, toàn bộ task bị fail im lặng và không trả về kết quả nào cho Coordinator.

---

## 3. Quy Tắc Phân Luồng Điều Phối (Coordinator Protocol)

1. **Gate 1 - Phân Biệt Code-Surgery vs Batch-Job:**
   - **Code-Surgery / Canary Đơn Lẻ (1 Profile)**: Có thể dùng Worker Subagent để kiểm tra tính đúng đắn của logic trong môi trường cô lập, thời gian < 3 phút.
   - **Batch-Job (>2 Profiles)**: **TUYỆT ĐỐI KHÔNG** dispatch toàn bộ batch vào Worker Subagent.
2. **Kỹ Thuật Background OS Runner Cho Batch:**
   - Coordinator chuẩn bị script hoàn chỉnh (hoặc dùng template có sẵn như `playwright_login_remaining.py`).
   - Kích hoạt chạy nền trên hệ điều hành host qua `terminal(command="python script.py", background=True, notify_on_complete=True)`.
   - Script tự động duyệt danh sách, ghi log tiến độ vào file `logs/*.log` và lưu screenshot nghiệm thu vào `debug_screenshots/`.
   - Coordinator chỉ việc inspect O(1) trạng thái hoàn thành mà không làm nghẽn context hay dính timeout của subagent.
