# Chẩn đoán executor path recovery (Codex CLI vs Hermes fallback) + 2 bug runtime + tiếng Việt

Bổ sung 2026-08-08 sau khi user hỏi "auto recovery hôm nay chạy qua codex hay fallback hermes".

## Trả lời nhanh câu "chạy qua Codex hay Hermes?" — 4 nguồn theo độ tin cậy

1. **Process sống** (tin nhất): `wmic process where "name='python.exe'" get ProcessId,CreationDate,CommandLine | grep -i "machine_\|bounded recovery"`
   - `hermes.exe -z "Act as the bounded recovery patch owner..." -m cmc/deepseek/deepseek-v4-pro --provider 9router` = **Hermes CLI fallback ĐANG chạy** (mỗi slot ladder = 1 process riêng, start ~08:58).
   - Output chứa `OpenAI Codex v0.145.0` / `provider: codex_local_access` = **Codex CLI**.
2. **Ledger** `python_runner/runs/schedule-recovery-ledger.jsonl` (KHÔNG nhầm với `runs/schedule-recovery-task.log` — file đó chỉ là poll log `{"observed_at", "outcomes": []}` 15s/lần, không có event chi tiết):
   - grep `PROVIDER_MODE_ACTIVATED` + `LUNA_PROVIDER_UNAVAILABLE` + `DEEPSEEK_FALLBACK` → fallback đã kích hoạt.
   - `REPAIR_NOT_READY`/`DEEPSEEK_EXECUTOR_NOT_READY` reason `structured-patch-decision-required` = worker có thể trả JSON hợp lệ nhưng runtime parse fail.
3. **Artifact header**: `.ai-runs/schedule-recovery/<incident>/slot-N/repair-output.txt` dòng đầu: header Codex = Codex CLI; không header + markdown-fenced JSON = Hermes CLI.
4. **So `repair-output.txt` vs `deepseek-executor-result.json`**: output có `"decision": "PATCH_READY"` đầy đủ nhưng result file toàn field rỗng (`{"action":"","decision":"",...}`) → **runtime parse fail, đang chạy code cũ trong memory → cần restart**.

⚠️ Timestamps: ledger `observed_at` là **UTC** (00:42 = 07:42 +07). Đừng grep theo ngày +07.

## Cơ chế fallback (nhắc lại để chẩn đoán đúng)

- `_repair_with_codex` → `code != 0` + output match `_QUOTA_MARKERS` → `PlannerResult.provider_unavailable(quota_exhausted)` → `ready_for_fallback` → `_activate_deepseek_executor_mode` → `_run_deepseek_executor_mode` (Hermes CLI ladder: flash/max → pro/high → pro/max, mỗi slot = 1 `hermes -z` mới).
- Repair fail vì lý do KHÁC (schema, parse) = `REPAIR_NOT_READY`/`DEEPSEEK_EXECUTOR_NOT_READY` — KHÔNG kích fallback; leo hết slot → `FINAL_BLOCKED`. **Lưu ý: fallback kích nhầm cũng có thể xảy ra** (bug 2 dưới).

## Bug 1 (2026-08-08): repair-schema `oneOf` bị Codex API từ chối — chết toàn bộ repair

- Triệu chứng: MỌI repair fail `ERROR: Invalid schema for response_format 'codex_output_schema': In context=('properties', 'evidence'), 'oneOf' is not permitted.` → 158× `REPAIR_NOT_READY` → 7/8 máy `FINAL_BLOCKED` dù advisor (Codex) chạy tốt và chỉ đúng root cause.
- Gốc: `_repair_with_codex` trong `python_runner/scheduler/recovery_runtime.py` viết `"evidence": {"oneOf": [{"type":"object"...},{"type":"array"...}]}` — **Codex structured-output API cấm `oneOf`**.
- Fix: `"evidence": {}` (empty schema — vẫn giữ `required`, chấp nhận cả object lẫn array). Không đụng constraint khác.
- Test đi kèm: assertion cũ đọc `["oneOf"][1]["items"]["type"]` trong `test_recovery_handlers.py` → đổi thành assert không có `oneOf`, bằng `{}`, và vẫn trong `required`.

## Bug 2 (2026-08-08): `_QUOTA_MARKERS` bare `429|403` false-positive → kích fallback nhầm

- Triệu chứng: máy 15 kích hoạt `PROVIDER_MODE_ACTIVATED` (deepseek_executor) dù Codex KHÔNG hết quota — output của Codex chứa `"source_row": 403` (số liệu artifact trong JSON echo) → regex `429|403` match bừa → `detect_provider_quota` trả `quota_exhausted`.
- Fix: thay `429|403` bằng `\b(?:HTTP|status|code)[ /:=]*[45][0-9]{2}\b` trong `_QUOTA_MARKERS` (`python_runner/scheduler/recovery_supervisor.py`) — chỉ match khi có context HTTP-status. Giữ nguyên các alternative khác.
- Test mới: `test_quota_status_codes_require_http_context` — bare `"source_row": 403` / `"processed 429 rows"` → `None`; `"HTTP 429"`, `"status: 403"`, `"code 429"` → có evidence.
- Bài học class: **regex quota/status-code phải yêu cầu context, không bao giờ match số trần** (số liệu artifact dễ chứa 403/429/500).

## User preference: worker recovery trả lời TIẾNG VIỆT (user: "xử lý phải trả kết quả tiếng việt để t còn đọc hiểu")

