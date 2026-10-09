# Batch Error Aggregator & Dual-Threshold Systemic Error Detection

Shared primitive module: `src/automation_core/batch_aggregator.py`
Unit tests: `tests/test_batch_aggregator.py`

## Purpose

When running batch automation across multi-device fleets (e.g. 40+ Android devices in Taadaa farm), individual transient errors (flaky Wi-Fi, random ADB timeout) should not trigger spam alerts. Only **systemic errors** affecting multiple devices with identical root causes must trigger alarms and lock the batch.

## Error Signature Normalization Precedence

The function `normalize_error_signature(error_type, step_id, message, target_element)` converts variable error text into a deterministic clustering key. Regex substitution ordering is critical:

1. **Hex addresses**: `\b0x[0-9a-fA-F]+\b` -> `<hex>` (before PIDs).
2. **Timestamps**: Full ISO (`\b\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2}...\b`) before bare time (`\d{1,2}:\d{2}:\d{2}`), date, and unix epoch (`1[5-9]\d{8,11}`).
3. **PIDs & Threads**: `(?i)\b(?:pid|process|thread)\s*[:=]?\s*\d+\b` -> `<pid>`.
4. **Device Prefixes**: `(?i)\b(?:máy|may|machine|device)\s*#?\d+\b` -> `<device>` (runs *before* bare serial matching so "May 8" or "machine 8" are caught whole).
5. **Serials**:
   - Taadaa farm serials (`m\d{1,4}`, `DEV-[A-Za-z0-9_-]+`, `emulator-\d+`, `IP:port`).
   - Hardware serials: Mixed alphanumeric (`(?=[A-Za-z0-9]*[0-9])(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{8,32}`) or long hex (`[0-9a-fA-F]{12,32}`). Must require both letter+digit to avoid masking uppercase constants like `TIMEOUT_ERROR` or `FAILED_LOCKED`.
6. **Coordinates & Bounds**: Bounds (`\[\d+,\s*\d+\]\[\d+,\s*\d+\]` -> `<bounds>`) before point coordinates (`\(\d+,\s*\d+\)` or `\[\d+,\s*\d+\]`).

## Dual-Threshold Classification (Ngưỡng kép)

In `evaluate_batch(results: list[MachineResult], min_rate: float = 0.10, min_count: int = 3)`:

- For each error signature group:
  - `count = len(group_machines)`
  - `rate = count / total_machines`
- Classification:
  - `systemic` if `(rate >= min_rate) and (count >= min_count)`
  - `sporadic` otherwise (Silent Skip — no alert sent).

### Failure Modes Guarded Against

1. **Small-Batch Trap**: 1 failure out of 5 machines = 20% (>= 10% rate), but count = 1 (< 3 count threshold). Classified as sporadic; does not halt or spam alert.
2. **High-Fleet Noise**: 3 failures on 50 machines = 6% (< 10% rate, even though count = 3 >= 3). Classified as sporadic.
3. **True Systemic Breakage**: 5 failures out of 40 machines = 12.5% (>= 10% rate AND count 5 >= 3). Triggers `should_alert=True`.

## Representative Media Selection

For each systemic signature:
- Select up to 1-2 representative screenshots (`snapshot_png`, fallback `snapshot_xml`).
- Include them in `representative_media` for direct Telegram photo attachments without flooding chat with 40 identical images.

## Canary Policy & Recovery in Alerts

The generated alert message enforces Canary Policy:
1. Lock batch: Halt fleet operations.
2. Propose single canary test on representative machine: `python D:/Taadaa/tools/inspect_machine.py <first_machine>`.
3. Provide representative media paths for visual inspection.
4. Only resume fleet once canary passes.
