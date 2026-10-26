# Auto-Wiring vs Guidance vs Fail-Fast: 3 Golden Criteria & ADB Detector Invariants

## 1. Context & User Correction
When Farm Gate Compliance reports show persistent, high-frequency rule blocks (e.g. 143 blocks in 6 hours), simply patching text in `SKILL.md` (guidance) fails to change execution behavior. The user correctly challenged: *"K auto wire à, cái m sửa là ở tầng guidance à"*.
Guidance is passive (the model reads but is not mechanically constrained). Machine-enforceable constraints and mechanical transforms MUST live in the hook/engine layer, not in prompt prose.

---

## 2. The 3 Golden Criteria for Auto-Wiring (`action: rewrite`)
A gate or hook interception is ONLY allowed to Auto-Wire (in-place rewrite/clamp) if it answers YES to all three questions:
1. **Deterministic & Intent-Preserving:** Is the transformation fully deterministic and independent of guessing agent intent?
2. **Authority-Narrowing (Subset $\subseteq$):** Does the transformation strictly narrow or preserve permissions/scope (never expand authority, change tiers arbitrarily, or bypass audit)?
3. **Transparent & Receipted:** Is the transformation clearly signaled to the caller (via `REWRITE_RECEIPT`, `TRANSIENT_CLAMPED` flag, or structured notice) so the agent does not mistake a partial/clamped result for a complete one?

*If any criterion fails: The gate MUST Fail-Fast with a structured Active Pivot (`REQUIRED_ACTION_O1`).*

---

## 3. Operational Classification Matrix (Farm Guard Interceptions)

| Interception Rule | Frequency (6h) | Mechanism Category | Architecture Resolution |
| :--- | :---: | :--- | :--- |
| **`GUARD_AMBIGUOUS_ADB_COMMAND`** | **21** | **Detector Bug (False Positive)** | **Fix Hook Detector Immediately:** Hook was doing naive substring matching across whole command lines. Any commit message or grep containing `"Adb"` or `"Admin"` was blocked. Must split shell into segment tokens (`argv`) and only inspect when the executable is actually `adb` or `fastboot`. |
| **`GUARD_DEVICE_FOREGROUND_TIMEOUT`** | **12** | **Auto-Wire (Auto-Clamp)** | **Auto-Clamp to 60s:** `timeout = min(requested or 60, 60)`. Tag telemetry with `TRANSIENT_CLAMPED` so Escalation Ladder does not count this as an objective task failure. Operations needing >60s must pivot to background. |
| **`investigate` (missing BUDGET)** | **30** | **Auto-Wire (Auto-Inject)** | **Auto-Inject Default Budget:** For structured read-only routes, inject `budget.tool_calls = min(given or 8, 8)`. Tag result with `BUDGET_AUTO_INJECTED`. Runtime must enforce the count, not just inject string into prompt. |
| **`GUARD_SEARCH_FILES_ROOT` / `DANGEROUS_ROOT`**| **69** | **Fail-Fast + Active Pivot** | **Strictly Forbidden to Auto-Wire:** Guessing which subfolder the agent meant violates Scope Lock and yields silent partial results. Must block and return copy-pasteable narrow path or inspect command. Provide an indexed `locate` tool for file discovery. |
| **`GUARD_MANUAL_ADB_TAP`** | **5** | **Fail-Fast + Active Pivot** | **Strictly Forbidden to Auto-Wire:** Never wash an unverified raw coordinate tap into an official tool action. Require OCR element detection or script runner updates. |
| **`subagent_edit_blocked`** | **6** | **Conditional: Route vs Fail-Fast** | **Auto-Route if Contract Valid:** If an exact patch contract exists, route to Dispatcher ladder (Sol $\to$ Agy $\to$ Haiku). If no contract exists, Fail-Fast with pre-filled `dispatch_worker.py` template. |

---

## 4. Shell Tokenizer & Subprocess Segmentation (Detector Fix Spec)
To prevent False Positives without weakening safety:
```python
def classify_command_segments(cmd: str, depth: int = 0) -> str:
    # Split on ;, &&, ||, |, newlines, $(), ``
    segments = split_shell_segments(cmd)
    if segments is None or depth > 3:
        return "AMBIGUOUS"  # Parse failed, fail-closed
    for argv in segments:
        exe = Path(argv[0]).stem.lower()
        if exe in {"bash", "sh", "powershell", "pwsh", "cmd", "python", "env", "xargs", "eval"}:
            payload = extract_subshell_payload(argv)
            res = classify_command_segments(payload, depth + 1)
            if res != "OK":
                return res
        elif exe in {"adb", "fastboot"}:
            return check_adb_safety(argv)  # Check for MANUAL_TAP, raw dangerous calls
        # benign wrappers (git, grep, rg, cat, echo) treat arguments strictly as data
    return "OK"
```
- `AMBIGUOUS` strictly means parser failure, not keyword detection.
- `git commit -m "fix(dual-cluster): route Admin machines ..."` is safely classified as `OK` because `argv[0]` is `git`.
