# Chẩn đoán "tại sao Hermes (DeepSeek) không chạy trong autorecovery"

Verify 2026-08-08 trên repo `tiktok-luot nuoi acc`. Incident mẫu:
`2026_08_08_MORNING_15_6_VICHANGER_VPN_...` — 25 máy fail cùng mili-giây với
`blocked-vichanger-vpn` nhưng thực chất là lỗi đọc proxy-mapping workbook chung
(không phải VPN thật) — classifier nhầm nguồn mapping → auto-recovery ladder.

## Nơi tìm bằng chứng

- Watch log: `runs/schedule-recovery-task.log` — JSON lines `{"outcomes": [...]}`.
  Lọc bỏ noise `noon:already-terminal` để thấy event thật.
- Ledger: `python_runner/runs/schedule-recovery-ledger.jsonl` — event chain gốc.
- Artifact per-slot: `.ai-runs/schedule-recovery/<incident_key>/slot-N/` với
  `repair-output.txt` (stdout/stderr executor), `repair-prompt.txt`,
  `deepseek-executor-result.json` (JSON parse được), `advisor-*.txt`.

## Chuỗi event khỏe mạnh

```
DETECTED -> CLASSIFIED(AUTO_RECOVERY_PENDING) -> PATCH_ATTEMPT_RESERVED
-> ADVISOR_RESERVED/ADVISOR -> (DEEPSEEK_)EXECUTOR_RESULT
-> DEEPSEEK_FALLBACK(executor=true) -> handler/live gate -> VERIFIED_SUCCESS
```

## Dấu hiệu triệu chứng → root cause

1. **Mọi slot đều `NOT_READY` / `structured-patch-decision-required`** với
   `decision: ""` trong ledger nhưng `repair-output.txt` CÓ JSON PATCH_READY:
   → bug parser: rightmost scan ghi đè object cha bằng object con evidence.
   Fix: `_last_embedded_json_object` chọn largest span.

2. **`repair-output.txt` hiện mojibake tiếng Việt** (`TÃ´i Ä‘Ã£...`):
   → subprocess `text=True` decode bằng locale Windows (cp1252).
   Fix: `_run_capture(..., encoding="utf-8")` cho call Hermes.

3. **`ERROR: Invalid schema ... 'oneOf' is not permitted`** ở đầu `repair-output.txt`
   (xảy ra ở Codex path): schema `repair-schema.json` dùng `evidence: {"oneOf":[...]}`
   nhưng 9router/commandcode từ chối `oneOf` trong `response_format` schema.
   → Codex chết ngay từ lúc gửi request, không sinh được quyết định nào.

4. **Slot reserved nhưng 3h+ không có RESULT**: `_run_capture` không timeout,
   Hermes one-shot agent-loop bị treo → slot tiêu vô hạn. **ĐÃ FIX (2026-08-08)**:
   `_run_capture(..., timeout=HERMES_CLI_TIMEOUT_SECONDS=5400.0)` — bắt
   `subprocess.TimeoutExpired` → return `(124, <partial output>)` → slot fail
   closed (`INVALID`/planner-process-failed). Chỉ áp cho 2 call Hermes
   (`_repair_with_hermes`, `_advise_with_hermes`); codex path giữ blocking.
   Lưu ý đối lập: Hermes one-shot hợp lệ cũng mất 10-15+ phút/slot — timeout
   quá ngắn (vd <10 phút) sẽ giết cả slot hợp lệ. 90 phút là dung hòa.

5. **Đừng nhầm testánh "Hermes không được gọi"** — kiểm `grep '"model":"' ledger
   | sort | uniq -c`: Hermes flash/pro có thể ĐÃ được gọi hàng trăm lần
   (`cmc/deepseek/deepseek-v4-flash`, `cmc/deepseek/deepseek-v4-pro`,
   `provider_mode:"deepseek_executor"`) nhưng mọi lần đều NOT_READY.

## Dry-run thật (không đụng repo thật)

```python
temp = Path(tempfile.mkdtemp(prefix="hermes-dryrun-"))
repo_root = temp / "repo"                 # KHÔNG dùng repo thật
artifact = repo_root / ".ai-runs" / "dryrun" / "machines" / "machine_99"
# tạo log.jsonl + summary.json nội dung fake, nhãn rõ "dry-run fake"
runtime = RecoveryRuntime(repo_root=repo_root, ledger=RecoveryLedger(temp/"ledger.jsonl"), artifact_root=temp/"runtime")
result = runtime._repair_with_hermes(incident, DEEPSEEK_FALLBACK_LADDER[0], run_root)
```
Với evidence fake, kết quả đúng là `NO_SAFE_PATCH` + `returncode 0` — Hermes
từ chối làm patch giả, đó là behavior ĐÚNG (fail safe), không phải failure.
Kỳ vọng `PATCH_READY` chỉ hợp lệ khi artifact là evidence thật từ repo thật.

## Lưu ý

- `HERMES_EXECUTABLE` env override; default pin
  `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe`.
- `import scheduler.recovery_runtime` từ script ngoài cần chdir về
  `python_runner/` (module scheduler nằm trong đó) và đừng import module
  `logging` clash khi test trực tiếp.