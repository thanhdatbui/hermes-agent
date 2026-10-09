# Mass-Failure Diagnostic: Proxy-First Rule

## Rule (User correction 09/09/2026)

When a batch alert shows **>5 machines failing with the same error** (especially `profile username still mismatched after switch`):

**CHECK PROXY FIRST — DO NOT DEBUG CODE.**

## Why This Matters

TikTok's account switcher requires active network egress to validate the session switch. When upstream MobiProxy dies:
1. Switcher opens normally (TCP to Sing-box 200xx is always OPEN)
2. Tap lands correctly on the target account row
3. TikTok attempts to validate the session switch server-side
4. Network request fails (502/RESET/TIMEOUT)
5. TikTok silently refuses to switch → profile stays on old account
6. Runner reports `profile username still mismatched after switch`

**The tap coordinates, switcher UI, and code logic are ALL correct.** The failure is at the network layer.

## Diagnostic Steps

1. **Scan Sing-box cluster**: `python scan_singbox_farm_proxies.py --host 192.168.110.2 --workers 30`
2. **Or quick TCP+HTTP probe** on the affected machines' Sing-box ports (20000+M)
3. If >30% ports show 502/RESET/TIMEOUT → **proxy is the root cause**
4. **Heal upstream ports** (51xx, NOT 200xx!) via MobiProxy `proxy_recreat` API
5. Wait 15-30s for modem reconnection
6. Retry failed ports (many succeed on 2nd try)
7. **Only after proxy is confirmed alive**, re-run the batch

## What NOT to Do

- ❌ Don't modify tap coordinates / switcher logic when proxy is dead
- ❌ Don't use Sing-box ports (200xx) with `proxy_recreat` API (returns 422)
- ❌ Don't dispatch worker subagents to debug code when >10 machines fail simultaneously
- ❌ Don't assume "TikTok bug" when the infrastructure is down

## Real-World Example

Session 09/09/2026: 21/79 machines (26.6%) failed with `profile username still mismatched after switch`. Coordinator spent 3 dispatch rounds debugging tap coordinates before user said "k phải k chuyển đc nick, mà do proxy sập, đã điều tra ra". After scanning: **23/26 affected ports were dead** (10× 502, 13× RESET/TIMEOUT). Heal restored 17/18 ports. No code changes needed.
