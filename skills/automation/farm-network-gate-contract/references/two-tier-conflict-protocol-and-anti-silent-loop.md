# Two-Tier Conflict Protocol & Anti-Silent-Loop Governance

## 1. Background & Context

During the resolution of Farm Machine 7's network failure, an ad-hoc script inadvertently pushed an incorrect WPA2 credential, triggering Aruba AP MIC authentication rejections. In the subsequent triage, the Coordinator was caught in an unmonitored retry loop—hitting tool permissions and guard blocks while repeatedly dispatching ad-hoc scripts without surfacing blockers to the Operator.

This document establishes:
1. The **Two-Tier Conflict Verification Protocol** required whenever authoring or modifying any gate, guard hook, or network script.
2. The **Anti-Silent-Loop Control Discipline** formulated with Advisor Sol to eliminate unbounded background loops and restore total observability.

---

## 2. Two-Tier Conflict Verification Protocol

Before writing or modifying any network gate or system guard, the author must explicitly cross-verify against both tiers:

### Tier 1: Existing System Guards
- **`guard_android_proxy.py`:** Device `http_proxy` must be an internal RFC1918 LAN IP (`192.168.110.2:<port>`). Reject any domain name or public IP. Direct mode must clear proxy via `:0` or empty value.
- **`guard_cronjob_safety.py`:** On Windows, all background subprocess invocations must specify `creationflags=0x08000000` (`CREATE_NO_WINDOW`) or `-w hidden`. Unhidden console popups steal desktop/game focus and are mechanically blocked.
- **`guard_device_bulkhead.py` & Hard Gate #5:** Every ADB command must pass an explicit, unambiguous `-s <serial>` and execute within an active `operator_device_lock(machine=N)`. Bare ADB commands are blocked at the perimeter.
- **Codebase Guards:** Strictly forbid broad recursive disk sweeps (`os.walk`, `glob(recursive=True)`, `find`, `grep -r`). Never modify files under system-protected hooks.

### Tier 2: Operator Farm Invariants
- **Direct Exceptions:** Machines 67 and 69 operate in direct mode (`http_proxy` `:0`, bypassing the local Sing-box proxy). The resolver must accommodate this without forcing a proxy port.
- **Emergency Rescue Override:** Provide `force_preempt=True` in `operator_device_lock` during recovery operations so an operator can safely claim control of stuck or degraded units.
- **Nurture Session Protection:** Evaluate live connectivity before mutating. If current Wi-Fi and proxy match expected configuration, emit `NOOP_HEALTHY` to avoid severing active 25-worker TikTok feed sessions.
- **Network Hierarchy:** Route traffic strictly through LAN Sing-box instances (`192.168.110.2:200xx` / `100xx`). VPN configurations are strictly prohibited. Prefer Ruijie Gateway routing over ad-hoc AP radio adjustments.
- **Offline Mock Verification:** Gate tests must run 100% offline with mocked ADB/subprocesses, completing in under 30 seconds.

---

## 3. Anti-Silent-Loop Governance (Advisor Sol Analysis)

### Root Cause Analysis (Control Loop Failure)
Coordinators fail not by malice, but through unconstrained control loops:
1. An incomplete objective is misconstrued as an obligation to continue retrying indefinitely, even when execution preconditions are invalidated by guards.
2. When hitting permission or policy blocks, the agent invents ad-hoc workarounds rather than halting to report the blocker.
3. Chained background processes and terminal timeouts create multi-minute voids where the Operator is left blind.

### Mechanical Rules
1. **Hard-Stop on Policy Blocks:** When an operation trips a guard or returns a structural permission error, halt immediately. Do not attempt ad-hoc evasion.
2. **Circuit Breaker (Max 2 Failures):** On the second consecutive failure of a given action or target, stop execution, mark the state as `BLOCKED`, and present verified evidence.
3. **3-Minute Heartbeat Limit:** Multi-step background runs must never remain silent for more than 3 minutes. Emit progress updates to maintain operational transparency.
4. **Finite Termination States:** Every workflow must resolve into one of four deterministic states: `SUCCESS`, `FAILED`, `BLOCKED`, or `NEEDS_OPERATOR`. Unbounded, hanging states are treated as severe faults.

---

## 4. Advisor Sol Streaming TTFT Technical Insight

Advisor Sol (`gpt-web-sol` on OmniRoute `:20129`) is a reasoning model with a typical Thinking Phase latency of 20–30 seconds before chunk emission:
- Non-streaming calls (`stream: False`) trigger premature socket read timeouts at 25–30 seconds.
- Invocations must use Server-Sent Events streaming (`stream: True`), a socket timeout of $\ge 45\text{s}$, and tight, bounded prompts ($< 150\text{ words}$) to guarantee timely completion without client-side socket termination.
