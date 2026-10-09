# OmniRoute Call-Logs Noise Suppression & Purge Ops

## Triệu chứng
Bảng Request Logs (`/dashboard/logs` trên port 20129) bị tràn ngập hàng ngàn dòng log kiểm tra kết nối tự động:
- `200 | UPSTREAM | connection-test` (path: `/api/providers/test`)
- Làm loãng, khó debug và theo dõi các request inference LLM thật (`/v1/chat/completions`).

## Cơ chế hoạt động của OmniRoute
1. Khi chạy probe connection test định kỳ hoặc bấm kiểm tra kết nối tài khoản (`POST /api/providers/[id]/test`), hàm `shouldHideLogs()` trong `src/lib/tokenHealthCheck.ts` sẽ kiểm tra cờ:
   - Biến môi trường: `OMNIROUTE_HIDE_HEALTHCHECK_LOGS`
   - Cấu hình KV database: `settings.hideHealthCheckLogs`
2. Nếu `hideHealthCheckLogs === false` (mặc định), `saveCallLog` ghi lại một dòng `model: "connection-test"` vào bảng `call_logs`.
3. Khi `hideHealthCheckLogs === true`, OmniRoute tự động bỏ qua (skip) không ghi các bản ghi probe test này vào database.

## Cách xử lý chuẩn (Runtime + Dọn rác)

### 1. Kích hoạt chặn log test vĩnh viễn (Runtime PATCH)
Không cần sửa code, gọi trực tiếp API cấu hình của OmniRoute:
```bash
curl -s -X PATCH "http://127.0.0.1:20129/api/settings" \
  -H "Content-Type: application/json" \
  -d '{"hideHealthCheckLogs": true}'
```
*Giao diện UI:* Menu **Settings** ➔ tab **Appearance** ➔ bật switch **"Hide Health Check Logs"** (hoặc *Ẩn nhật ký kiểm tra sức khỏe*).

### 2. Dọn sạch toàn bộ log test và call logs rác tích tụ
OmniRoute cung cấp endpoint chuyên dụng dọn sạch request history & artifacts:
```bash
curl -s -X POST "http://127.0.0.1:20129/api/settings/purge-request-history" \
  -H "Content-Type: application/json"
```
Kết quả trả về sẽ báo số lượng bản ghi `call_logs` và JSON artifacts bị xóa:
```json
{"deleted": 100019, "deletedArtifacts": 10010, "deletedDetailedLogs": 0, "errors": 0}
```

### 3. Đồng bộ & Sao lưu cấu hình
Mỗi khi thay đổi cấu hình OmniRoute trong phiên, luôn đồng bộ về repo `D:/Taadaa/AI-Tools/tools/omniroute/`:
```bash
# Xuất snapshot settings
curl -s http://127.0.0.1:20129/api/settings | python -m json.tool > "D:/Taadaa/AI-Tools/tools/omniroute/settings_backup.json"

# Xuất snapshot combos
curl -s http://127.0.0.1:20129/api/combos | python -m json.tool > "D:/Taadaa/AI-Tools/tools/omniroute/combos_backup.json"

# Sao lưu DB sqlite
powershell -Command "Copy-Item 'C:\Users\Kibe\AppData\Roaming\omniroute\storage.sqlite' 'D:\Taadaa\AI-Tools\tools\omniroute\storage.sqlite.bak'"
```
