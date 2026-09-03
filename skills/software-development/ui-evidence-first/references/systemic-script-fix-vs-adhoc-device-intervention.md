# Systemic Script Fix vs. Ad-Hoc Device Intervention

## User Correction & Operational Directive

### The Failure Pattern (Ad-Hoc Triage Trap)
When the user reports an incident on a specific device (e.g. "fix máy 19" with a Telegram alert screenshot), agents have a failure tendency to treat the request as device maintenance:
- Connecting to the live device via ADB.
- Sending keyevents (`HOME`, `BACK`) or tapping coordinates to unstick the UI.
- Reporting the device is now clear, without modifying the underlying automation codebase.

**Why this fails:** Ad-hoc manual intervention only temporarily clears the screen on 1 machine while leaving the systemic bug live in production across the remaining 159 farm devices.

---

### The Correct Standard Workflow
1. **Device as Read-Only Evidence:** Use the incident device, its `ui.xml`, `screen.png`, and `log.jsonl` strictly as evidence to determine the technical root cause. Preserve the blocked lock state (TTL 2h) until the fix is ready.
2. **"Fix" Mandate = Codebase Patch:** The deliverable for any incident fix is an authoritative patch in the corresponding repository (`python_runner/flows/`, `core/`, etc.) resolving the issue farm-wide.
3. **Evidence-Gated Verification:** Add unit/regression tests, verify against incident fixtures, and document the Case Fix & Anti-Pattern in `docs/farm-automation-cases.md` before closeout.
4. **Zero Ad-Hoc Bypasses:** Never claim an incident is fixed by manually navigating the device out of the blocked screen.
