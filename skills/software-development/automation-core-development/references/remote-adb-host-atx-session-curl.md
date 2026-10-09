# Remote ADB Host ATX Session Dump Invariant & Device-Local Curl

## Context & Symptoms
When automating Android devices via a remote ADB host (e.g. Admin cluster `192.168.110.119:5037` or farm machines 201-280):
- `adb forward tcp:0 tcp:7912` allocates a port on the remote machine's loopback, but network firewalls or loopback bindings prevent Python on the control machine from directly connecting via `http://<remote_host>:<forwarded_port>/...`.
- Attempting HTTP requests across LAN to forwarded ports fails with connection timeouts, ECONNREFUSED, or transport drops.

## Durable Patterns & Invariants

1. **Device-Local Curl via ADB Shell:**
   - The ATX agent binary on the device (`/data/local/tmp/atx-agent`) contains an embedded `curl` applet:
     ```bash
     /data/local/tmp/atx-agent curl -s -X POST -d '<payload>' http://127.0.0.1:7912<endpoint>
     ```
   - Invoking this via `adb.shell([...])` routes entirely through ADB transport, executing directly on device localhost and bypassing all host-to-host LAN networking and firewall limitations.

2. **Parsing ATX Embedded Curl Output:**
   - `atx-agent curl` may prepend log prefixes (e.g. `curl.go: ...`) or response headers to stdout.
   - When extracting JSON or XML responses from stdout:
     - Search for the boundary of `{` or `<?xml` / `<hierarchy`, or strip non-JSON header lines before parsing.

3. **`_resolve_host` Precedence Invariant:**
   - In `persistent_ui.py`, `_resolve_host(adb)` must evaluate `adb.host` before checking global/cached request hosts.
   - Global mutable variables like `_ACTIVE_REQUEST_HOST` can leak across unit test runs (e.g. `test_resolve_host_resolution`), causing assertions expecting a specific adb instance's host to return stale cached values (`localhost` instead of target IP).
