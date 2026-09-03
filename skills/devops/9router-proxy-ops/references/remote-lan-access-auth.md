# 9Router remote (LAN) access auth — mechanism & cross-machine sharing

## Symptom
POST tới `http://<lan-ip>:20128/v1/chat/completions` từ máy KHÁC trả:
```
{"error":"API key required for remote API access"}
```
(request từ localhost vẫn đi thẳng — lỗi chỉ xuất hiện khi gọi qua LAN IP).

## Middleware logic (decode từ minified source)
Nguồn bundle: `%TEMP%\9router-pkg\package\app\.next-cli-build\server\middleware.js`
- Path prefixes bắt buộc key khi request remote: `/v1`, `/v1beta`, `/api/v1`, `/api/v1beta`, `/codex`.
- Key được nhận theo thứ tự: `Authorization: Bearer <key>` → header `x-api-key` → header `x-goog-api-key` → query `?key=`.
- Validate = `SELECT isActive FROM apiKeys WHERE key = ?` trên SQLite — **CHỈ check isActive=1, KHÔNG bind machineId** → một key dùng chung nhiều máy được.
- **Dummy key LUÔN fail** (không có row nào khớp trong bảng apiKeys). Đặt `'***'` làm env var không đủ — phải dùng key thật hoặc INSERT row mới.

## Key nằm ở đâu
- DB thật: `%APPDATA%\9router\db\data.sqlite` (~77MB). Bảng `apiKeys(id, key, name, machineId, isActive, createdAt)`.
- ⚠️ `%APPDATA%\9router\9router.db` là placeholder **0 byte** — đọc nhầm file này sẽ thấy [] tables và kết luận sai.
- Key đang hoạt động: name `codex-local`, isActive 1 (lấy full giá trị cột `key`).

## Đọc DB khi server đang giữ lock
- Dùng read-only URI: `sqlite3.connect('file:C:/Users/Kibe/AppData/Roaming/9router/db/data.sqlite?mode=ro', uri=True)`.
- Connect thường (không mode=ro) vào DB thật trả về [] tables; fallback: copy file ra Temp rồi đọc bản copy.

## Recipe chia sẻ 9Router cho máy thứ 2 (client Hermes)
1. Lấy key thật từ bảng `apiKeys` (hoặc tạo mới: id=uuid4, name tự đặt, key `sk-...`, machineId, isActive=1, createdAt ISO — server có helper `generateApiKeyWithMachine`).
2. Tìm IP LAN máy chủ: `ipconfig` → Ethernet adapter IPv4 (vd `192.168.110.123`).
3. Trên máy client:
   ```powershell
   hermes config set custom_providers '[{"name": "9router", "base_url": "http://<IP>:20128/v1", "key_env": "NINEROUTER_API_KEY", "api_mode": "chat_completions", "discover_models": false, "model": "worker"}]'
   hermes config set model.provider "custom:9router"
   hermes config set model.default "ag/gemini-3.7-flash-high"
   # vision
   hermes config set auxiliary.vision.provider "custom:9router"
   hermes config set auxiliary.vision.model "ag/gemini-3.7-flash-low"
   hermes config set auxiliary.vision.base_url "http://<IP>:20128/v1"
   # key (PowerShell MỚI sau khi set để env ăn)
   [System.Environment]::SetEnvironmentVariable('NINEROUTER_API_KEY','sk-...','User')
   ```
   ⚠️ `auxiliary.vision.key_env` in warning "not a recognized config key" nhưng vẫn được lưu — vô hại, bỏ qua.
4. Verify từ client:
   ```
   curl -X POST http://<IP>:20128/v1/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer $KEY" -d '{"model":"worker","messages":[{"role":"user","content":"say ok"}],"max_tokens":5}'
   ```
   → JSON `chat.completion` = OK. Response có thể kèm `data: [DONE]` suffix (stream marker) — bình thường.

## Server process discovery (trên máy chủ)
- `netstat -ano | findstr :20128` → PID listener (0.0.0.0:20128).
- `(Get-CimInstance Win32_Process -Filter "ProcessId=<pid>").CommandLine` → `node.exe ... server.js`; owner qua `Invoke-CimMethod GetOwner`.
- Cwd không lộ qua WMI — nếu cần decode thêm logic, dùng bundle tại `%TEMP%\9router-pkg`.
