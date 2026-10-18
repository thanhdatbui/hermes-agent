---
name: farm-network-gate-contract
description: "Use when designing farm Wi-Fi/proxy safety gates."
version: 1.0.0
category: automation
tags: [farm, wifi, proxy, ssot, fail-closed, device-lock, evidence]
---

# Farm Network Gate Contract

Use this skill when a multi-device Android farm needs reliable Wi-Fi assignment, proxy mapping, recovery, or a guard against ad-hoc network changes. The goal is not merely to reconnect a phone: it is to make a wrong SSID/PSK/proxy mapping mechanically difficult or impossible.

## Design principles

1. **Single source of truth (SSOT).** Wi-Fi groups and proxy mappings are authoritative data, not caller-supplied strings. Keep Wi-Fi credentials and proxy endpoints in separate sources. Never infer a profile from the currently connected SSID.
2. **One canonical mutation primitive.** Expose an API shaped like `apply_profile(machine)`; the caller supplies only the machine identifier. The primitive resolves SSID, security, credential reference, subnet, and proxy endpoint from validated data. Reject caller-supplied SSID, PSK, host, or port.
3. **O(1) resolution after load.** Validate ranges once, reject overlaps/gaps and missing fields, then build an indexed `machine -> profile` map. Unknown or ambiguous machines fail closed; there is no fallback group and no guessed credential.
4. **Lock before mutation.** Acquire the machine/device lock before any write, reboot, profile removal, or join operation. Confirm serial provenance independently. A busy lock means untouched and blocked, not forceful takeover unless the operator explicitly authorizes preemption.
5. **Idempotency.** Read current state first. If the expected Wi-Fi, L3 route, and proxy are already healthy, return `NO_OP` without disrupting a running session.

## Required gate sequence

```text
validate SSOT
  -> resolve machine/profile/serial
  -> acquire device lock
  -> read current state and decide NO_OP vs apply
  -> apply exact resolved profile
  -> verify L2 Wi-Fi
  -> verify L3 address/route/gateway
  -> verify L4 proxy
  -> write sanitized evidence
  -> release lock
```

The sequence is one-way: if a gate fails, do not run downstream checks or change another layer to hide the failure.

## Layered verdicts

### L2: Wi-Fi association

Verify expected SSID/BSSID policy, association state, reason code, RSSI/link rate, and the absence of an unwanted active profile. `MIC failure`, `4-way handshake failure`, association rejection, or wrong-password disablement is `L2_AUTH_FAIL`/`FINAL_BLOCKED`. Do not try alternate passwords, roam to another farm group, or loop radio toggles.

### L3: IP, DHCP, and routing

Verify a farm-subnet IPv4 address, the expected gateway, default route on the Wi-Fi interface, and gateway reachability. Missing IP/route is `L3_NO_IP` or `L3_NO_GATEWAY`; it is not a proxy failure. A stale/static profile must be treated as a profile-state issue and verified after rebind.

### L4: Proxy

Only after L2 and L3 pass, verify the machine's resolved proxy endpoint, TCP connectivity, proxy authentication/HTTP status, and egress policy. A 407/502 or wrong port is an L4 verdict; never “fix” it by changing Wi-Fi.

## Fail-closed and anti-hardcode rules

- Unknown machine, serial mismatch, missing/changed profile hash, missing lock, mismatch on readback, or incomplete evidence => `FINAL_BLOCKED`.
- Never hardcode a group credential from memory or reuse a neighboring group’s password. Do not print PSKs in argv, logs, screenshots, reports, or exceptions.
- Add static lint/guard coverage that rejects literal SSID/PSK connection commands outside the canonical primitive.
- Auth/MIC failures have a bounded attempt policy; after the first confirmed credential failure, preserve evidence and stop rather than retrying a wrong configuration.
- Do not reboot AP/router, change transmit power, or move a phone between groups as an automatic response.

## Two-tier conflict verification protocol

Before authoring or modifying any gate, guard hook, or network script, verify against both tiers:

1. **Tier 1 — Existing system guards:**
   - `guard_android_proxy.py`: Android `http_proxy` MUST be RFC1918 LAN IP (`192.168.110.2:<port>`), never domains or public IPs.
   - `guard_cronjob_safety.py`: Windows subprocesses MUST include `creationflags=0x08000000` (`CREATE_NO_WINDOW`) or `-w hidden`.
   - `guard_device_bulkhead.py` & Hard Gate #5: ADB commands MUST include explicit `-s <serial>` and run inside `operator_device_lock`.
   - Codebase safety: strictly forbid broad disk sweeps (`os.walk`, `glob(recursive=True)`, `find`, `grep -r`), never edit protected system hook files.
