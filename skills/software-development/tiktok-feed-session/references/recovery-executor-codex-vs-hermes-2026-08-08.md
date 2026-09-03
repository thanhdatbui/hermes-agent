# Recovery executor diagnosis — Codex CLI vs Hermes fallback (2026-08-08)

Session: user hỏi "auto recovery hôm nay chạy qua codex hay fallback qua hermes?"
Kết luận: **bắt đầu qua Codex CLI, máy 15 đã fallback Hermes và đang chạy live.**

## Nguồn sự thật (file paths)

- **Ledger chính:** `python_runner/runs/schedule-recovery-ledger.jsonl` (KHÔNG phải `runs/schedule-recovery-task.log`
  — file đó chỉ là poll heartbeat `{"observed_at":..., "outcomes":[]}`, vô hồn khi muốn biết executor).
- **Scheduler shifts:** `python_runner/runs/scheduler.jsonl` + `scheduler-state.json`.
- **Incident artifacts:** `.ai-runs/schedule-recovery/<INCIDENT_KEY>/slot-N/` — mỗi slot có
  `repair-output.txt` (header cho biết executor), `advisor-output.txt`, `advisor-plan.txt`,
  `repair-schema.json`, `deepseek-executor-result.json`.
- **Process live:** `wmic process where "name like '%python%'" get ProcessId,CommandLine` (PowerShell qua
  git-bash: `$_` bị nuốt → ghi script .ps1 ra `C:\Users\Kibe\AppData\Local\Temp` rồi `powershell -File`,
  hoặc bọc single quotes).

## Chuỗi event cho biết executor

Ledger event (theo thứ tự):
1. `DETECTED` → `CLASSIFIED` → `AUTO_RECOVERY_PENDING`
2. `ADVISOR_RESERVED`/`ADVISOR` (model `gpt-5.6-sol`, effort high/xhigh) — advisor Codex
3. `PATCH_ATTEMPT_RESERVED` (model `gpt-5.6-luna`, effort max) — repair Codex
4. `REPAIR_NOT_READY` — lặp lại nhiều lần
5. `LUNA_PROVIDER_UNAVAILABLE` → `PROVIDER_MODE_ACTIVATED` với `provider_mode=deepseek_executor` — **đây là lúc fallback Hermes kích hoạt**
6. `PATCH_ATTEMPT_RESERVED` (model `cmc/deepseek/deepseek-v4-flash` → `cmc/deepseek/deepseek-v4-pro`) + `DEEPSEEK_EXECUTOR_RESULT` + `DEEPSEEK_FALLBACK` + `DEEPSEEK_EXECUTOR_NOT_READY` — ladder Hermes

Phân biệt executor qua artifact:
- `repair-output.txt` bắt đầu `OpenAI Codex v0.145.0 ... provider: codex_local_access ... model: gpt-5.6-luna` = Codex CLI.
- Hermes: process `hermes.exe -z "<prompt>" -m cmc/deepseek/deepseek-v4-pro --provider 9router` (path
  `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe`), stdout-only, không `--output-schema`.
- `deepseek-executor-result.json` rỗng (`{"action":"","decision":"",...}`) = Hermes result NOT_READY — NHƯNG
  **không có nghĩa Hermes "không chạy"** (xem section "Hermes CÓ chạy" bên dưới).

## Hermes CÓ chạy — fail vì KHÔNG qua được gate decision, không phải "không được gọi" (chẩn đoán 08-08 chiều)

User hỏi "codex fail rồi mà sao hermes cũng k chạy" → ledger cho thấy Hermes ĐƯỢC GỌI thật:
`provider_mode=deepseek_executor` xuất hiện 212 lần, model flash 36 lần + pro 206 lần trong
`schedule-recovery-ledger.jsonl`. Mọi slot kết thúc `DEEPSEEK_EXECUTOR_NOT_READY` / `NOT_READY`
reason=`structured-patch-decision-required` vì result không đạt enum gate, KHÔNG phải vì Hermes im lặng.
Hai lý do phân biệt được qua artifact slot:

1. **`decision: "IN_PROGRESS"` bị enum reject (slot-3 morning máy 15).** `deepseek-executor-result.json`
   slot-3 CÓ nội dung đầy đủ (hypothesis/evidence/action/tests/verifier) nhưng `decision=IN_PROGRESS` —
   schema `repair-schema.json` chỉ chấp nhận `PATCH_READY`/`NO_SAFE_PATCH` → runtime ghi
   `DEEPSEEK_EXECUTOR_NOT_READY reason=structured-patch-decision-required`. Đây là lỗi worker trả sai enum,
   không phải lỗi transport/quota.
