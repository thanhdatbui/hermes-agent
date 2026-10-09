# Offline 5-Profile Concurrent Supervisor Contract & Architecture

## 1. Lifecycle Stage Sequence (Strict Order)

The end-to-end lifecycle for GPM Hotmail/Codex multi-stage automation follows a strict sequential pipeline per account:

```text
HOTMAIL_LOGIN
      ↓
 CHATGPT_REG
      ↓  (wait 24-48h nurture cooldown)
 CODEX_OAUTH
      ↓  (wait 7d security aging)
 CHANGE_INFO
      ↓
REMOVE_RECOVERY
      ↓
SIGN_OUT_EVERYWHERE
      ↓
RELOGIN_NEW_PASSWORD
      ↓
    DONE
```

### Stage Transitions & Cooldown Rules
- **HOTMAIL_LOGIN**: Initial authentication and session seeding into GPM profile.
- **CHATGPT_REG**: Direct email registration (Zero-SSO). If Graph API / Hotmail OTP support is incomplete, MUST return `STAGE_BLOCKED_DEPENDENCY` and preserve state; NEVER fabricate success.
- **Cooldown 24-48h**: Required pause before triggering OAuth flows to avoid prompt risk.
- **CODEX_OAUTH**: Authorize Codex OAuth with GPM session.
- **Aging 7d**: Cooldown period before modifying account credentials/recovery proofs.
- **CHANGE_INFO**: Update Hotmail account password.
- **REMOVE_RECOVERY**: Strip unapproved recovery emails (e.g. getnada, boxtaikhoan).
- **SIGN_OUT_EVERYWHERE**: Revoke active sessions across all devices on Microsoft Security panel.
- **RELOGIN_NEW_PASSWORD**: Re-verify and seed the updated credential into the GPM profile.
- **DONE**: Terminal state.

---

## 2. Supervisor Concurrency & Execution Model

- **5 Profiles Concurrent**: The supervisor manages a target cohort of 5 profiles simultaneously (e.g. via `ThreadPoolExecutor(max_workers=5)`).
- **Stages Sequential Per Profile**: Within a given profile, stages must execute in strict order. No skipping or out-of-order execution.
- **Tick Scanning**: On every tick/execution, the supervisor inspects each profile's current state and selects the first eligible incomplete stage. If a stage is blocked by a dependency or cooldown, it remains in that stage with status `STAGE_BLOCKED_DEPENDENCY` or `WAITING_COOLDOWN`.

---

## 3. Critical Safety Invariants

1. **Anti-Fabrication Guard**:
   - Never mark any stage `SUCCESS` merely because a dependency script exists or returns 0 without verifiable evidence.
   - When a required flow or helper is missing or unsupported, log explicitly as `STAGE_BLOCKED_DEPENDENCY` and halt progress for that profile.
2. **Single-Instance Mutex (Windows `msvcrt`)**:
   - Must acquire a batch-level non-blocking lock (`msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)`) at script startup.
   - If lock is held by another process, exit immediately with clean error.
3. **Atomic State Persistence**:
   - State path: `D:\Taadaa\runtime\kibe\cron-state\batch_gpm_5profiles_supervisor_state.json`.
   - Never write directly to the target state file. Write to a temporary file in the same directory (`NamedTemporaryFile(dir=..., delete=False)`), flush + `os.fsync`, then `os.replace` atomically.
4. **Execution Modes**:
   - `--dry-run` (default): Inspect persisted state, evaluate eligibility for each profile, print planned actions, and exit without launching browser processes or mutating files.
   - `--profile-id <id>` (optional): Filter inspection or execution to a single profile.
   - `--live`: Must be rejected with `NOT_ACTIVATED` error unless full live safety requirements and explicit user activation are present.
5. **Budget Preservation & Direct Action**:
   - When assigned a focused task under a strict iteration/call budget (e.g. <= 15 calls), avoid deep historical session digging. Implement the core script skeleton, verify with `py_compile`, and execute `--dry-run` immediately.
