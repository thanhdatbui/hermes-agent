# OmniRoute / 9Router: Connection-Test & Health-Check Log Flooding

## Hiện tượng
Trong giao diện Request Logs (`/dashboard/logs`) hoặc Recent Requests của OmniRoute (`:20129`), bảng log bị ngập tràn hàng loạt bản ghi liên tục:
```text
200 | UPSTREAM | connection-test | -
```
(Status 200, Route UPSTREAM, Model `connection-test`, Path `/api/providers/test`).

## Nguyên nhân
- OmniRoute / 9Router chạy cơ chế định kỳ probe hoặc test connection để kiểm tra sức khỏe của các token/account trong provider pools (đặc biệt là Antigravity, OAuth, ChatGPT Web...).
- Khi probe thành công, hàm test kết nối gọi `saveCallLog()` với:
  - `path: "/api/providers/test"`
  - `model: "connection-test"`
  - `sourceFormat: "test"`, `targetFormat: "test"`
- Mặc định cài đặt hệ thống `hideHealthCheckLogs` là `false`, khiến mọi lượt probe này được lưu vào SQLite table `call_logs` và hiển thị trực tiếp lên bảng Request Logs.

## Giải pháp

### 1. Tắt vĩnh viễn ghi log connection-test vào DB (Cấu hình hệ thống)
- **Qua UI**: Vào `Settings` ➔ tab `Appearance` ➔ tìm `Hide Health Check Logs` (hoặc `Ẩn nhật ký kiểm tra sức khỏe`) ➔ chuyển sang **ON (Bật)**.
- **Cơ chế code**: Khi bật cờ này, trường `hideHealthCheckLogs` trong bảng `settings` được set `true`. Hàm `shouldHideLogs()` trong `src/lib/tokenHealthCheck.ts` sẽ return `true`, chặn `saveCallLog()` ghi `connection-test` vào `call_logs`.
- **Qua API / Environment Variable**:
  - Đặt biến môi trường: `OMNIROUTE_HIDE_HEALTHCHECK_LOGS=1`
  - Hoặc PATCH settings qua API:
    ```bash
    curl -X PATCH http://127.0.0.1:20129/api/settings \
      -H "Content-Type: application/json" \
      -d '{"hideHealthCheckLogs": true}'
    ```

### 2. Lọc nhanh khi quan sát UI Request Logs
- **Ô Search**: Nhập `/v1/` hoặc tên model cụ thể (`gemini`, `flash`, `gpt`...). Bảng sẽ lọc trực tiếp theo query và ẩn các bản ghi management/test.
- **Dropdown Filter**: Chọn model chỉ định thay vì để `All Models`.

### 3. Tẩy dọn log test cũ tích tụ trong SQLite
- Nhấn **Clean History** trên góc phải trang `/dashboard/logs`.
- Hoặc vào **Settings** ➔ tab **Storage** ➔ nhấn **Purge Call Logs** (`POST /api/settings/purge-call-logs`).
