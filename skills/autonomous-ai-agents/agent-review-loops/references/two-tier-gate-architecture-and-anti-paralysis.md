# Two-Tier Gate Architecture & Anti-Paralysis Protocol

## 1. Context & Incident (05/10/2026)
Between 01/10 and 05/10/2026, the Taadaa Farm Coordinator suffered complete operational paralysis ("Coordinator Paralysis"):
- Multiple conflicting procedural rules were hardcoded into pre-tool hooks and plugins (`farm-coordinator-guard`, `farm_policy.py`).
- Rules enforced:
  1. Terminal DEFAULT-DENY allowlist (only allowing git status/diff and a handful of binaries).
  2. Complete lockdown of `execute_code`.
  3. Strict write ledger capping Coordinator edits to <= 1 file, <= 15 lines cumulative across the session.
  4. Dispatch budget hard ceiling (10 to 20 calls max).
  5. Mandatory Sol Planning blocking any routine edit without `SOL_PLAN_ID`.
  6. Two-way self-protection guard blocking any tool touching hook/guard/config paths.
- Consequence: When any issue occurred, the Coordinator could not write code, could not dispatch workers, could not run diagnostics, and could not even edit the config to disable the guard. The system suffered a fatal administrative deadlock.

## 2. The Solution: Strict Two-Tier Gate Separation (PA3)

All safety and policy mechanisms must be strictly segregated into two separate tiers:

### Tier 1: Hardware & Asset Safety Invariants (HARD FAIL-CLOSED)
These must be extremely lightweight, 100% offline, zero network dependencies, and enforced strictly:
1. **Device Bulkhead (`guard_device_bulkhead.py`):** Block manual `adb shell input tap/swipe/keyevent` used as a quick fix instead of writing automated code handlers.
2. **Filesystem Bulkhead (`guard_broad_grep.py`):** Block broad recursive filesystem scans (`os.walk`, `grep -r`, `find`) on protected repository roots (e.g. `D:/Taadaa`).
3. **Resource Protection (`guard_read_file_size.py`):** Block reading monolithic log files > 10MB into context; enforce `tail` or targeted extraction.
4. **Git Safety:** Block destructive git commands (`git reset --hard`, `git push --force`).
5. **Asset Preservation:** Prohibit rogue account logouts, cookie wiping, or status downgrades based on transient network errors.

### Tier 2: Workflow, Dispatch & Quality Discipline (ADVISORY / AUDIT LOG ONLY)
These govern process, style, and review. They MUST NEVER hard-block the Coordinator or cause operational deadlock:
1. **Dispatch & Sol Planning:** Routine code edits with O(1) patch contracts proceed immediately. External planner (Sol/OmniRoute) is advisory; timeout or downtime must fall back to allow with warning, NEVER block.
2. **Terminal & Tool Permissions:** Coordinator retains full access to `terminal`, `write_file`, `patch`, and `execute_code`.
3. **Dispatch & Write Budget:** Budgets are monitored and logged to audit telemetry for review, not enforced as hard execution kills.
4. **Closeout Gate:** Reviewer scoring (>= 85/100) is enforced at the pre-push boundary before remote publication, not as an obstacle between routine development turns.

## 3. Telegram Chunking Invariant
When delivering instructions or prompts meant for the user to copy/paste into external tools (Antigravity, local terminal):
- DO NOT dump monolithic blocks (> 100 lines) into Telegram messages; mobile clients cannot select/copy cleanly.
- Split into numbered sections (e.g. Part 1/6, 2/6, <= 50 lines each) OR write directly to a local file (e.g. `C:/Users/Kibe/...prompt.txt`) and inform the user.

## 4. Git Push from Subshell Environment
Hermes subshells set `GIT_ALLOW_PROTOCOL=file` by default. When pushing to an authorized remote (`fork` on GitHub) after Closeout Gate approval:
- Explicitly pass `GIT_ALLOW_PROTOCOL=https`.
- Use the authenticated GitHub token via `$(gh auth token)`.
- Commit with explicit user identity (`-c user.name="Kibe" -c user.email="kibe@taadaa.local"`).
