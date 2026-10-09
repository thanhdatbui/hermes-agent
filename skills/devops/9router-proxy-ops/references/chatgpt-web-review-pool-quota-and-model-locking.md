# Model Locking & Quota Guardrails for ChatGPT-Web Review Pools (:20129)

## Overview
ChatGPT Web pools on OmniRoute (:20129) map connections to accounts with specific performance tiers (`instant`, `high`, `xhigh`, `pro`). 

### Critical Quota Distinction
- **`chatgpt-web/gpt-5.6-sol-high`**: Default lane for code review and audit. Moderate-to-high quota shared evenly across the 16-account round-robin pool.
- **`chatgpt-web/gpt-5.6-sol-pro`**: Heavy thinking lane with strict upstream limits on Web Plus/Team. Calling `sol-pro` directly consumes the account's rare pro quota and triggers `[502]: You've hit your limit. Please try again later.`.
- **`chatgpt-web/gpt-5.6-sol-instant`**: Non-thinking (0 effort) lane. Inadequate for deep code audit and scorecard evaluation.

## Guardrail Rules
1. **Never pass bare model overrides (`--model sol-pro` / `--model sol-instant`)** in automated scripts or review runners (`closeout_gate.py`, `sol_auditor.py`).
2. **Always route through combo `review`**: Canonical combo `review` points Tier 0 to `chatgpt-web-pool` running `chatgpt-web/gpt-5.6-sol-high`.
3. **Defense-in-depth ("Strip & Freeze")**:
   - In CLI scripts: Whitelist allowed models and strip/reject unrecognized `--model` arguments.
   - In Shell Hooks: Block commands attempting to execute with `sol-pro` or `sol-instant` flags before execution.
   - On 502 rate limits: Back off and retry within the same tier pool; NEVER automatically downgrade thinking tiers to "instant".
