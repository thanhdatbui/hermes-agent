# Hermes CLI Fallback for Auto-Recovery (tiktok-luot nuoi acc) — 2026-08-07

✅ **DONE + COMMITTED** — nhánh `feat/hermes-cli-fallback` (consumer repo), commit `ca2431c`.
Suite: **99 passed + 8 subtests** (test_recovery_*.py). Recovery watch đã restart chạy code mới.
Core repo `automation-core`: KHÔNG đổi file (global_recovery.py thuần policy) — chỉ tạo branch.

## Mục tiêu

Codex CLI hết quota (`You've hit your usage limit`) làm toàn bộ auto-recovery tê liệt:
planner trả `INVALID("planner-process-failed")` thay vì `PROVIDER_UNAVAILABLE` → fallback
DeepSeek không bao giờ kích hoạt ("fallback chết im", xem `schedule-recovery-log-analysis.md`).
Fix: (1) detect quota pattern trong output → PROVIDER_UNAVAILABLE + evidence,
(2) chạy DeepSeek ladder qua Hermes CLI one-shot thay vì codex exec.

## Files đã sửa (consumer repo `D:\Taadaa\tiktok-luot nuoi acc`)

### `python_runner/scheduler/recovery_supervisor.py`
- Const (gần `DEEPSEEK_PROVIDER = "9router"`):
  ```python
  HERMES_EXECUTABLE = os.environ.get("HERMES_EXECUTABLE",
      r"C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe")
  HERMES_PROVIDER = DEEPSEEK_PROVIDER
  ```
- `_QUOTA_MARKERS` regex + `detect_provider_quota(output, *, model="", source="codex-cli-output")`
  → `{"code": "quota_exhausted", "provider": "codex", "model", "source"}` | None.
  Regex: `usage\s*limit|quota|rate\s*limit|429|403|hit\s+your|insufficient\s+quota|credit\s+balance|out\s+of\s+credits|model\s+unavailable|provider\s+unavailable|capacity` (IGNORECASE).
- `provider_unavailable_from_output(...)` → `PlannerResult.provider_unavailable` hoặc `invalid("planner-process-failed")`.
- `build_repair_command` / `build_advisor_command`: nhánh sớm cho `slot.model in DEEPSEEK_FALLBACK_MODELS`
  trả `[HERMES_EXECUTABLE, "-z", <prompt>, "-m", slot.model, "--provider", HERMES_PROVIDER]`.
  - repair: prompt đọc từ `prompt_path.read_text()`; advisor: prompt truyền thẳng.
  - **KHÔNG** có `--sandbox` / `--output-schema` / `--output-last-message` — Hermes in stdout.
  - Các nhánh codex cũ cho Luna/Terra/Sol GIỮ NGUYÊN.

### `python_runner/scheduler/recovery_runtime.py`
- Import thêm `detect_provider_quota` + `provider_evidence_digest` (CẢ 2 import blocks — try/except).
- `__init__` defaults:
  ```python
  self.deepseek_executor = deepseek_executor or self._repair_with_hermes
  self.deepseek_planner_executor = deepseek_planner_executor or self._advise_with_hermes
  ```
- `_repair_with_hermes(incident, slot, run_root)` — mới: prompt ghi `repair-prompt.txt`, build command
  Hermes shape, `_run_capture`, output ghi `repair-output.txt`, parse `_json_object(output)` (stdout).
- `_advise_with_hermes(incident, advisor, run_root)` — mới: parse stdout, code==0 → `output.strip()[:12000]` làm plan.
- **BUG FIX (quan trọng):** `PatchDecision.from_result({})` KHÔNG bao giờ trả None (mapping rỗng → PatchDecision
  rỗng) → điều kiện `code != 0 and decision is None` LUÔN sai → quota check bị bỏ qua → trả `patched:false`.
  **Fix:** trong cả `_repair_with_codex` lẫn `_repair_with_hermes`, quota check chạy TRƯỚC `PatchDecision.from_result`
  khi `code != 0`:
  ```python
  decision = PatchDecision.from_result(result)
  if code != 0:
      quota = detect_provider_quota(output, model=slot.model, source="...-cli-output")
      if quota is not None:
          return {"planner_status": PROVIDER_UNAVAILABLE, "planner_reason": quota["code"], ...}
      if decision is None:
          return {"planner_status": INVALID, ...}
  ```

