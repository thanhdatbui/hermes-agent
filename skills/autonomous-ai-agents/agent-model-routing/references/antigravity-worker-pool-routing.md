# Antigravity CLI Worker Pool Routing & Concurrency Architecture

## Core Concepts: Coordinator vs. Worker Division

### 1. Coordinator (Long-Running / Stateful)
- **Role**: Telegram gateway, 24/7 cron supervision, OCR/vision inspection, decision-making.
- **Traffic Profile**: Low frequency, high context (30k-100k tokens per turn).
- **Session Strategy**: Needs **Prompt Caching**; sticky session (same account across consecutive turns) minimizes latency and token consumption.
- **Provider**: Can run via OmniRoute combo (`ag-gemini-pool-3` with `stickyRoundRobinLimit=15`) or direct API key.

### 2. Worker (One-Shot / Stateless Execution)
- **Role**: Code surgery, refactoring, AST analysis, unit test execution.
- **Traffic Profile**: High burst frequency, heavy disk/file access, rapid token consumption.
- **Session Strategy**: Must **NEVER use sticky session**. Sticky routing on worker bursts exhausts single-account RPM/TPM immediately.
- **Provider**: Native Antigravity CLI (`python D:/Taadaa/tools/ag_cli.py fix/ask`) running directly on host.

---

## Worker Architecture: 4 Invariants for Multi-Account Stability

```
  [Coordinator Task]
          │
          ▼
   python ag_cli.py fix "..." --file "..."
          │
  ┌───────┴────────────────────────┐
  ▼                                ▼
[Pool State Check]        [LRU Profile Sorter]
Filter out active          Sort by: (last_used ASC,
cooldown profiles          calls ASC)
  │                                │
  └───────┬────────────────────────┘
          ▼
   [Atomic Lock Check] ──(O_CREAT | O_EXCL)──► [Success] ──► Bind Sandbox & Proxy ──► Run agy.exe
          │                                                                                 │
       [Busy]                                                                               ▼
          │                                                                        [Check Result]
          ▼                                                                         ├── OK: record_profile_usage
     Skip to next                                                                   └── 429: set exponential cooldown
     profile in LRU                                                                          + Jitter sleep + Failover
```

### Invariant 1: Least-Recently-Used (LRU) Load Balancing
- Profiles in `D:/Taadaa/agy_profiles/profiles_config.json` are sorted dynamically by `(last_used ASC, calls ASC)` from `pool_state.json`.
- Prevents traffic concentration on `acc_01` and spreads token usage across all 20+ accounts evenly.
- Successful executions invoke `record_profile_usage(name)` to update timestamps.

### Invariant 2: Atomic Exclusive Lease (`os.O_CREAT | os.O_EXCL`)
- Profile contention between concurrent sessions or background cronjobs is eliminated via atomic OS-level file creation (`.profile.lock`).
- Eliminates TOCTOU (time-of-check to time-of-use) race conditions present in read-then-write approaches.
- Leases include PID and timestamp; stale locks (>300s or non-existent PID via `psutil.pid_exists`) are safely evicted.
- **Fail-Closed Principle**: Unreadable or locked files fail closed (profile treated as busy, jumping to next candidate).

### Invariant 3: Exponential Backoff Cooldown & Jitter
- Detecting `RESOURCE_EXHAUSTED`, `429`, or `quota exceeded` triggers `set_profile_cooldown(name)`.
- Base cooldown: 1800s (30m). Exponential backoff: `1800s * min(4, 2**(hits-1))` (up to 2h).
- **Failover Jitter**: Random delay (5.0s–10.0s) between switching accounts to prevent Google burst correlation detection.

### Invariant 4: Sandbox & Proxy Isolation
- Each account profile directory (`D:/Taadaa/agy_profiles/acc_XX`) maintains:
  - Isolated `.gemini/installation_id` (independent UUID).
  - Isolated `AppData/Roaming`, `AppData/Local`, and `Temp` subdirectories.
  - Dedicated 4G proxy injected into `HTTP_PROXY` and `HTTPS_PROXY` environment variables.
- Execution uses native Go BoringSSL TLS in `agy.exe`, bypassing web proxy TLS fingerprints.

### Invariant 5: Structured Telemetry, Dynamic Configuration & Pre-write Validation
- **Structured JSONL Telemetry (`emit_telemetry`)**: Emits structured JSON events (`profile_dispatched`, `quota_failover`) with `correlation_id` and timestamp to trace execution lifecycles and monitor pool rotation across farm profiles.
- **Dynamic Environment Discovery**: Configuration relies on `os.environ.get(...)` with sensible fallbacks (`AGY_PROFILES_DIR`, `GPM_API_URL`, `OMNIROUTE_API_URL`, `GPM_PID`), eliminating fragile hardcoded paths, ports, or credentials.
- **Pre-write Validation & Rollback**: Validates credentials (`validate_credentials`) before provisioning and uses atomic temporary-file replacement (`.tmp` -> `replace`) to prevent corrupt profile states during unexpected interruptions.
- **Explicit Concurrency Testing**: The test suite includes multi-process contention verification (`test_profile_lock_two_process_contention`) asserting atomic single-winner locking under race conditions.

