# Hardware Proxy Auto-Healing & Anti-Flapping Patterns

## Context & Problem Statement
Automated healers for 4G/LTE mobile proxy pools (e.g. MobiProxy boxes, USB dongle farms) probe port liveness and issue redial/recreate commands (e.g. `/proxy_recreat?proxy=host:port`). Without defensive rate-limiting and locking, several failure modes emerge:

1. **Cron Overlap / Instance Multiplication**:
   - A health check cycle that takes longer than the cron interval (e.g. 60s) spawns a second instance while the first is waiting for modems to redial.
   - Multiple instances bombard the proxy box simultaneously, corrupting state and triggering cascading timeouts.

2. **Flapping / Premature Re-triggering**:
   - 4G LTE modems require 10–20 seconds to detach from the base station, negotiate a new cellular bearer, and obtain a public IP.
   - If a script checks health 10 seconds later and sees the modem still down, it triggers redial *again*, trapping the modem in an endless reset loop ("flapping").

3. **Reset Storms (SIM Box / Controller Overload)**:
   - When a base station blip or network re-route causes 15–20 modems to disconnect simultaneously, firing 20 parallel redial commands overwhelms the embedded controller and base station interface.

---

## The Four Anti-Spam Guardrails

### 1. Single-Instance Lock
Use kernel-level non-blocking file locking (Windows `msvcrt.locking(fileno, msvcrt.LK_NBLCK, 1)` or Unix `fcntl.flock`).
- Exit cleanly with code 0 if the lock is held by an ongoing scan.
- Never use naive file-existence checks (`if os.path.exists(...)`), which leave orphan files after ungraceful termination or host reboots.

### 2. Per-Target / Per-Port Cooldown (e.g. 300s / 5 minutes)
Track `last_heal_time` persistently in a statistics or state file (`mobiproxy_stats.json`).
- Before issuing a recreate/reboot command for port $P$:
  ```python
  if last_heal_time and (now - last_heal_time).total_seconds() < COOLDOWN_SECONDS:
      logger.info(f"[COOLDOWN] Port {port} healed recently ({remaining}s left). Skipping to allow stabilization.")
      continue
  ```
- This guarantees the modem has adequate time to establish a stable PDP context without being re-interrupted.

### 3. Max Heals Cap per Scan Cycle (e.g. Max 4 Ports)
Cap the number of redial commands executed in a single cycle:
```python
MAX_HEALS_PER_RUN = 4
eligible_dead_ports = [r for r in dead_results if not is_in_cooldown(r.port)]
heals_to_run = eligible_dead_ports[:MAX_HEALS_PER_RUN]
if len(eligible_dead_ports) > MAX_HEALS_PER_RUN:
    logger.warning(f"Throttling: {len(eligible_dead_ports)} ports dead, capping to {MAX_HEALS_PER_RUN} heals this cycle.")
```
- Remaining dead ports will be handled in subsequent cycles once earlier ports have recovered or entered cooldown.

### 3b. Cron Interval Must Exceed Full Heal Cycle Duration
If a cron fires every 1 minute but one full scan+heal cycle takes 3–8 minutes (32 ports × 15s HEAL_WAIT_TIME), the healer stacks up **multiple simultaneous instances**. The Single-Instance Lock is the safety net, but the root fix is to set cron interval ≥ expected cycle duration:
- With 32 ports, MAX_HEALS_PER_RUN=4, HEAL_WAIT_TIME=15s, HEAL_API_DELAY=2s → worst-case single-run ≈ 4×(15+2)s + scan overhead ≈ 90s+ → set cron to `*/5 * * * *` (5 min), not `*/1`.
- Pattern: `cron_interval > (MAX_HEALS_PER_RUN × (HEAL_WAIT_TIME + HEAL_API_DELAY)) + api_scan_overhead`.

### 4. Inter-API Request Spacing (e.g. 2.0s)
Add an intentional sleep (`time.sleep(HEAL_API_DELAY)`) between recreate commands sent to the hardware controller.
- Avoids HTTP request burst drops and race conditions inside the embedded modem management daemon.

---

## MobiProxy Box Web UI Access — Common Pitfalls

### HTTP-only, Chrome auto-upgrades to HTTPS
The MobiProxy management web UI (`test.taadaa.click`) runs plain HTTP on port 80, **no HTTPS**. Browsers (especially Chrome) auto-upgrade bare hostnames/domains to `https://`, producing `ERR_CONNECTION_REFUSED` (port 443 refused).
- **Fix:** Always type the full scheme: `http://test.taadaa.click` — never let the browser auto-fill.
- Port 80 GET returns `302 Found → /login.php` = box is online. Port 443 timeout or refused = browser scheme issue, not box down.

### DDNS hostname, not static IP
`test.taadaa.click` is a DDNS entry pointing to the box's **current 4G WAN IP**, which changes on each modem reset/redial. Do not treat the resolved IP as stable — always use the hostname. Verify with `nslookup test.taadaa.click`.

