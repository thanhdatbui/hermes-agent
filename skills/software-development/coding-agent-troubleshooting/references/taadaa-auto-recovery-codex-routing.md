# Taadaa Auto-Recovery: Codex CLI Routing & Quota Fallback

Context for the D:\Taadaa automation workspace. The auto-recovery system runs
headless via a Python scheduler — it is NOT "Codex spawning Hermes". The
fallback question ("what happens when GPT models hit quota?") is answered by
routing the SAME codex CLI through a local router, not by adding a second
agent instance.

## Architecture (as of 2026-08)

```
RecoveryRuntime (python_runner/scheduler/recovery_runtime.py)
   ├─ repair_executor  → build_repair_command()        → codex exec --model gpt-5.6-luna ...
   ├─ advisor_executor → build_advisor_command()       → codex exec --model gpt-5.6-terra/sol ...
   ├─ audit_executor   → _audit_patch (Gemini/OpenCode/Command Code wrappers)
   └─ live_executor    → _run_target_verify (target ADB/UI script)
```

- `RecoveryRuntime` is flow-neutral: schedule, CLI, runner, and event producers
  all emit one-target incidents into the same runtime.
- Codex CLI commands are built in `recovery_supervisor.py`:
  - `build_repair_command(repo_root, slot, prompt_path)` — line ~465
  - `build_advisor_command(repo_root, slot, result_path, prompt)` — line ~487
  - Both use: `codex --ask-for-approval never exec --model <slot.model>
    --config 'model_reasoning_effort="<effort>"' --sandbox <...>`
- The model comes from `slot.model` (RepairSlot) — THIS is the fallback
  insertion point. To route a slot through DeepSeek:
  add `--config 'model_provider="9router"'` and set `slot.model` to
  `deepseek-v4-flash` when the GPT route reports quota exhaustion.
- Audit wrappers live in `D:\Taadaa\tools\*.ps1`:
  - `invoke-gemini-9router-audit.ps1` → `gemini/gemini-3.6-flash`, reasoning_effort=high
  - `invoke-opencode-audit.ps1` → `opencode/deepseek-v4-flash-free` only
  - `invoke-command-code-9router-audit.ps1` → `cmc/deepseek/deepseek-v4-flash`
    (local 9Router `http://127.0.0.1:20128/v1`, key `NINEROUTER_API_KEY`)
  - `claude-quota-preflight.ps1` → exit 0=OK, 20=5h≥85% block, 21=unavailable, 22=weekly≥90% block

## Roles (Taadaa AGENTS.md, D:\Taadaa)

- Luna/max = sole patch/live executor (codex exec, model gpt-5.6-luna,
  effort max). Terra high/xhigh + Sol high/max = read-only planners/advisors.
- `global_recovery.py` in automation-core hard-codes
  `LUNA_EXECUTOR_MODEL = "gpt-5.6-luna"`, `TERRA_MODEL = "gpt-5.6-terra"`,
  `SOL_MODEL = "gpt-5.6-sol"` and `GlobalRecoveryPolicy.__post_init__`
  REJECTS any executor_model != LUNA_EXECUTOR_MODEL
  (`LUNA_MAX_IS_ONLY_EXECUTOR`). A DeepSeek-executor fallback therefore
  touches core policy, not just the consumer supervisor — expect a
  `GlobalRecoveryPolicy` change + contract test update.
- Recovery state machine (all triggers): DETECTED -> CLASSIFIED ->
  RECOVERY_RESERVED -> RECOVERING -> RECAPTURED -> RETRYING ->
  VERIFIED_SUCCESS | FINAL_BLOCKED. Attempt cap: detection + 7 live
  recoveries; escalation/restart/schedule re-fire NEVER resets the cap.
- Audit slots: one independent read-only slot per unchanged plan/diff;
  ordinary code audit route Gemini -> OpenCode -> Command Code -> fresh Codex;
  hard-trigger (core/shared-contract, ≥2 consumers, security/lock/scheduler,
  global policy) Claude -> fresh Codex -> OpenCode -> Gemini -> Command Code.
- FINAL_BLOCKED requires same-target Sol/high terminal review +
  `sol_handoff_completed=true` in
  `D:\CodexRuntime\<project-id>\recovery\handoff-ledger.jsonl`.

## Fallback design (from 2026-08-04 consultation)

- User's ask: when Codex GPT models exhaust quota, auto-recovery should fall
  back to deepseek-v4-flash via 9Router — NOT spin up a separate Hermes
  instance ("2 bản phức tạp quá").
- Verified feasible: config.toml already has `[model_providers.9router]`,
  `/v1/responses` wire confirmed working with deepseek-v4-flash, and a
  `config.pre-deepseek-20260731-1740.toml` backup shows the omni provider
  (same endpoint) was previously used.
- **Tool-calling smoke test (2026-08-04) — RESOLVED:** deepseek-v4-flash via
  codex CLI DOES support tool calling (shell exec + file read) and
  deepseek-v4-pro answers text. Both work through `--sandbox workspace-write`
  **once the error-1920 PATH fix is applied** (see
  `references/windows-sandbox-errors.md`). Without the PATH fix, sandboxed
  exec fails for EVERY model including gpt-5.6-luna — the fallback decision is
  therefore blocked by the same sandbox issue, not by deepseek capability.
- DeepSeek models on 9Router (from `/v1/models`): `deepseek-v4-flash`,
  `deepseek-v4-pro`, `deepseek-v4-pro-max` (combo) and
  `cmc/deepseek/deepseek-v4-flash`, `cmc/deepseek/deepseek-v4-pro` — all
  `tools=true`, `reasoning=true`, 1M context, 384K maxOutput. Command Code
  provider (`cmc/`) has identical capabilities to combo for deepseek.
- Remaining implementation decision: granting deepseek write/live executor
  role still requires the `GlobalRecoveryPolicy` change (core policy rejects
  non-Luna executor) + AGENTS.md rule change — see "Roles" above.
- Rule change needed: a "DeepSeek quota fallback" section in
  D:\Taadaa\AGENTS.md allowing deepseek-v4-flash (9Router) to substitute the
  same role when GPT quota is exhausted, preserving state machine, cap,
  verifier, and fresh-session/materially-different-hypothesis requirements.
