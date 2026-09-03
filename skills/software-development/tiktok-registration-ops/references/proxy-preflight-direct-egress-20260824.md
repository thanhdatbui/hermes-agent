# Proxy preflight incident pattern (2026-08-24)

## Root cause pattern
A registration gate may report `CONNECTED` while the device is not proven to egress through its assigned proxy. Keep these signals separate:

- `tun0` UP = local tunnel exists.
- Android VPN `CONNECTED` = VPN agent reports connected.
- ViChanger `GET_IP result=200` with `data="..."` = the broadcast returned a non-empty IP-shaped value.

The third signal alone does **not** prove that the value is proxy egress, differs from direct egress, is fresh, or is not cached. A route table with the default route on Wi-Fi while `tun0` only carries selected routes is a warning sign, not proof of proxy egress.

## Registration adapter contract
For a mapped serial:

1. Resolve mapping with shared `serial_is_mapped_in_workbook(...)` and header aliases; do not use positional `row[1]`/`row[2]` inference.
2. Force `verify_live_ip=True`; do not allow a registration env flag to disable it.
3. Require `allowed=True`, `connected=True`, and non-empty `proxy_ip`; never accept the status string `CONNECTED` alone.
4. Log redacted status plus `proxy_ip` and an artifact/timestamp reference. Never log proxy credentials, OTP, or account secrets.
5. If the required contract is proxy-vs-direct proof, independently measure direct/host egress or query a trusted proxy-side endpoint and compare. `GET_IP result=200` alone is insufficient.
6. On failure, stop before opening TikTok. Use bounded recovery/recheck only where the flow already provides that adapter.

## Historical audit rule
Do not claim a historical run used a fake IP from `vpn preflight: CONNECTED` alone. Require the actual returned IP and evidence that it was proxy egress. If the historical artifact omitted the IP, report the run as unverified.

## Scope-aware dirty worktrees
A dirty repository is not automatically a blocker for a scoped fix. Inspect status and the target-file diff first. Preserve unrelated dirty files; block only if dirty changes overlap the edit, make verification unsafe, or explicit repository rules require cleanliness. Report unrelated dirty files without treating them as a blocker when a non-conflicting scoped patch is authorized.
