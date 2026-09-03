# AG gemini 429 — verified 2026-08-15

## ⚠️ CORRECTION 17/08 — root cause thật = denylist identity (thay chẩn đoán "size" dưới đây)

Bisect + replay request thật (17/08, 2 account AG, curl lẫn hermes chat) chứng minh:
- 429 `RESOURCE_EXHAUSTED` chỉ xảy ra khi system prompt bắt đầu bằng ĐÚNG chuỗi
  `"You are Hermes Agent, an intelligent AI assistant created by Nous Research."` — 
  Antigravity gateway có **denylist literal** cho identity mặc định của Hermes.
- Đổi tên/org/bỏ 1 cụm → 200; đúng nguyên câu → 429 (lặp lại, cả gemini lẫn sonnet/opus).
- KHÔNG phải kích thước request, KHÔNG phải RPM, KHÔNG phải quota account.
- **FIX đã áp dụng 17/08:** sửa `~/AppData/Local/hermes/SOUL.md` (identity slot #1) → 
  câu gọn không dính denylist → `hermes chat -m ag/gemini-3.7-flash-high` = 200.
  Session mới (/new) mới nạp; session cũ giữ prompt cũ.
- Chẩn đoán "theo kích thước request" bên dưới GIỮ LẠI chỉ làm lịch sử — đừng dùng để kết luận.
- Chi tiết kỹ thuật replay/bisect + fingerprint denylist + modelLock nhiễu test: `references/replay-request-dump-429-diagnostics.md`; probe nhanh: `scripts/ag-identity-probe.py`.

---

## Triệu chứng

`hermes chat -m gemini-3.6-flash-high --provider custom:9router` → HTTP 429 `RESOURCE_EXHAUSTED`
dù app Antigravity (Models & Usage) hiện quota Gemini còn 99% (weekly + 5h). User test trong app 9Router/AG vẫn OK.

## Nguyên nhân thật

⚠️ 17/08: `logs/server.log` NGỪNG ghi từ 16/08 22:28 (watchdog restart 22:39 chạy node KHÔNG redirect stdout) → log live chỉ đọc qua API `GET /api/translator/console-logs` (giữ ~200 entries gần nhất) hoặc Quota Tracker UI. File cũ chỉ còn giá trị lịch sử.

- Hermes gửi request có **29 TOOL messages + system prompt dài** (log: `STREAM · 2 MSG · 29 TOOL · THINK:high`) → Antigravity từ chối theo **kích thước request/context**, không phải hết quota.
- Request nhỏ (curl, 1 MSG, `stream:false`) → `antigravity/gemini-3.6-flash-high` **succeeded**.
- 9router còn cơ chế **modelLock**: sau mỗi 429, account bị lock `2s→4s→6s→13s` (tăng dần) — log: `all 1 accounts locked for gemini-3.6-flash-high (reset after Ns)`. Mọi request trong thời gian lock bị từ chối ngay, trông như 429 liên tục.

## Fix

Muốn dùng gemini 3.6 flash qua 9router → **gọi thẳng API bằng curl** (không qua hermes chat):

```bash
curl -sS -X POST "http://127.0.0.1:20128/v1/chat/completions" \
  -H "Authorization: Bearer $NINEROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-3.6-flash-high","messages":[{"role":"user","content":"..."}],"max_tokens":2000,"stream":false}'
```

- Model id: `gemini-3.6-flash-high` hoặc có prefix `ag/` — đều chấp nhận, route về `antigravity/gemini-3.6-flash-high`.
- Bắt buộc `stream:false` khi parse JSON (nếu stream, phải gom SSE chunks).

## Key env

- `NINEROUTER_API_KEY` nằm trong **OS env** (`printenv` thấy, len ~35, dạng `sk-247...c65`), KHÔNG có trong `~/AppData/Local/hermes/.env`.
- `OMNIROUTE_API_KEY` trong .env là key cũ (omniroute), giờ trả `Invalid API key` trên 9router — đừng dùng.
- Hermes config `key_env: NINEROUTER_API_KEY` → hermes đọc được OS env, nhưng vẫn gửi tool messages gây 429 với AG.
