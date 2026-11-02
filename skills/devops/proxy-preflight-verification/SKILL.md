---
name: proxy-preflight-verification
description: Verify Android tunnel, VPN state, proxy liveness, and real egress IP for device automation; diagnose why a registration proceeded after an apparently successful preflight.
---
# Proxy Preflight Verification

Use for mapped Android devices, TikTok registration, proxy/VPN watchdogs, and any incident where a `CONNECTED` log conflicts with a dead proxy or direct egress.

## Core model

Never collapse these into one boolean:

1. `tun0` exists and is UP: the tunnel interface exists.
2. Android reports VPN `CONNECTED`: the VPN network agent is connected.
3. ViChanger `GET_IP` returns `result=200` plus a non-empty IP: the configured proxy path answered at that instant.
4. The returned public IP differs from a direct host egress probe: the traffic actually exits through a different public IP.

`VPN CONNECTED` is not proof of proxy liveness or IP substitution. `result=0`, missing `data`, timeout, or empty IP is unverified/dead for a mapped target.

## Incident workflow

1. Read the target's exact batch log around preflight and registration start.
2. Align timestamps before drawing conclusions. A current failure does not prove an earlier failure.
3. Inspect the historical source commit, interpreter, runner environment, and live-IP flag used at that timestamp; do not use only today's source.
4. Confirm the target was actually mapped to a non-empty proxy. An unmapped target may legitimately skip the required gate.
5. Inspect the preflight implementation and wrapper. A fail-closed shared helper may raise correctly while a consumer wrapper can still log a permissive status string or ignore the boolean/error decision.
6. Determine whether verification was one-shot. A preflight pass is a point-in-time observation, not a lease; if the proxy dies later, the flow needs a second gate immediately before registration.
7. Compare proxy-returned IP and direct host IP from comparable timestamps. If either is missing, report `UNVERIFIED`, not “fake IP confirmed”.

## Required evidence

For every mapped target, preserve a redacted structured record containing target/serial, timestamp, `tun_up`, Android VPN state, `GET_IP` result, returned IP, retry count, error, direct host egress IP, interpreter/runtime, source revision, live-IP flag, and whether a second preflight ran.

Logs saying only `vpn preflight: CONNECTED` are insufficient. A later watchdog result cannot retroactively prove the earlier egress route.

## Safe behavior

Investigation is read-only by default: do not reassign proxy, restart ADB, restart VPN, clear app data, rerun registration, or alter the device unless explicitly requested. Redact proxy credentials, tokens, OTPs, email passwords, and other secrets.

For a mapped device, a failed live-IP check must fail closed. Do not weaken the gate to tunnel-only status. If the evidence is incomplete, stop the target and report the exact missing proof.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