### Tests (đã thêm/cập nhật)
- `test_recovery_classification.py`: đổi assert DeepSeek slot → Hermes shape (`command[0]==HERMES_EXECUTABLE`,
  `-z`, model, `--provider 9router`, KHÔNG `--sandbox`/`--config`). Import thêm `HERMES_EXECUTABLE`.
- `test_recovery_supervisor.py`: thêm `HermesCliFallbackTests` (quota detect, provider_unavailable,
  Hermes command build, `_repair_with_hermes` parse stdout JSON + quota).

## Đã verify
- `hermes.exe -z "..." -m deepseek-v4-flash --provider 9router` → stdout sạch, exit 0. `-m cmc/deepseek/deepseek-v4-flash` cũng OK.
- Full suite: `cd "/d/Taadaa/tiktok-luot nuoi acc" && PYTHONPATH=python_runner python -m pytest python_runner/tests/test_recovery_*.py -q -p no:cacheprovider` → **99 passed, 8 subtests**.
- Ad-hoc verify (script tạm `%TEMP%/hermes-verify-quota-fallback.py`, đã dọn): 14/14 checks — quota→PROVIDER_UNAVAILABLE,
  ready_for_fallback=True, Hermes command build, `_repair_with_hermes` quota + valid JSON paths.
- Quota path debug trực tiếp: `_repair_with_hermes` + mock `_run_capture` trả quota → `planner_status: PROVIDER_UNAVAILABLE`,
  `planner_reason: quota_exhausted`, evidence `{code, provider:codex, model, source:hermes-cli-output}`, evidence_digest đủ.

## Restart recovery watch (đã làm)
- Watch cũ: parent 2576 + child 13444 (lease cũ). Kill theo identity lease:
  ```powershell
  $lease = Get-Content -Raw <lease.json> | ConvertFrom-Json
  if ($lease.parent_pid -eq <P> -and $lease.child_pid -eq <C>) { Stop-Process -Id <C> -Force; Stop-Process -Id <P> -Force }
  ```
- Start lại: `Start-ScheduledTask -TaskName 'TikTokScheduleRecovery'`.
- **Health-watch KHÔNG tự restart khi kill tay** — chỉ restart khi stall (heartbeat già + checkpoint + fence).
- Verify sau restart: lease mới (parent/child mới), `runs/schedule-recovery-task.log` poll đều mỗi 15s,
  `schedule-recovery-task.log.stderr` trống, Python 3.12 import được `HERMES_EXECUTABLE` + `detect_provider_quota`
  + `provider_unavailable_from_output(...).ready_for_fallback == True`.

## Cách hoạt động sau deploy
1. Codex CLI hết quota → output `usage limit` → `detect_provider_quota` → `PROVIDER_UNAVAILABLE` + evidence.
2. `ready_for_fallback` mở → `_activate_deepseek_executor_mode` → `_run_deepseek_executor_mode`.
3. DeepSeek ladder chạy qua **Hermes CLI** (`hermes -z`) → provider 9router → KHÔNG phụ thuộc OpenAI/Codex account.

## Pitfall tooling (session này)
- `search_files` (ripgrep) FAIL với path chứa space (`D:\Taadaa\tiktok-luot nuoi acc\...` — MSYS mangle).
  Workaround: `terminal` + `grep -n` với `cd "/d/Taadaa/tiktok-luot nuoi acc" &&`, hoặc `read_file` Windows path.
- `git diff --stat` trên repo `core.autocrlf=true` + file LF → warning CRLF vô hại.
- `patch` tool với file CRLF: diff hiện dòng đổi cả CRLF — check `git diff` sau mỗi patch.
- **Enum value:** `PlannerStatus.PROVIDER_UNAVAILABLE.value` = `"PROVIDER_UNAVAILABLE"` (uppercase).
- **E2E test đừng gọi hermes thật** (timeout ~150s): mock `_run_capture`. Khi JSON hợp lệ → result `patched:True`
  + `decision` (KHÔNG `planner_status`); chỉ quota/exit≠0 mới có `planner_status`.
- `-Q` (quiet) chỉ dùng với `hermes chat`, KHÔNG hợp với `-z`.
