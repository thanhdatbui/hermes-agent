# Proxy preflight and mid-run verification

Use this reference when a TikTok registration appears to run despite a dead or unverifiable proxy.

## What the gate proves

Keep these states separate:

1. `tun0` exists and is UP: an Android tunnel/interface exists.
2. Android `VPN CONNECTED`: Android reports a connected VPN network.
3. ViChanger `GET_IP` returns `result=200` with a non-empty IP: the proxy path answered at that instant.
4. The returned IP differs from the direct host egress IP: the public egress was actually changed.

`VPN CONNECTED` alone is not proof of proxy health or IP substitution. A `result=0`, missing `data`, timeout, or empty IP must be treated as unverified/dead for a mapped device.

## How to explain a registration that still ran

Do not infer from the current source or from a single `CONNECTED` log line. First align timestamps and inspect the exact runtime/source version used by the batch.

- A one-time preflight can pass while the proxy dies afterward. Unless the registration flow performs a second gate immediately before the sensitive registration action, it can continue after the proxy becomes unhealthy.
- A later live `GET_IP` failure proves the proxy is unhealthy at the later probe time; it does not prove it was unhealthy at the earlier registration preflight.
- If the preflight really receives `result=0` and the script still proceeds, inspect whether the batch disabled live-IP verification, used stale/different `automation-core`, or logged a status string without checking the boolean `allowed/connected` result.
- Current `automation_core.preflight.require_android_vpn` is fail-closed when `verify_live_ip=True`: it raises on failed `GET_IP`. The consumer wrapper must not replace that boolean/error decision with a permissive string check.

## Evidence required in reports

For every mapped target, capture and correlate:

- timestamp and target serial;
- `tun_up` and Android VPN state;
- `GET_IP` result, returned IP (redacted only if sensitive), retry count, and error;
- direct host egress IP captured at a comparable time;
- source commit/runtime interpreter and `TIKTOK_REG_VERIFY_LIVE_IP` value;
- whether a second preflight ran immediately before registration.

The normal success log should include a structured preflight artifact, not only `vpn preflight: CONNECTED`. A later proxy watchdog cannot retroactively prove the earlier egress path.

## Safe debugging sequence

1. Read-only inspect the exact batch log around the target's preflight and registration start.
2. Read-only inspect the historical source/commit and runner environment used at that timestamp.
3. Confirm whether the target was mapped to a non-empty proxy; an unmapped target may legitimately skip the VPN gate.
4. Compare `GET_IP` and direct host IP evidence at matching timestamps.
5. If evidence is incomplete, report `UNVERIFIED` rather than claiming the IP was changed.
6. Do not rerun, reassign proxy, restart ADB, or modify the device while investigating unless the user explicitly asks.

## Common log interpretation

- `BLOCK VPN_PREFLIGHT_BLOCKED ... GET_IP failed`: the fail-closed gate worked.
- `vpn preflight: CONNECTED` followed by `preflight_phase passed`: the gate passed at that moment; it is not a lease for the rest of the run.
- `MACHINE_IN_USE`: that invocation did not proceed into device registration, even if its preflight line exists.
- A later `GET_IP result=0`: current/later proxy failure; correlate against the earlier preflight before assigning root cause.
