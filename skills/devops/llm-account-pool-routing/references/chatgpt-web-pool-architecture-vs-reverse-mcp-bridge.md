# ChatGPT Web Pool Architecture vs. Reverse MCP Web Bridge

## 1. Bối cảnh Kỹ thuật: Reverse MCP Bridge vs. Managed Farm Pool

### Hiện Tượng "MCP Bridge Ngược Từ Web" Trôi Nổi (Ví dụ Antigravity Jio Pro)
- **Bản chất thủ thuật:** Một số bên bán tài khoản khuyến mãi viễn thông giá rẻ (như Jio Google Pro 20k-30k) bị Antigravity IDE bóp quyền chọn model cao cấp. Để kích cầu, họ tặng kèm tool "MCP Server" làm cầu nối ngược:
  ```
  Antigravity IDE/CLI  --->  Local MCP Server (Python/Node)  --->  Web Session (gemini.google.com / chatgpt.com)
  ```
- **Tử huyệt kỹ thuật & Rủi ro sản xuất:**
  1. **Direct IP Egress & Rate-Limit Treo Mõm:** Chạy thẳng trên IP gia đình hoặc máy dev, không có cơ chế gán proxy độc lập. Giao diện Web kiểm soát token/rate-limit rất chặt; khi đẩy context code lớn vào, chỉ 2-3 câu lệnh là tài khoản chạm trần hoặc bị Cloudflare/CAPTCHA chặn đứng.
  2. **Độ trễ cao (Latency Bloat):** Quá trình reverse scraping/CDP mất từ 5 đến 15 giây cho mỗi lượt tương tác, không hỗ trợ streaming API chuẩn, gây nghẽn luồng điều phối tự động.
  3. **Nguy cơ An ninh mạng:** Tải file ZIP/Google Drive từ các kênh buôn bán tài khoản cá nhân tiềm ẩn rủi ro mã độc đánh cắp `.env`, token môi trường, SSH keys và cookie trình duyệt.

---

## 2. Kiến Trúc Managed ChatGPT Web Pool của Taadaa Farm (`gpt-web-sol` / `:20129`)

Hệ thống Taadaa Farm vận hành ChatGPT Web theo mô hình **hạ tầng tập trung có quản trị** qua OmniRoute (`port 20129`), phục vụ cho các tác vụ Reviewer (`closeout_gate.py`), Repair (`sol_repair.py`) và Fallback Worker (`sol_worker.py`).

### 2.1. Cơ Chế Tự Động Xoay Tài Khoản (Automated Account Rotation)
Hệ thống xoay tài khoản tự động ở 2 tầng khép kín:
1. **Tầng Router (OmniRoute Combo Failover):**
   - Model `gpt-web-sol` được cấu hình dưới dạng combo load-balancing round-robin liên kết hàng chục tài khoản ChatGPT Web trong `storage.sqlite`.
   - Khi một tài khoản bị chạm quota 429 hoặc timeout, OmniRoute tự động tạm dừng tài khoản đó và xoay sang tài khoản kế tiếp trong combo mà client không cần khởi động lại session.
   - Client (`sol_worker.py` / `closeout_gate.py`) bắt mã `rc=125` (`QUOTA_BLOCKED`) để tự động thử lại khi router hoàn tất xoay tài khoản.
2. **Tầng Cronjob Bơm Tài Khoản Tự Động (`cron-auto-feed-chatgpt-pool`):**
   - Cronjob `cron-auto-feed-chatgpt-pool` (ID: `3269c6faeb03`) chạy định kỳ **15 phút một lần** (`*/15 * * * *`).
   - Script `cron_auto_feed_chatgpt_pool.py` quét kho 1.464 profile GPM (ưu tiên phân vùng `cand_h` Hotmail và `cand_g` Gmail).
   - Tự động mở profile GPM ngầm qua CDP, trích xuất `session-token` mới nhất, cập nhật vào bảng `provider_connections` và gắn vào combo `gpt-web-sol`.

