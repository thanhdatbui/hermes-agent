# OmniRoute Pool Healer Proactive Recovery & Closeout Evidence Standards

> Associated Skill: `farm-alert-autonomous-recovery`

---

## 1. Anti-Passive Quarantine Trap (Chống Thói Quen Thụ Động Cô Lập Thay Vì Cứu Acc)

### Triết lý Vận hành:
Khi nhận Farm Alert hoặc Watchdog Alert về pool tài khoản OmniRoute (ChatGPT-Web, Codex, Antigravity), **CẤM TUYỆT ĐỐI** Agent chỉ đọc log, set `is_active = 0` rồi dừng lại phân trần / báo cáo cho có lệ. Người dùng yêu cầu cơ chế **Auto-heal 100% tự sửa ngầm**:
- Xác định nguyên nhân gốc rễ và cứu sống ngay các tài khoản có thể cứu được.
- Đưa ngay tài khoản về trạng thái phục vụ lưu lượng (`is_active = 1, test_status = 'active'`).
- Chỉ cô lập những tài khoản thực sự bị upstream ban hoặc hỏng không thể cứu, và phải có bằng chứng giải mã xác thực.

### Quy trình 4 Bước Triage & Cứu Sống Ngay Lập Tức:

1. **Đối soát tầng Proxy trước khi phán xét Token:**
   - Kiểm tra bảng `proxy_registry` trong `storage.sqlite` xem proxy có bị thiếu credentials (ví dụ MikroTik port 10006 thiếu `username/password = admin@1:admin@1`), hoặc bị lỗi transient 502 Bad Gateway / Connection Reset.
   - Sửa ngay credentials proxy bị thiếu trong `proxy_registry`.

2. **Gọi Test Endpoint Trực Tiếp trên OmniRoute (`POST /api/providers/{cid}/test`):**
   - Nhiều tài khoản bị watchdog đánh dấu `EMPTY_SESSION_TOKEN` hoặc `failed` chỉ do mạng chập chờn nhất thời tại thời điểm cron chạy.
   - Kiểm tra trực tiếp qua API:
     ```python
     req = urllib.request.Request(f"http://127.0.0.1:20129/api/providers/{cid}/test", data=b"{}", headers={"Content-Type": "application/json"})
     res = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
     ```
   - Nếu `res.get('valid') is True`: Token hoàn toàn còn sống! Lập tức chạy query phục hồi:
     ```sql
     UPDATE provider_connections
     SET is_active = 1, test_status = 'active', last_error = NULL, last_error_at = NULL, backoff_level = 0, rate_limited_until = NULL
     WHERE id = ?;
     ```

3. **Kiểm tra Cookie Session Google SID trong GPM Profile:**
   - Với các tài khoản Codex OAuth bị 401 hoặc timeout đăng nhập, mở cookie database của GPM Profile ở chế độ read-only:
     ```python
     uri = f"file:{gpm_profile_cookie_db}?immutable=1"
     conn = sqlite3.connect(uri, uri=True)
     has_sid = len(conn.cursor().execute("SELECT name FROM cookies WHERE host_key LIKE '%google%' AND name = 'SID'").fetchall()) > 0
     ```
   - Nếu `has_sid is False`: Profile đã văng session Google. Phải phân loại rõ ràng cần bước Google Login (bằng TOTP/2FA tự động qua `post_evening_gpm_login_watchdog.py`) trước khi chạy Codex OAuth, tránh timeout vô ích.

4. **Giải mã Payload Upstream để Phân Loại Chính Xác:**
   - Khi OpenAI chuyển hướng về `auth.openai.com/error?payload=...`, trích xuất chuỗi base64 và giải mã:
     ```python
     payload_json = json.loads(base64.b64decode(payload + "==").decode("utf-8", errors="replace"))
     # e.g. {"errorCode": "account_deactivated"}
     ```
   - Phân loại rõ ràng:
     * `account_deactivated`: Upstream OpenAI đã khóa vĩnh viễn -> Quarantined vĩnh viễn (`is_active = 0, test_status = 'error'`).
     * `sentinel_turnstile_required`: Dải IP proxy bị Cloudflare challenge -> Tạm dừng định tuyến fail-closed, chuyển proxy hoặc chờ cooldown.
     * `session_expired`: Hết hạn session cookie -> Đưa vào hàng đợi tự động đăng nhập của GPM supervisor.

---

## 2. Tiêu Chuẩn Hồ Sơ Closeout Cho Tác Vụ Operational / Database Triage (Zero Code Diff)

Khi kết thúc phiên làm việc dạng vận hành/cứu database (không có git commit/diff mã nguồn), Closeout Gate yêu cầu bộ bằng chứng kiểm toán nghiêm ngặt để đạt điểm >= 85:

### A. Bộ Kiểm Thử Tự Động PyTest (Automated PyTest Regression Suite):
Bắt buộc tạo và chạy một file test độc lập (ví dụ `test_operational_health.py`), kiểm chứng trực tiếp bằng code assertions:
1. `PRAGMA journal_mode = wal` và `PRAGMA foreign_key_check` (0 violations).
2. Kiểm tra tính toàn vẹn và số lượng connection của từng pool (ChatGPT-Web, Antigravity, Codex).
3. Kiểm tra tính an toàn của các kết nối bị cô lập (tất cả kết nối lỗi bắt buộc có `is_active == 0`).
4. Kiểm tra HTTP status 200 của các dịch vụ cốt lõi (:20129, :19995, :20128).
5. Kiểm tra không có profile GPM nào bị rò rỉ hay kẹt chạy ngầm (`profiles/running`).

### B. Bảng Đối Soát Số Học 100% (Truth Matrix):
* Bắt buộc có phép cộng số học khớp tuyệt đối:
  $$\text{Active Connections} + \text{Quarantined Connections} = \text{Total Connections}$$
* Trích xuất verbatim output từ lệnh query SQL nhóm theo `is_active` và `test_status`.

### C. Tính Nhất Quán Trạng Thái (State Alignment Invariant):
* **CẤM TUYỆT ĐỐI mâu thuẫn trạng thái**: Tài khoản đã bị cô lập (`is_active = 0`) thì `test_status` bắt buộc phải phản ánh đúng nguyên nhân (`'error'` hoặc `'banned'`), tuyệt đối không được để sót `test_status = 'active'`.

### D. Bằng Chứng Phần Cứng Thực Tế:
* Đính kèm trích xuất nguyên bản từ `adb devices`, thống kê rõ số lượng máy `device` online và `offline`.
* Xác nhận 0 file lock bị kẹt trong thư mục runtime state.