Đã thêm vào 4 prompt template trong `recovery_runtime.py` (`_repair_with_codex`, `_repair_with_hermes`, `_advise_with_codex`, `_advise_with_hermes`) — câu chốt:
> "Trả lời bằng tiếng Việt: viết toàn bộ phần phân tích, hypothesis, action và verifier bằng tiếng Việt; giữ nguyên các enum máy-đọc (PATCH_READY, NO_SAFE_PATCH, PROVIDER_UNAVAILABLE...), strategy_id, handler_id, tên file/test và các identifier bằng tiếng Anh; JSON cuối cùng phải hợp lệ theo schema."

Lưu ý: deepseek-v4-pro đã tự trả tiếng Việt theo AGENTS.md — prompt chỉ để chắc chắn 100%.

## Pitfall: KHÔNG gửi message vào CLI one-shot đang chạy được

- `hermes -z "<msg>" --resume <session_id>` → **output rỗng, không có hiệu lực**. Session CLI one-shot là process con của `recovery_runtime` (đọc prompt từ args), không nhận message xen giữa như session desktop interactive. Không có đường "chèn lệnh" vào worker đang chạy.
- `hermes -z` top-level KHÔNG nhận `-Q` (`unrecognized arguments`) — `-Q` chỉ có ở `hermes chat`.
- Muốn đổi hành vi worker giữa ladder: chỉ có **restart runtime** (nạp code mới). Restart giữa slot đang chạy để lại `LIVE_ATTEMPT_UNKNOWN_AFTER_CRASH` cho slot đó — cân nhắc timing (slot ~30 phút/lần).
- Cách theo dõi session worker thật: `session_search(query="Act as the bounded recovery patch owner machine_15", sort=newest)` → session_id, model, `bookend_end` cho thấy tiến độ / lý do kết thúc ("maximum number of tool-calling iterations allowed").

## Pitfall: đừng thả script inspect vào repo root (gây verification noise + user bực)

- Viết `_tmp_procs.ps1` vào repo root để query process → verify-tracker coi là "edited code" → tốn lượt verification, user bực ("m làm cái đéo gì thế" khi chỉ hỏi 1 câu status).
- Đúng: dùng inline `python - <<'EOF'` heredoc, hoặc `wmic`/`tasklist` trực tiếp, hoặc script dưới `%TEMP%` prefix `hermes-verify-` (rồi xóa). **Không bao giờ tạo file tạm trong working tree khi chỉ inspect read-only.**
- Khi user hỏi câu status đơn giản ("chạy qua codex hay hermes?"): trả lời verdict trực tiếp + bằng chứng tối thiểu (1 bảng nhỏ), đừng chạy verification script cho thay đổi không tồn tại.

## Restart runtime để nạp code mới

`recovery_runtime` chạy in-memory — patch file thôi KHÔNG đủ; ledger vẫn `structured-patch-decision-required` dù fix đã xong. Restart an toàn: task `TikTokScheduleRecovery` → watch ps1 → child (verify lease identity → stop child → watch tự exit → `schtasks /run` qua `cmd //c` → verify lease mới, không double-run). Chi tiết: `recovery-executor-codex-quota-fallback.md`.

### Restart đã chạy THÀNH CÔNG 2026-08-08 (quy trình chuẩn, đã verify từng bước)

1. **Verify identity trước khi kill**: đọc `python_runner/runs/schedule-recovery-watch-lease.json` (parent_pid + child_pid + command_identity) → đối chiếu `wmic process where "ProcessId=N" get ProcessId,ParentProcessId,CreationDate,CommandLine` (parent = powershell chạy `run-schedule-recovery-watch.ps1`, child = `python -m scheduler.recovery_runtime`). Backup lease: `cp ... schedule-recovery-watch-lease.json.pre-restart-<ts>`.
2. **Kill child**: `taskkill /PID <child> /T /F` (git-bash: dùng `/PID` đơn, KHÔNG `//PID` — `//PID` bị bash convert thành `/PID` sai → "Invalid argument"). Chờ ~10s.
3. **Watch parent tự exit** khi thấy child chết (`HasExited`) — và **XÓA lease file khi exit** (đúng hành vi, đừng hoảng khi thấy lease biến mất; backup vẫn còn). Verify parent chết bằng `wmic` (tasklist qua MSYS trả trống dù sống).
4. **Trigger lại**: `schtasks /run /tn "TikTokScheduleRecovery"` qua `cmd //c` **FAIL im lặng trong git-bash** — lỗi thật gặp: `'un' is not recognized` (bash nuốt quote) rồi `ERROR: The system cannot find the file specified`. **Đường chạy được: PowerShell** — `Start-ScheduledTask -TaskName "TikTokScheduleRecovery"` (viết .ps1 dưới `%TEMP%`, chạy `powershell -NoProfile -ExecutionPolicy Bypass -File ...`, xóa sau). Trước khi start: `Get-ScheduledTask -TaskName "TikTokScheduleRecovery"` phải `State=Ready` (sau khi watch exit); sau start: `State=Running`.
5. **Verify lease MỚI**: `lease_id` ĐỔI (vd cũ `1ca561...` → mới `b5e9b867...`), parent_pid + child_pid + `child_process_start_time` đều mới, `state=running`. Double-run check: `wmic process where "name='python.exe'" get CommandLine | grep -c "scheduler.recovery_runtime"` phải = **1**. Log `runs/schedule-recovery-task.log` append tiếp (`outcomes: []` bình thường).
6. **Sau restart, incident cũ có slot reserved trước crash**: runtime mới KHÔNG tự tiếp tục slot đó — chờ dispatch mới (shift kế tiếp) hoặc fail-closed `LIVE_ATTEMPT_UNKNOWN_AFTER_CRASH` (reservation-without-completion). Đừng kỳ vọng ledger có entry mới ngay cho incident cũ; `outcomes: []` = chưa có fail mới = bình thường.
