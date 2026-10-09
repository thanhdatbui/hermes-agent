# Account Switcher Verification & Device Timeout Patterns

## 1. Profile Navigation Pre-condition
The TikTok account switcher dropdown sheet only exists and can only be opened when the app is on the **Profile** tab.
- **Rule**: Always call `reg.go_to_profile(serial)` and sleep 2 seconds to settle BEFORE calling `reg.open_account_dropdown(serial)`.
- If an automated flow re-opens TikTok or returns from Settings/Logout, the active screen might default to Feed or an intermediate screen; calling `open_account_dropdown(serial)` without ensuring Profile first will fail or misclick.

## 2. Resilient Verification & Evidence Capture
When capturing screenshot evidence at the end of a logout or reconcile routine:
- Wrap `reg.open_account_dropdown(serial)` in a `try...except` block:
  ```python
  reg.open_app(serial)
  time.sleep(2)
  reg.go_to_profile(serial)
  time.sleep(2)
  try:
      reg.open_account_dropdown(serial)
      time.sleep(2)
  except Exception as exc:
      print(f"[{machine_id}] Warning opening dropdown for verify: {exc}")
  ss_path = f"D:/Taadaa/reports/m{machine_id}_switcher_verified_logout.png"
  subprocess.run(f'"{ADB}" -s {serial} exec-out screencap -p > {ss_path}', shell=True)
  ```
- This guarantees that even if the switcher sheet cannot be opened (e.g. account already logged out and only 1 account remains without dropdown), the verification screencap and subsequent teardown to HOME still complete cleanly.

## 3. Command Timeout Allocation for S7 Farm Devices
- Reconcile, logout, and multi-step UI verification scripts on older S7 farm hardware involve multiple XML dumps (`atx-agent` retries / `uiautomator`) and UI settling times.
- A single end-to-end run often exceeds 180 seconds. When executing canary or single-machine reconciliation tests via CLI or terminal runners, set timeouts to at least 300s to avoid mid-run SIGKILL / timeout.
