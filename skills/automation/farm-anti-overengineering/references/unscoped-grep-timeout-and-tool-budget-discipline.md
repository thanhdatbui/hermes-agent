# Pitfall: Unscoped Recursive Grep on D:/Taadaa Root & Tool Call Budget Burn

## 1. Context & Incident (2026-09-19)
- User requested: "Hoan tat tach biet canh bao mat phien va captcha trong batch_aggregator.py va chay pytest pass. Gioi han: <= 10 tool calls. Apply patch truc tiep va chay test ngay."
- Agent spent multiple tool turns reading git log and then executed:
  `grep -rn "chưa mất phiên" /d/Taadaa/`
  which timed out after 180 seconds because `D:/Taadaa/` contains hundreds of gigabytes of Python virtualenvs (`python-envs/`), device snapshots, media artifacts, node modules, and git histories.
- As a result, tool call budget was exhausted before applying the patch and running pytest.

## 2. Hard Invariants
1. **Never grep recursively on `/d/Taadaa/` root**:
   - ALWAYS scope searches to the exact repository or subdirectory, e.g.:
     `grep -rn "..." /d/Taadaa/automation-core/src/`
   - Use `--exclude-dir` for virtual environments, `.git`, `__pycache__`, and `artifacts` if searching higher up.
2. **Obey Explicit Tool Budget Directives**:
   - When prompt states `<= 10 tool calls. Apply patch directly and run test immediately`:
     - Step 1: Read the exact function/lines in the target file (1 call).
     - Step 2: Apply patch immediately with `patch` (1 call).
     - Step 3: Run targeted test with `terminal` (1 call).
     - Step 4: Sync / copy artifact (1 call).
     - Total: 4 tool calls.
   - Do NOT run deep historical git log archaeology, repo-wide searches, or speculative verification loops when the prompt already specifies the exact logic to implement.