### Management API vs Proxy Port availability are independent
The box management API (port 80, `/proxy_getlist`, `/proxy_recreat`) can respond normally even when all 32 proxy ports (5101–5138) are TCP-refused. The Nginx/PHP management plane runs separately from the 3proxy/modem pool. Check both independently.

### Web UI hangs when healer is spamming API
When the healer script is sending dozens of concurrent `/proxy_recreat` requests, the embedded PHP/nginx backend saturates → the web UI returns `302` initially but then hangs on subsequent requests. Stopping the healer restores UI responsiveness within seconds.

### Primary Port (Port 1 / proxy01) DDNS Coupling & Cascading Reset Trap
In embedded multi-modem boxes (e.g. OpenWrt + Cloudflare DDNS on `test.taadaa.click`), the box's default gateway and DDNS updater are often bound to the interface of the **first modem (Port 1 / proxy01)**:
- **Coupling Proof**: `nslookup test.taadaa.click` and `proxy01` share the exact same public WAN IP (e.g. `171.240.99.104`), while ports 5102..5138 have independent cellular IPs.
- **Cascading Failure Mechanism**: Resetting Port 1 drops the default gateway and freezes DDNS. Probing other ports via the domain during this window results in 100% timeouts. The healer misinterprets all ports as dead and fires sequential reset requests to every modem, crashing the controller.
- **Defense Rules & 2-Tier Hard Guard Architecture**:
  1. **Two-Tier Hard Guard (`PROTECTED_HEAL_PORTS = {5101}`)**:
     - **Tier 1 (Client Guard)**: In `MobiProxyClient.recreate_proxy(port)`, if `port in PROTECTED_HEAL_PORTS`, immediately raise `ValueError` and log `[PROTECTED]`. Never construct or send the `/proxy_recreat` HTTP request.
     - **Tier 2 (Scanner / Healer Loop Guard)**: In `run_scan`, when iterating `dead_results`, filter out any `dead_res.port in PROTECTED_HEAL_PORTS` with a `[PROTECTED]` log and `continue` before checking cooldowns or appending to `to_heal`.
     - **Secondary Catch**: Wrap `recreate_proxy` in `try ... except ValueError` in the heal loop so even unintended invocations fail safe without crashing the daemon.
  2. **Domain/Gateway Preflight**: Watchdogs must verify root domain reachability before port-level evaluation. If root probe fails, abort the cycle immediately rather than marking ports dead.

## 2-Layer Health Verification Architecture
API responses from proxy hardware often suffer from **stale status traps**:
- **Layer 1 (Management API)**: Query `/proxy_getlist` or `/proxy_check`.
  - API may report `status: "true"` because the modem daemon process is running, but the WAN link or port forwarder has hung.
- **Layer 2 (Direct TCP Socket Probe)**: Run `socket.connect_ex((host, port))` with a short timeout (1.5s).
  - Catches the false-positive trap where API reports healthy but the TCP listener is dead/unresponsive.
- **Post-Heal Verification**: Wait `HEAL_WAIT_TIME` (15s), then probe both TCP connectivity and an external IP reflection service (`api.ipify.org` through the proxy with basic auth) to confirm true WAN egress routing.

---

## Unit Testing Multi-Port Cluster Healers & Mocking Pitfalls

When authoring unit tests (e.g. `test_mobiproxy_protect_5101.py`) for cluster health scanners with caps (`MAX_HEALS_PER_RUN`) and 2-layer verification:

### 1. The Missing Ports Cluster-Cap Trap
- **Trap**: Mocking only the target test ports in `get_proxy_list` (e.g. only 5101 and 5107). All other ports in `KNOWN_PORTS` lack API data, causing Layer 1 to evaluate all 30 remaining ports as DEAD (`api_status='none'`, empty IP).
- **Consequence**: `MAX_HEALS_PER_RUN` (e.g. 4) immediately caps healing to the first eligible ports (5102..5105). The target test port (5107) gets deferred, causing `res.heal_attempted` assertion to fail (`False is True`).
- **Fix**: Always populate the mock API list for **all** cluster ports (`KNOWN_PORTS`), setting non-target ports to `status: "true"` with dummy IPs so only the intended test ports fail Layer 1/2.

### 2. Post-Heal Verification Re-Probe Statefulness
- **Trap**: Using a static mock for `probe_tcp_port` that always returns `False` for the tested dead port.
- **Consequence**: During post-heal verification, `probe_tcp_port` is invoked a second time. If it still returns `False`, `res.heal_success` is marked `False` and an error is logged.
- **Fix**: Use a stateful mock or call-count tracker (e.g. `nonlocal probe_calls`) so that the initial probe returns `False` (port dead), and subsequent post-heal probes return `True` (port recovered).