2. **Output PATCH_READY đầy đủ nhưng parse fail vì encoding mojibake (slot-4).** `repair-output.txt`
   chứa JSON PATCH_READY hợp lệ về cấu trúc NHƯNG tiếng Việt bị vỡ (`TÃ´i Ä‘Ã£...` = UTF-8 đọc nhầm
   Latin-1/cp1252) → `_json_object` (recovery_runtime.py ~L703, qua `_run_capture` `text=True, errors="replace"`)
   không parse được → `deepseek-executor-result.json` = rỗng → `decision:""` → NOT_READY.

Chẩn đoán nhanh 1 slot NOT_READY: đọc CẢ HAI file
- `slot-N/deepseek-executor-result.json` — rỗng = parse fail (mojibake); có nội dung nhưng decision≠PATCH_READY = enum reject.
- `slot-N/repair-output.txt` — grep `TÃ´i|Ä‘Ã£|Ä�` = encoding vỡ; grep `invalid_json_schema|oneOf` = schema reject.

## Watcher log — lọc noise để thấy sự kiện thật

`runs/schedule-recovery-task.log` là poll heartbeat ~16s/lần, đa số chỉ `{"outcomes":["noon:already-terminal"]}`
(sau khi shift terminal, watcher lặp vô hạn cùng outcome). Lọc để thấy sự kiện thật:
```bash
grep -v '"outcomes": \["noon:already-terminal"\]' runs/schedule-recovery-task.log | tail -40
```
Toàn bộ log chỉ còn `already-terminal`/`[]` = incident ĐÃ đóng băng (terminal), KHÔNG phải đang recovery.
Sự kiện thật nằm trong `schedule-recovery-ledger.jsonl`, không phải file log poll.

## Incident schedule-level: NO_HANDLER_IMPLEMENTED ≠ lỗi máy

Noon 08-08: `SCHEDULE_TERMINAL (incident_key=schedule:2026-08-08:noon:4, status=failed)` →
`FINAL_BLOCKED reason=NO_HANDLER_IMPLEMENTED` — schedule-level incident (không phải per-machine) kết thúc
bằng NO_HANDLER_IMPLEMENTED khi không có handler đăng ký cho signature schedule đó, rồi watcher lặp
`already-terminal` mãi. Đừng retry mù hay đổ lỗi executor khi thấy pattern này.

## PITFALL chính: schema `oneOf` làm Codex repair fail toàn bộ (158× REPAIR_NOT_READY)

`_repair_with_codex` (recovery_runtime.py ~L2205) viết `repair-schema.json` với:
```json
"evidence": {"oneOf": [{"type":"object","minProperties":1},{"type":"array","minItems":1,...}]}
```
API Codex từ chối: `invalid_request_error: Invalid schema for response_format 'codex_output_schema':
In context=('properties','evidence'), 'oneOf' is not permitted.`
→ không slot nào ra patch decision → 7/8 máy `FINAL_BLOCKED` + `MANUAL_REQUIRED` dù advisor chẩn đoán đúng.
Fallback Hermes chỉ kích hoạt ở máy cuối (15) khi `LUNA_PROVIDER_UNAVAILABLE` được ghi.

Fix đề xuất: bỏ `oneOf` → `{"type": ["object","array"]}` hoặc chỉ `{"type":"object"}`; test parser chấp nhận.

## Kết quả 08-08 (MORNING, run 20260808-060009)

- 8 máy VICHANGER_VPN: 2, 4, 5, 9, 10, 11, 12, 15 (account_row 6).
- Máy 2-12: Codex repair fail (schema) → FINAL_BLOCKED + MANUAL_REQUIRED (~07:13-07:34 +07).
- Máy 15: PROVIDER_MODE_ACTIVATED 07:42 → DEEPSEEK_FALLBACK 08:09 → hermes.exe chạy
  `cmc/deepseek/deepseek-v4-pro` slot-2 (PID thấy trong wmic, start 08:09:20).
- Root cause thật của signature (advisor + repair worker đều chốt): lỗi preflight đọc
  `PROXYgandienthoai.xlsx` bị `_run_child` catch-all gán nhầm thành `blocked-vichanger-vpn`
  (xem SKILL.md mục 3b).
