# Graph OTP clock-skew verification

## Fix pattern

For Graph OTP freshness checks anchored to local UTC time, allow a narrow one-minute backward tolerance for provider/device clock skew:

```python
from datetime import datetime, timezone, timedelta
otp_started_at = datetime.now(timezone.utc) - timedelta(minutes=1)
```

Keep sender, subject, OTP-format, and seen-message-id checks unchanged. Import `timedelta` explicitly; focused parser tests may not execute the live Hotmail branch, so a missing import can surface only in the canary.

## Verification sequence

1. Run the focused Hotmail/Graph OTP pytest module.
2. Run the single requested canary profile once.
3. If the canary exposes an import/runtime error, repair it, rerun pytest, then rerun the same bounded canary.
4. Report pytest and canary evidence separately. Any edit after a passing run makes the earlier evidence stale.

Observed successful evidence in the source session: focused module `2 passed`; the single Hotmail canary fetched Graph OTP and reached final `SUCCESS` after the missing `timedelta` import was repaired.
