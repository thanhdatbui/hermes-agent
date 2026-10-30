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

## GPM Profile Proxy Safety Invariant & Operator Direct-IP Protocol (Approach A)
- **Agent Enforcement:** Agent is 100% blocked from creating GPM profiles without a proxy (`guard_gpm_proxy.py` pre-tool hook on `terminal|execute_code`).
- **Operator Direct Exemption:** When direct IP is needed for primary personal Gmails, Operator creates profiles directly on the GPM desktop GUI. Agent is permitted to start and use existing direct profiles.
- **Deep Reference:** See `references/gpm-proxy-enforcement-mechanical-gate-and-operator-direct-rule.md`.
- **Farm Multi-Site Offloading & 1:2 Ratio Rebalancing:** See `references/farm-multisite-proxy-offload-and-ratio-rebalancing.md` for guidelines on filtering young/incubating accounts to offload 3:1 bottlenecked farm machines to remote multi-WAN proxy nodes.
- **MikroTik Sing-Box & Remote Proxy Routing:** See `references/mikrotik-singbox-tailscale-portproxy-bridge-architecture.md` for the rule prohibiting direct phone-to-WAN proxying, Sing-box fail-closed kill-switch, and bridging MikroTik to Tailscale via host Windows PortProxy.
- **SSOT Proxy Identity vs Mechanical Hop & ISP Session Ceilings:** See `references/ssot-proxy-identity-vs-mechanical-hop-and-isp-ceilings.md` for the rule requiring SSOT/Web Ledger to display true proxy destination identities (e.g. `tb.taadaa.click:51xx`), keeping local Sing-box translation transparent to the user, and respecting carrier PPPoE public session hard limits.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
