# Gemini Web Session Extraction via GPM CDP & ReAct Worker Architecture

## Bối cảnh & Căn nguyên Kỹ thuật

Khi vận hành cụm AI Agent cho Phone Farm, việc tối ưu chi phí và hạn ngạch (quota) đòi hỏi phân định rõ ràng giữa hai tầng:
1. **Tầng API IDE (Antigravity CLI / `agy`):** Sử dụng OAuth token của Google Cloud Code / Gemini Code Assist. Đây là API chính ngạch có hạn ngạch theo tài khoản (RPM/TPM).
2. **Tầng Giao Diện Web (`gemini-web` qua OmniRoute :20129):** Kết nối trực tiếp vào `https://gemini.google.com/app`. Sử dụng cookie phiên duyệt web (`__Secure-1PSID`, `__Secure-1PSIDTS`, `__Secure-1PSIDCC`). Tầng này **hoàn toàn miễn phí 100%**, không tiêu tốn hạn mức quota IDE của 22 tài khoản Pro.

---

## 1. Kỷ Luật Chủ Động Tuyệt Đối (Anti-Luna Proactive Invariant)

### Bẫy Thoái Thác Công Việc Cho Người Dùng:
- **Hiện tượng vi phạm:** Khi cần cookie web, Coordinator dừng lại hỏi người dùng: *"Anh vào F12 copy cookie..."* hoặc *"Em mở profile lên anh vào gõ mật khẩu..."*.
- **Quy tắc bất di bất dịch:** CẤM TUYỆT ĐỐI đẩy việc thao tác trình duyệt cho người dùng khi GPMLogin v3 Local API (:19995) và Chrome DevTools Protocol (CDP) có thể tự động làm 100%.
- **Quy trình tự động hóa CDP:**
  1. Quét O(1) file SQLite `Cookies` của GPMLogin tại `C:/Users/Kibe/AppData/Local/Programs/GPMLogin/profile/{profile_path}/Default/Network/Cookies` để tìm profile có sẵn session Google (`__Secure-1PSID`).
  2. Khởi động profile GPM ngầm qua `GET http://127.0.0.1:19995/api/v3/profiles/start/{id}` lấy `remote_debugging_address`.
  3. Kết nối WebSocket CDP (lưu ý: `suppress_origin=True` để tránh lỗi 403 Forbidden).
  4. Gửi lệnh `Storage.getCookies` để bóc tách trọn vẹn bộ 3 cookies: `__Secure-1PSID`, `__Secure-1PSIDTS`, `__Secure-1PSIDCC`.
  5. Dừng profile qua `GET http://127.0.0.1:19995/api/v3/profiles/stop/{id}` và dùng `psutil` kill sạch tiến trình mồ côi `gpm_browser_chromium_core.exe`.

---

## 2. Nạp Connection `gemini-web` Vào OmniRoute (:20129) Kèm Proxy 1-1

### A. Tạo Connection trong OmniRoute:
Gửi request `POST http://127.0.0.1:20129/api/providers`:
```json
{
  "name": "dokieu04092004@gmail.com (Pro Web)",
  "provider": "gemini-web",
  "email": "dokieu04092004@gmail.com",
  "apiKey": "__Secure-1PSID=...; __Secure-1PSIDTS=...; __Secure-1PSIDCC=...",
  "isActive": true,
  "providerSpecificData": {
    "cookie": "__Secure-1PSID=...; __Secure-1PSIDTS=...",
    "proxy": "http://mobi11:TaadaaMobi%232026%21@test.taadaa.click:5111",
    "tier": "g1-pro-tier",
    "plan": "Pro"
  }
}
```

### B. Gán Cố Định Proxy Egress:
Thêm bản ghi vào bảng `proxy_assignments` trong `C:\Users\Kibe\.omniroute\storage.sqlite`:
```sql
INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at)
VALUES ('<proxy_uuid>', 'connection', '<connection_id>', 0, datetime('now'), datetime('now'));
```

### C. Tạo Combo Routing:
Tạo combo `gemini-web-pro` (qua `POST /api/combos`) trỏ vào model `gemini-web/gemini-3.1-pro`.

---

## 3. Phân Vai Chuẩn: `sol_repair.py` vs `sol_worker.py` Trong Hệ Thống

| Tiêu chí | `sol_repair.py` (Closeout Gate) | `sol_worker.py` (Autonomous Worker) |
| :--- | :--- | :--- |
| **Bản chất** | **Read-Only Patch Proposal Generator** | **Multi-Turn Autonomous ReAct Worker** |
| **Tương tác đĩa** | CẤM sửa file trực tiếp. Chỉ sinh JSON proposal có AST check. | Tự động thực thi ReAct: READ_FILE -> PATCH -> COMMAND -> DONE. |
| **Ngân sách code** | Cứng $O(1) \le 30$ dòng diff theo đúng nhận xét Reviewer. | Tối đa 8 turns, tự chạy test suite kiểm chứng. |
| **Phân vai sử dụng** | **Độc quyền cho Strike 1 & 2** khi Closeout Gate bị Rejected. | **Routine tasks** hoặc **tầng dự phòng cứu sinh thứ 3** khi Claude CLI và Agy CLI cạn quota. |

---

## 4. Claude CLI Quota Stale-Gate Prevention

- **Nguyên nhân:** File `plan-usage-history.json` bị cũ quá 2 giờ (`MAX_QUOTA_STALE_HOURS = 2.0`), hàm `get_claude_quota_status()` trong `claude_worker.py` đánh giá nhầm là `is_stale = True` và từ chối điều phối dù quota còn >90%.
- **Khắc phục:** Thiết lập Cronjob chu kỳ 30 phút (`refresh-claude-quota-watchdog`) chạy `python D:/Taadaa/tools/refresh_claude_quota_file.py` để giữ dữ liệu lịch sử usage luôn tươi mới.
