# UI Provisioning Policy: REQUIRE_PROVISIONED Contract & Shell Suppression

### 1. Architectural Invariant & Motivation
In `automation-core`, falling back to legacy shell `uiautomator dump` during device automation causes severe performance degradation (5-15s per dump), UI freezes, and masks missing or broken `atx-agent` / uiautomator daemons.
To enforce reliable and fast UI capture across the farm:
- The default provisioning policy is hard-pinned to `ProvisioningPolicy.REQUIRE_PROVISIONED`.
- Any fallback attempt to execute shell UI dump under `REQUIRE_PROVISIONED` must be strictly suppressed with telemetry `SHELL_DISABLED_BY_POLICY`.

### 2. Implementation Invariants in `automation_core/ui.py`
1. **Default Policy in `_dump_current_ui_unlocked`**:
   Parameter signature defaults to:
   ```python
   provisioning_policy: ProvisioningPolicy | str = ProvisioningPolicy.REQUIRE_PROVISIONED,
   ```
2. **Default Policy in `dump_current_ui` compatibility wrapper**:
   Ensure `kwargs` default before lock acquisition:
   ```python
   kwargs.setdefault("provisioning_policy", ProvisioningPolicy.REQUIRE_PROVISIONED)
   ```
3. **Shell Suppression Gate in `try_shell`**:
   Inside `_dump_current_ui_unlocked`:
   ```python
   def try_shell(attempt_number: int, mode: str, *, recovery: str = "",
                 meaningful_recovery: bool = False) -> str | None:
       if policy == ProvisioningPolicy.REQUIRE_PROVISIONED:
           entry = {
               "backend": "shell",
               "attempt": attempt_number,
               "mode": mode,
               "recovery": recovery,
               "failure_signature": "SHELL_DISABLED_BY_POLICY",
               "suppressed": True,
           }
           attempts.append(entry)
           journal.add("BACKEND_SUPPRESSED", **entry)
           return None
       # Proceed to circuit breaker permit check only if not suppressed
   ```

### 3. Verification & Test Targets
- Primary test suite for capture replay, backend selection, and suppression telemetry:
  ```bash
  cd /d/Taadaa/automation-core
  PYTHONPATH=src python -m pytest tests/test_ui_capture_replay.py -v
  ```
- Check that tests asserting shell fallback suppression under `REQUIRE_PROVISIONED` expect:
  - `entry["failure_signature"] == "SHELL_DISABLED_BY_POLICY"`
  - `entry["suppressed"] is True`
  - Journal records event `BACKEND_SUPPRESSED`
