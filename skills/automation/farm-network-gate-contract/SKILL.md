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

## Evidence and rollout

Each apply/readback record includes machine, serial, profile ID, profile hash, expected-vs-actual values, timestamp, lock ID, layer verdicts, and sanitized raw output. A screenshot is required for UI evidence and must be visually inspected before delivery.

Roll out in this order: read-only dry run; one idle canary per Wi-Fi group; verify complete L2→L3→L4 evidence; expand one group at a time; stop the first failing group; enable enforcement only after the canary matrix is green. Never infer whole-farm success from a single canary or launcher exit code.

## Minimum offline test matrix

Cover overlapping/gapped ranges, unknown machines, duplicate serials, changed profile hash, busy lock, caller-supplied SSID/PSK rejection, auth failure without retry, no IP, wrong gateway/route, wrong proxy port, proxy 407/502, readback mismatch, and healthy-profile no-op.

## Android legacy notes

For older Samsung Android builds, prefer the platform-supported/canonical join helper and explicit shell quoting for SSIDs containing spaces. Do not assume modern `cmd wifi` subcommands exist. Any device-specific fallback must remain inside the canonical primitive, be locked, bounded, and followed by independent readback.

## References

- `references/network-gate-contract-and-m7-lesson.md` — the validated design review, failure pattern, and acceptance contract from the M7 incident.
