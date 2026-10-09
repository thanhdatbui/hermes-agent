# Batch alert: overall failure rate + per-signature rates

User correction (2026-09-11): full-fleet failure (80/80) was reported as
75% (60/80) because the alert showed only the largest signature's local
rate. Rule: the alert MUST show the overall batch failure rate first.

Format (implemented in `automation-core/batch_aggregator.py`,
`format_alert_message`, commit dbe8737):

```
Quy mo batch: 80 may | Thanh cong: 0 | That bai: 80
Tong ty le that bai toan batch: 100.0% (80/80 may)
Signature: ...
  - Ty le tren toan batch: 75.0% (60/80 may)
  - Ty le trong so may loi: 75.0% (60/80 may loi)
```

Checklist for future batch-alert edits:
1. Overall line = failed_count/total_machines, always present.
2. Each signature shows BOTH batch share AND share-of-failed.
3. Focused test only: `pytest tests/test_batch_aggregator.py`
   (never full `pytest tests/`).
4. Related user rule: device lock TTL max 1h (3600s), auto-reap.
