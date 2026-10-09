# UI session-expiry safe-exit reference

## Reproduction pattern

Use a deterministic UI hierarchy fixture containing an expired-session marker, for example:

```xml
<hierarchy>
  <node text="phiên của bạn đã kết thúc" />
</hierarchy>
```

Patch the UI dump seam to return this fixture, patch the credential loader to return a sentinel password, and patch the ADB/process seam with a call recorder. Invoke the real flow function.

## Required assertions

- The flow returns its normal failure sentinel (`None` or a blocked result).
- The credential loader is not called.
- No process/UI call contains the equivalent of `input text <password>`.
- The flow does not continue into account-picker, security-code, or downstream extraction steps.
- A bounded warning or telemetry reason identifies safe exit due to expired session.

## Implementation rule

Detect expiry before credential lookup. Do not treat a missing password as the safety condition: the branch must remain safe even when a valid password is available. This prevents regressions where a later credential source silently re-enables blind typing.

## Scope boundary

This is offline regression evidence only. Do not run live ADB, device re-authentication, password injection, or account recovery as part of the focused test. A separate explicitly authorized re-authentication workflow must own any interactive credential entry.
