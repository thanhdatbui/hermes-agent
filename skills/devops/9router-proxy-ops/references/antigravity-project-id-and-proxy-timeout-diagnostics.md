# 9Router Antigravity Diagnostics & Proxy Attachment Quirks (2026-08-20)

## 1. Lỗi Console Log: `[ProjectId] onboardUser failed after 5 attempts: onboardUser done but no project_id in response`
### Hiện tượng:
- Console log của 9Router ghi nhận lỗi đỏ lặp lại:
  `[ProjectId] onboardUser attempt 1 failed: onboardUser done but no project_id in response, retrying...`
  `[ProjectId] could not fetch projectId for connection <connection_id>`
### Nguyên nhân:
- 9Router tự động kích hoạt tiến trình nền `onboardUser` khi refresh token Google/Antigravity để tìm `project_id` trên Google Cloud Code Assist.
- Nếu tài khoản Google OAuth đó chưa tạo Cloud Project hoặc bị Google giới hạn quyền cá nhân, response trả về HTTP 200 nhưng trường `project_id` rỗng (`null`).
- 9Router retry 5 lần rồi ghi nhận lỗi connection đó.
### Ảnh hưởng & Cách xử lý:
- Các connection khác đã có `projectId` (ví dụ `rich-aria-16shk`, `phrasal-gamma-xnn32`) vẫn nhận request gọi API bình thường.
- Với các connection bị lỗi: Vào **Providers > Antigravity** bấm Re-auth / Login lại tài khoản Google, hoặc bấm xoá Connection nếu tài khoản không còn sử dụng.

---

## 2. Lỗi Connection: `Proxy test timed out` / `502 Bad Gateway`
### Hiện tượng:
- Trên UI 9Router (Providers > Antigravity hoặc Proxy Pools), trạng thái proxy bị đỏ: `failed: Proxy test timed out` hoặc `HTTP Error 502: Bad Gateway`.
- Các provider gán proxy pool (Antigravity, OpenAI-compatible) không gửi được request qua proxy.
### Quy trình chẩn đoán hạ tầng:
1. **Kiểm tra DNS & Ping domain proxy:**
   - Kiểm tra `test.taadaa.click` xem DDNS có cập nhật đúng Public IP WAN mới hay không (tránh trường hợp Box mạng vừa reset IP WAN nhưng DDNS chưa cập nhật).
2. **Kiểm tra Port liveness:**
   - Scan cổng proxy HTTP (5101–5138). Nếu port mở nhưng test `api.ipify.org` trả về 502/Timeout, kiểm tra target URL kiểm tra.
3. **Cơ chế xác thực Proxy của Box MobiProxy:**
   - Format URL chuẩn trong 9Router DB (`%APPDATA%\9router\db\data.sqlite`):
     `http://mobi{X}:TaadaaMobi%232026%21@test.taadaa.click:51{XX}/`
   - Ký tự đặc biệt trong password (`#` và `!`) **bắt buộc phải URL-encode** thành `%23` và `%21`.
4. **Kích hoạt lại trạng thái Proxy Pools trong 9Router sau sự cố:**
   - Sau khi Box proxy online trở lại, 9Router có thể vẫn giữ trạng thái `testStatus = 'error'` / `isActive = 0`.
   - Có thể kích hoạt lại nhanh trực tiếp qua SQLite DB:
     ```python
     import sqlite3, json, os, datetime
     db_path = os.path.expandvars(r'%APPDATA%\9router\db\data.sqlite')
     conn = sqlite3.connect(db_path)
     now = datetime.datetime.now(datetime.timezone.utc).isoformat()
     cur = conn.cursor()
     cur.execute('SELECT id, data FROM proxyPools WHERE data LIKE "%test.taadaa.click%"')
     for pid, d_str in cur.fetchall():
         d = json.loads(d_str)
         d['lastTestedAt'] = now
         d['lastError'] = None
         cur.execute('UPDATE proxyPools SET isActive = 1, testStatus = "active", data = ?, updatedAt = ? WHERE id = ?', (json.dumps(d), now, pid))
     conn.commit()
     ```
