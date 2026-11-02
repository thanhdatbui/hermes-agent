---
name: closeout-gate-dispatch-worker-patterns
description: Use when closeout_gate rejects dispatch_worker changes.
version: 1.0.0
---
# Closeout Gate Patterns for `dispatch_worker.py`

## Trigger
Use when running `closeout_gate.py` on `D:/Taadaa/tools/dispatch_worker.py` or when a remediation loop struggles to reach 85/100.

---

## 1. Sol Auditor Scoring Model (100 pts)

| Category | Weight | What it checks |
|---|---|---|
| Logic Correctness | 35 | Tier ordering, fallback ladders, snapshot baseline ownership |
| Test Evidence | 25 | Actual pytest log, not mocks alone |
| Telemetry & Obs | 15 | Per-tier, per-attempt audit() calls; JSONL coverage |
| Farm Safety | 15 | Worst-case chain latency, no unbounded timeout |
| Code Architecture | 10 | No duplicate code paths; helpers extracted |

**Threshold:** >= 85 to pass; 80–84 is Grace Band (passes if tests verified).

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
