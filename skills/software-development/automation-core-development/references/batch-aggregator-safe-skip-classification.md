# Safe-Skip Classification Pattern for Batch Aggregator

## Context
When running large batches across many devices (e.g. 80 machines), machines can encounter benign non-execution conditions such as:
- Account row in workbook is empty (`is empty (no username)`)
- Workbook row invalid (`does not have valid row`)
- Device intentionally skipped or deferred locked (`skipped-device-locked`, `deferred_locked`, `skipped-empty`)

## Problem: False Systemic Alerts
If treated as generic failures (`failed`), these safe-skips inflate `failed_count` and trigger high-rate systemic error alarms (`BatchAggregationReport.should_alert = True`), disrupting operators with false alerts.

## Design & Implementation Pattern
1. **Model attributes**:
   - `MachineResult.skipped: bool = False`
   - `BatchAggregationReport.skipped_count: int = 0`
   - Maintain full backwards compatibility in serialization (`to_dict()`).

2. **Classification logic in `evaluate_batch`**:
   - Separate results into `succeeded`, `skipped`, and `failed`.
   - A result is categorized as `skipped` if:
     - `r.skipped is True`, OR
     - `not r.succeeded` and error keywords match safe-skip phrases:
       `("is empty (no username)", "does not have valid row", "account workbook does not have valid row", "skipped-empty", "skipped-device-locked", "deferred_locked")`
       or `"skip"` in `error_type.lower()`, or (`"skipping"` in `error_message.lower()` and `"empty"` in `error_message.lower()`).
   - Only non-skipped failures go to `failed` and form error signatures (`groups`).

3. **Alert display formatting**:
   - Display `Bỏ qua: {skipped_count}` in scale line when `skipped_count > 0`:
     `• Quy mô batch: <b>{total_machines} máy</b> | Thành công: {succeeded_count} | Bỏ qua: {skipped_count} | Thất bại: {failed_count}`
