# Hermes CLI fallback cho auto recovery khi Codex hết quota (2026-08-07)

## Vấn đề

Schedule recovery watch (`tiktok-luot nuoi acc`) chạy advisor/repair qua
`codex exec --model gpt-5.6-terra/sol/luna`. Codex account hết quota →
output `ERROR: You've hit your usage limit. Upgrade to Pro... try again at
Aug 12th, 2026 12:29 AM.` → recovery fail 100%: 35 máy `FINAL_BLOCKED` →
lock `blocked` giữ chặt → shift sau skip máy.

## Chuỗi lỗi trong ledger (chẩn đoán)

```
DETECTED → CLASSIFIED → ADVISOR_RESERVED (slot 5-7, gpt-5.6-sol/terra)
→ ADVISOR_NOT_READY (reason=planner-process-failed)
→ FINAL_BLOCKED (reason=repair-ladder-exhausted-without-approved-patch)
→ MANUAL_REQUIRED
```

Bằng chứng quota trong `.ai-runs/schedule-recovery/<incident_key>/slot-*/advisor-output.txt`:
```
OpenAI Codex v0.145.0 ... model: gpt-5.6-sol ... sandbox: read-only
ERROR: You've hit your usage limit. Upgrade to Pro ... try again at Aug 12th, 2026 12:29 AM.
```

## Fix (commit ca2431c, branch feat/hermes-cli-fallback)

### 1. `recovery_supervisor.py`
- Hằng số:
  ```python
  HERMES_EXECUTABLE = os.environ.get(
      "HERMES_EXECUTABLE",
      r"C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe",
  )
  HERMES_PROVIDER = DEEPSEEK_PROVIDER  # "9router"
  ```
- Quota detector:
  ```python
  _QUOTA_MARKERS = re.compile(
      r"usage\s*limit|quota|rate\s*limit|429|403|hit\s+your|"
      r"insufficient\s+quota|credit\s+balance|out\s+of\s+credits|"
      r"model\s+unavailable|provider\s+unavailable|capacity",
      re.IGNORECASE,
  )
  def detect_provider_quota(output, *, model="", source="codex-cli-output"):
      # return {"code": "quota_exhausted", "provider": "codex", "model", "source"}
      # or None — NEVER embed raw output (secret leak into ledger)
  def provider_unavailable_from_output(output, *, model="", source=...):
      # PlannerResult.provider_unavailable(...) hoặc invalid("planner-process-failed")
  ```
- `build_repair_command` / `build_advisor_command`: nhánh deepseek slot trả
  `[HERMES_EXECUTABLE, "-z", prompt_text, "-m", slot.model, "--provider", "9router"]`
  — prompt đọc từ prompt_path (repair) hoặc inline (advisor); KHÔNG
  `--sandbox` / `--output-schema` / `--output-last-message`.

### 2. `recovery_runtime.py`
- Import thêm `detect_provider_quota`, `provider_evidence_digest` (cả 2 import blocks).
- Default executor: `deepseek_executor or self._repair_with_hermes`,
  `deepseek_planner_executor or self._advise_with_hermes` (trước đây là
  `_repair_with_codex` / `_advise_with_codex`).
- `_repair_with_hermes` / `_advise_with_hermes`: mirror codex nhưng parse stdout
  qua `_json_object`, quota → `PROVIDER_UNAVAILABLE` + evidence
  (`source="hermes-cli-output"`).

### 3. BUG quan trọng đã sửa

`PatchDecision.from_result({})` KHÔNG bao giờ trả None (empty mapping → empty
PatchDecision). Code cũ `if code != 0 and decision is None:` bỏ qua nhánh quota
khi output quota (json_object → None → `{}`). Fix:

```python
decision = PatchDecision.from_result(result)
if code != 0:
    quota = detect_provider_quota(output, model=slot.model, source=...)
    if quota is not None:
        return {"planner_status": "PROVIDER_UNAVAILABLE", "planner_reason": quota["code"],
                "provider_evidence": quota, "evidence_digest": provider_evidence_digest(quota),
                "returncode": code}
    if decision is None:
        return {"planner_status": "INVALID", "planner_reason": "gpt-planner-process-failed",
                "returncode": code}
```

### 4. Test

- `test_recovery_classification.py`: assert cũ `command[index("--sandbox")+1] ==
  "workspace-write"` FAIL (deepseek giờ build Hermes command) → đổi sang
  `command[0] == HERMES_EXECUTABLE`, `"-z" in command`, `"--provider"` +
  `"9router"`, `"--sandbox" not in command`.
- `test_recovery_supervisor.py`: `HermesCliFallbackTests` — quota detect,
  provider_unavailable → ready_for_fallback, Hermes command build,
  `_repair_with_hermes` mock `_run_capture` (JSON → `patched: True`; quota →
  `PROVIDER_UNAVAILABLE`).
- Kết quả: 99 passed + 8 subtests (consumer), core 5 passed.

## Hermes CLI one-shot notes

- `hermes -z "<prompt>" -m deepseek-v4-flash --provider 9router` → stdout only.
- `-Q` KHÔNG hợp lệ với `-z` (`unrecognized arguments: -Q`); chỉ `hermes chat -Q`.
- Executable nằm trong venv: `...\hermes-agent\venv\Scripts\hermes.exe`, KHÔNG
  system PATH → recovery chạy qua Start-Process phải dùng abs path.

## Delegation pitfall (Windows/MSYS worktree)

Worker tạo worktree với path MSYS bị mangling (`D:\d\Taadaa\...`) → git
registration lỗi, `git worktree add` báo "branch already exists", branch rác
không có worktree. Dọn:
```bash
git worktree prune
rm -rf /d/Taadaa/worktrees/<rác>
git branch -d feat/<branch-rác>
```
Khi giao repo Windows cho worker: hướng dẫn `git checkout -b` TRONG working dir,
KHÔNG tạo worktree; yêu cầu chạy test + commit xong trong 1 phiên (worker dễ
hết iteration giữa chừng → parent tự hoàn tất: verify diff, sửa test fail,
commit).

## File log quan trọng (chẩn đoán schedule recovery)

| File | Nội dung |
|---|---|
| `python_runner/runs/schedule-recovery-ledger.jsonl` | events recovery (DETECTED/ADVISOR_*/FINAL_BLOCKED/MANUAL_REQUIRED) |
| `python_runner/runs/schedule-recovery-task.log` | watch loop (observed_at mỗi ~16s) |
| `.ai-runs/schedule-recovery/<incident>/slot-*/advisor-output.txt` | stderr Codex CLI thật (bằng chứng quota) |
| `python_runner/runs/schedule-recovery-watch-lease.json` | heartbeat watch (parent/child pid, lease_id) |
| `C:\Users\Kibe\.codex\device-locks\machine_*.lock.json` | lock blocked/handoff/running |
