# Operational Closeout Gate Rubric for Farm Wi-Fi Remediation

When closing an operational remediation session that contains no new git codebase commits, `closeout_gate.py` must be invoked via `--input <audit_package.md> --json-output`.

## 1. Sol Auditor Scorecard Rubric Expectations (>= 85 pts)
Sol Auditor evaluates operational closeout packages across 5 rubrics. If any of the following artifacts are missing, the score is penalized to 75–84/100 (REJECTED):

1. **Raw Logcat Proof (Logic & Observability)**:
   - Provide concrete, before-and-after logcat excerpts from a verified canary device (e.g. M221).
   - Before: `D adbjoinwifi: SSID: admin` -> failed association -> roamed to rogue SSID (`mWifiInfo: [SSID: Dat, Net ID: 2]`).
   - After: `D adbjoinwifi: SSID: admin 1` -> `Device Connected to admin 1` -> `mWifiInfo: [SSID: admin 1, Net ID: 1, Supplicant state: COMPLETED]`.

2. **100% Farm Device Accounting (Coverage & Safety)**:
   - Never report partial counts without classifying remaining devices.
   - For a 160-device dual cluster: explicitly report verified online devices (e.g. 154/154 with `dat_still_saved: false` and valid `192.168.110.x` IP).
   - For all offline devices (e.g. 6/160), enumerate exact machine numbers and hardware serials, identify the physical root cause (USB cable/ADB drop), and provide a fail-safe risk assessment (e.g. offline phones cannot leak traffic; periodic watchdog auto-heals them upon reconnect).

3. **Automated Verification Test Suite (Test Evidence)**:
   - Include an executable unit test suite (`pytest`) testing the core remediation invariants:
     * Mapping of machine index to fixed SSID/password.
     * Regex extraction of rogue Net ID from `dumpsys wifi`.
     * Regex validation of allowed farm subnets (`192.168.110.x`, `192.168.10.x`).
     * Shell quoting formatting preventing whitespace splitting.
     * Auto-healer fail-safe behavior for reconnected offline devices.
   - Report exact pytest results (e.g. `5 passed in 11.83s`).

4. **Timeline & Incident Isolation**:
   - Provide explicit timestamps proving that production job failures (e.g. 40 machines blocked-proxy in Shift 3) occurred during the rogue SSID window *before* the remediation ran.
   - Show that after remediation, proxy ports are 100% open and device-to-gateway ping achieves 0% packet loss.