### 2.2. Bất Biến Gán Proxy 1-1 Chuẩn (Fail-Closed Egress Invariant)
Để tránh thảm họa rò rỉ IP máy chủ làm chết hàng loạt tài khoản (`account_deactivated`), quy tắc gán proxy được khóa cứng trong mã nguồn:
1. **Truy vấn Proxy Registry theo Cổng GPM:**
   Mỗi profile GPM mang một cổng proxy cố định (dải 51xx hoặc 100xx trỏ về `test.taadaa.click` hoặc `mirotik1.taadaa.click`).
2. **Cơ Chế Fail-Closed Tuyệt Đối:**
   ```python
   # BẮT BUỘC resolve được proxy TRƯỚC khi chạm connection/is_active
   port = r.get("port")
   host = "test.taadaa.click" if port < 10000 else "mirotik1.taadaa.click"
   cur.execute("SELECT id FROM proxy_registry WHERE host=? AND port=? LIMIT 1", (host, port))
   p_row = cur.fetchone()
   if not p_row:
       logger.error(f"[SKIP FAIL-CLOSED] {email}: không tìm thấy proxy_registry -> không tạo/bật connection")
       continue  # Dừng ngay, tuyệt đối không kích hoạt is_active
   ```
   Nếu cổng proxy chưa sẵn sàng trong `proxy_registry`, tài khoản **KHÔNG BAO GIỜ được bật `is_active = 1`**.
3. **Ràng Buộc `proxy_assignments`:**
   Mỗi connection `chatgpt-web` bắt buộc có một bản ghi tương ứng trong bảng `proxy_assignments` với `scope = 'account'` và `scope_id = <connection_id>`, ép toàn bộ HTTP request gửi ra ngoài phải đi qua đúng địa chỉ proxy của profile đó.

---

## 3. Kiến Trúc Autonomous Fallback Worker Trên Sol Web (`sol_worker.py`)

Khi cả Claude CLI và Agy CLI cạn quota 5h/weekly, `sol_worker.py` đóng vai trò là tầng Autonomous Worker dự phòng cuối cùng:

1. **State Machine Cục Bộ (Local Context Management):**
   Toàn bộ lịch sử ReAct loop được lưu trữ tại tiến trình local, không phụ thuộc vào session state của giao diện Web, giúp an toàn 100% khi OmniRoute đổi tài khoản giữa chừng.
2. **DSL Line-Based Parser Chịu Lỗi:**
   Thay vì dùng JSON thuần (dễ bị vỡ dấu ngoặc hoặc hỏng escape sequence khi stream SSE dài), worker sử dụng DSL phân dòng:
   - `ACTION: READ_FILE` kèm `PATH:` và `LINES:`
   - `ACTION: PATCH` kèm khối `<<<<<<< SEARCH ... ======= ... >>>>>>>`
   - `ACTION: COMMAND` kèm `COMMAND:`
   - `ACTION: DONE` kèm `SUMMARY:`
   - `ACTION: BLOCKED` kèm `REASON:`
3. **Cưỡng Chế Xác Minh Trước Khi Hoàn Tất (`has_verified` Gate):**
   - Khởi tạo `has_verified = False`.
   - Mỗi khi áp dụng một `ACTION: PATCH` mới, tự động reset `has_verified = False`.
   - Chỉ chuyển `has_verified = True` khi có lệnh `ACTION: COMMAND` chạy test runner thành công (exit code 0).
   - Nếu model phát lệnh `ACTION: DONE` khi đã sửa file nhưng `has_verified is False`, worker **từ chối hoàn tất** và ép model phải thực thi lệnh kiểm thử.
4. **Command Sandbox & Atomic Patching:**
   - Thực thi subprocess với `shell=False`, chặn toàn bộ shell metacharacters (`;&|`$`).
   - Giới hạn runner allowlist: chỉ cho phép `python -m pytest`, `python -m unittest` hoặc `pytest`.
   - Patch file nguyên tử qua file tạm `.tmp.<uuid>`, đồng bộ đĩa `os.fsync`, kiểm tra read-back byte-for-byte và tự động hoàn nguyên (rollback) nếu có sai lệch.
