# Live Mobile Canary Evidence Checklist

Use this checklist whenever a farm task requires canary verification on an Android device (especially avatar upload, registration, login, or recovery).

## Evidence Classes (Do Not Conflate)

| Class | What it proves | What it DOES NOT prove | Example Artifacts |
|---|---|---|---|
| **1. Preflight** | Target device is connected, awake, and available | The workflow has not run | `inspect_machine.py <N>`, `dumpsys window windows`, lock JSON |
| **2. Action Execution** | Runner executed on the bound target | Output or visual success | Terminal stdout/stderr, runner exit code, process PID |
| **3. Target-Screen Evidence** | Workflow reached intended terminal state | Does not prove persistence without readback | Screenshot of new avatar on profile, save success dialog |
| **4. State/Persistence Readback** | Data changed in persistent store | Visual UI correctness | Workbook/Excel row `Avatar = OK`, DB state, HTTP 200 upload |
| **5. Teardown** | Device safely returned to idle state | ANY prior success | `LauncherActivity` screenshot, force-stop log |

## Hard Invariants

1. **Screen State Invariant:** Never capture canary evidence while the device is in `Sleep/Dozing` or screen OFF. Always wake (`input keyevent 224` + `wm dismiss-keyguard`) and confirm awake state before capturing.
2. **Surface Invariant:** A screenshot of `LauncherActivity` or `SplashActivity` is NEVER proof of avatar upload. It is only teardown or startup evidence.
3. **Capture-Before-Cleanup:** Screenshots of the target outcome MUST be captured BEFORE issuing `am force-stop` or `input keyevent KEYCODE_HOME`.
4. **No Synthetic Completion:** If the runner did not execute (e.g. account already has avatar, machine locked, script blocked by gate):
   - Report `BLOCKED` / `FINAL_BLOCKED` honestly.
   - Attach the live preflight screenshot with the true explanation.
   - NEVER rename an idle screenshot or teardown screenshot to `..._verified.png` or `..._avatar.png` to satisfy a gate.
5. **Gate Verification Independence:** A passing `done_gate` exit code only checks that an evidence file exists and is recent; it does not inspect the visual contents of the image. The human and AI coordinator must inspect the image visually via `MEDIA:` to confirm true target surface.
