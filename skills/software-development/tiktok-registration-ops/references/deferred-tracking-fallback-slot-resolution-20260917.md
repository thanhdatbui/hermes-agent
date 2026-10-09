# Dynamic Empty Slot Fallback in deferred_tracking_writer.py (2026-09-17)

## Problem & Context
When running reg batches (or offline/deferred apply flows), account targets carry `tracking_row` and `tik` determined at preflight/detection time.
However, during execution or cross-machine operations:
1. `expected_row` may drift if another process or manual edit touched rows.
2. `expected_row` might already be filled with TikTok ID/Pass (`TRACKING_ROW_HAS_ID_OR_PASS`).
3. `expected_row` might have a different email assigned (`EXPECTED_EMAIL_x_GOT_y`) or mismatched TIK index (`EXPECTED_TIK_x_GOT_y`).

Previously, `_check_expected_row` would immediately block with `BLOCKED_DATA_CONFLICT`, leaving newly registered accounts unwritten to the tracking workbook.

## Solution & Pattern
In `_check_expected_row(ws, result)`:
- Detect if the blocker is due to row conflict or drift:
  - `EXPECTED_EMAIL_{email_l}_GOT_{row_email}`
  - `TRACKING_ROW_HAS_ID_OR_PASS`
  - `EXPECTED_TIK_{expected_tik}_GOT_{row_tik}`
- When such a conflict is detected, trigger fallback resolution via:
  ```python
  slot_row, slot_tik, slot_blocker = resolve_tracking_slot(ws, stt, email_l)
  if slot_row and slot_tik and slot_row != expected_row:
      expected_row = slot_row
      expected_tik = slot_tik
      result["tracking_row"] = slot_row
      result["tik"] = slot_tik
      blocker = ""
  ```
- If a valid empty slot for the machine (`stt`) exists, update the result target to the new slot and clear `blocker`.
- If no slot is available, retain the conflict blocker (`BLOCKED_DATA_CONFLICT`).

## Verification
- Unit test coverage in `tests/test_fallback_slot_resolution.py` and `tests/test_deferred_tracking.py`.