2. **Tier 2 — Operator farm invariants:**
   - Direct exceptions: M67 and M69 are direct (`http_proxy` `:0`, bypass local Sing-box proxy).
   - Rescue override: allow `force_preempt=True` in `operator_device_lock` during emergency machine rescues.
   - Nurture protection: return `NOOP_HEALTHY` when current state matches expected to avoid breaking active 25-worker TikTok sessions.
   - Network hierarchy: Sing-box LAN only, strictly no VPN, Ruijie > Aruba.
   - Verification suite: 100% offline mocked tests running under 30s.

## Control loop and anti-silent-loop discipline

- **Hard-stop on policy blocks:** When an action trips a guard, bulkhead, or permission check, STOP immediately. Never write ad-hoc scripts to bypass a guard.
- **Bounded retries (Circuit Breaker):** Max 2 attempts on a structural failure. On the 2nd failure, stop and report `BLOCKED` with evidence.
- **Mandatory progress reporting:** Never leave the operator in a silent loop exceeding 3 minutes during multi-step background work. Always emit a heartbeat.
- **Definitive completion:** Every task must terminate in one of four valid states: `SUCCESS`, `FAILED`, `BLOCKED`, or `NEEDS_OPERATOR`. Never allow unbounded or hanging states.

## Evidence and rollout

Each apply/readback record includes machine, serial, profile ID, profile hash, expected-vs-actual values, timestamp, lock ID, layer verdicts, and sanitized raw output. A screenshot is required for UI evidence and must be visually inspected before delivery.

Roll out in this order: read-only dry run; one idle canary per Wi-Fi group; verify complete L2→L3→L4 evidence; expand one group at a time; stop the first failing group; enable enforcement only after the canary matrix is green. Never infer whole-farm success from a single canary or launcher exit code.

## Minimum offline test matrix

Cover overlapping/gapped ranges, unknown machines, duplicate serials, changed profile hash, busy lock, caller-supplied SSID/PSK rejection, auth failure without retry, no IP, wrong gateway/route, wrong proxy port, proxy 407/502, readback mismatch, and healthy-profile no-op.

## Android legacy notes

For older Samsung Android builds (e.g. Galaxy S7 running Android 8):
- **Stale profile sweep beyond ID 10:** Android retains stale Wi-Fi networks with IDs >= 10 (e.g. ID 10, ID 11). If a stale network was marked `blackListed` with `NETWORK_SELECTION_DISABLED_AUTHENTICATION_FAILURE`, hardcoded sweeps like `range(10)` miss it and cause false L2 auth-fail blocks. Always parse all configured IDs from `dumpsys wifi` (`ID: (\d+)`) and sweep `set(range(30)) | ids` via `service call wifi 14 i32 <ID>`.
- **ICMP ping `-I wlan0` failure on non-root:** On Android 8 non-root, running `ping -c 1 -W 3 -I wlan0 <IP>` fails with `Permission denied` or `connect: Network is unreachable` (returncode 2). Always ping without `-I` and fallback to TCP probes (`toybox nc` to Gateway port 80 or Sing-box proxy port `20000 + machine`) when ICMP is blocked or unsupported by router/OS.
- **`toybox nc` syntax compatibility:** Android toybox netcat does NOT support `-z` (which BSD nc uses). Use `toybox nc -w 3 -W 3 <host> <port> < /dev/null` or `-w 2 -q 0 <host> <port>`.
- **Post-association DHCP stall remediation:** In older devices, WPA2 association may complete (`<BROADCAST,MULTICAST,UP,LOWER_UP> state UP`) but Android fails to acquire IPv4 (only link-local IPv6 `fe80::...`). Implement `_renew_dhcp(serial)` (`dhcpcd -n wlan0`, toggle `svc wifi disable` -> `sleep 1` -> `svc wifi enable`), extend polling (`IP_POLL_ATTEMPTS = 10, IP_POLL_INTERVAL = 2.0s`), or fall back to static IP mapping from farm topology.
- **Anti-Paralysis / Anti-Whining Invariant (User Mandate):** Operator strictly forbids passively stopping at `BLOCKED` and crying/giving up. When a gate layer fails (e.g. `L3_NO_IP`), Coordinator MUST proactively extract physical evidence (`dumpsys wifi`, `ip addr show wlan0`, `logcat`), identify the root physical layer, and propose/execute deterministic remediation.

## References

- `references/s7-android8-wifi-stack-quirks-and-dhcp-remediation.md` — Samsung S7 Android 8 quirks: stale network IDs >= 10, non-root ping -I socket errors, toybox nc syntax without -z, DHCP renewal, and anti-paralysis protocol.
- `references/network-gate-contract-and-m7-lesson.md` — the validated design review, failure pattern, and acceptance contract from the M7 incident.
- `references/two-tier-conflict-protocol-and-anti-silent-loop.md` — two-tier conflict verification protocol, operator invariants, anti-silent-loop control rules, and Advisor Sol streaming TTFT insight.
- `references/farm-network-gate-production-implementation-and-review-audit.md` — production implementation of farm_network_gate.py, resolution of 3 Claude Reviewer blocking findings, 36/36 tests, and live canary evidence.
