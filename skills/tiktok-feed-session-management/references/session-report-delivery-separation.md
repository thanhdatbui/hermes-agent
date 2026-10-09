# Session report delivery separation

## Observed failure pattern

The watchdog can correctly detect and claim two sessions, for example `ca2_phien1` and `ca2_phien2`, yet deliver one Telegram message containing both reports. The telltale implementation is:

```python
messages.append(msg)
print("\n\n".join(messages))
```

A cron job with `no_agent: true` commonly treats the complete stdout as one delivery payload. Newlines are formatting, not message boundaries.

## Verification recipe

1. Read the cron job definition: confirm script, schedule, `no_agent`, and destination.
2. Inspect the exact timestamped cron output file, not only the latest chat message.
3. Confirm separate session headers occur in one stdout payload.
4. Check `feed_session_reported.json` for independent claim keys. Independent keys prove detection/claiming, not independent Telegram delivery.
5. Inspect the scheduler's actual multi-message/delivery API before proposing a patch.

## Safe design rule

One session should map to one delivery unit. If the scheduler exposes a supported send-message function, call it once per session after atomic state claim. If it only accepts one stdout payload, do not guess a delimiter: mark the task BLOCKED with the exact evidence and require a delivery-layer change. Do not alter session windows, claim keys, or deduplication merely to make formatting appear separate.

## Evidence from the reproduced case

Output file `1d62cb3562e0_20260926_152148.txt` contained `Ca 2 - Phiên 1/2` at line 5 and `Ca 2 - Phiên 2/2` at line 51. The watchdog implementation joined `messages` at its final print, explaining the single Telegram message without implying duplicate execution.
