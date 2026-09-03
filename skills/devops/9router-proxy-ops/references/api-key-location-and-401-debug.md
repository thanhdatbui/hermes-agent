# 9router API key: nơi lưu + debug 401 (verified 2026-08-17)

## Key nằm ở đâu

- **Active API key cho remote access lưu trong sqlite**: `~/AppData/Roaming/9router/db/data.sqlite`,
  bảng `apiKeys`, dòng `isActive=1`, cột `key` (vd `sk-247...6f2a`, dạng sk-...).
  Thêm cột `machineId` cùng hàng. Bảng thay đổi schema theo version (đừng hardcode
  tên cột — chạy `PRAGMA table_info(apiKeys)` trước nếu `key_prefix` báo lỗi).
- Query nhanh:
  ```bash
  python - <<'PY'
  import sqlite3, os
  c = sqlite3.connect(os.path.expanduser(r'~\AppData\Roaming\9router\db\data.sqlite'))
  row = c.execute("SELECT key, machineId FROM apiKeys WHERE isActive=1").fetchone()
  print(row[0] if row else None)
  PY
  ```
- Env `NINEROUTER_API_KEY` phải KHỚP key active trong db. Verify server nhận key:
  `curl -s -m 8 http://127.0.0.1:20128/v1/models -H "Authorization: Bearer $NINEROUTER_API_KEY"`
  → 200 OK; `Bearer dummy` → 401 `{"error":"API key required for remote API access"}`.

## Bẫy: gateway Hermes thiếu key → LLM cron job 401

- Gateway service chạy qua `~/AppData/Local/hermes/gateway-service/Hermes_Gateway.vbs`
  chỉ set `HERMES_HOME/PYTHONIOENCODING/HERMES_GATEWAY_DETACHED/VIRTUAL_ENV/PYTHONPATH`
  — KHÔNG kế thừa `NINEROUTER_API_KEY` từ shell tương tác ⇒ mọi session/cron spawn từ
  gateway process không có key ⇒ LLM-mode cron job qua `custom:9router` fail 401.
- Session Hermes tương tác (CLI từ bash) có key từ shell env → hoạt động bình thường.
  Đừng kết luận "9router chết" khi chỉ cron 401 — test bằng curl trước.
- Fix ưu tiên: chuyển cron job sang **no_agent script-only** (0 token, 0 key) — pattern
  chuẩn farm này. Chỉ khi bắt buộc LLM cron mới thêm `env.Item("NINEROUTER_API_KEY")`
  vào VBS + restart gateway (cần user duyệt vì đụng gateway; không restart khi batch live).
- Auth cũ hơn: `~/AppData/Roaming/9router/auth/cli-secret` (hex 64) là CLI secret,
  KHÔNG phải API key remote access.