# Case Study: Hermes Cron Subprocess Timeout Misclassification ("Provider Timeout")

## Context & Incident
A watchdog job `hourly-stale-post-receipts-reconcile` (ID: `8d6b3c18dd64`) configured with `no_agent: true` periodically reconciles stale post receipts (>24h) on the TikTok farm to prevent deadlock traps.
In a prior session, the job was migrated to `no_agent: true` to avoid LLM model-drift spend guards.
One hour later, the job failed on schedule with the following Telegram alert:
```text
⚠️ Cron 'hourly-stale-post-receipts-reconcile' failed: provider timeout. Fallback chain was exhausted or unavailable. Full details saved in cron output.
```
This led operators and agents to suspect that the job had reverted to calling an LLM inference provider or that global model configuration had drifted again.

---

## Root Cause Analysis

### 1. Hermes Scheduler Error Classifier Regex
In `D:/Taadaa/Hermes/cron/scheduler.py`, Hermes classifies cron errors using coarse keyword matching:
```python
if "readtimeout" in lower or "timed out" in lower or "timeout" in lower:
    return (
        f"⚠️ Cron '{job_name}' failed: provider timeout. "
        "Fallback chain was exhausted or unavailable. "
        "Full details saved in cron output."
    )
```
Whenever ANY cron job error contains the token `"timeout"` or `"timed out"`—including Python's `subprocess.TimeoutExpired` inside a standalone `no_agent: true` script—Hermes synthesizes the misleading message:
`provider timeout. Fallback chain was exhausted or unavailable.`

### 2. Under-the-Hood Subprocess Timeout
Inspection of `%LOCALAPPDATA%\hermes\cron\output\8d6b3c18dd64\2026-10-27_18-23-19.md` revealed:
```text
Script exited with code 1
stderr:
Traceback (most recent call last):
  ...
  File "subprocess.py", line 1630, in _communicate
    raise TimeoutExpired(self.args, orig_timeout)
subprocess.TimeoutExpired: Command '['...python.exe', 'D:\\Taadaa\\tools\\cron_reconcile_stale_receipts.py']' timed out after 120 seconds
```
The script ran 100% locally with 0 LLM tokens, but took $> 120$s to complete.

### 3. File I/O Bottleneck on 9,500+ Receipts
In `reconcile_stale_post_receipts.py`, `find_stale_receipts` naively opened and JSON-parsed every single file:
```python
for f in receipt_dir.glob("*.json"):
    data = json.loads(f.read_text(encoding="utf-8"))
    if data.get("status") == "completed":
        continue
```
In `D:\CodexRuntime\tiktok-video\idempotency\post-attempts`, over **9,522 out of 9,524 files** were already `"completed"`. Under heavy disk I/O (e.g. concurrent farm upload batches + OneDrive sync), reading and parsing 9,524 files on Windows NTFS easily exceeded the 120-second timeout budget.

---

## Engineering Remedy

### Fast Binary Prefix Filter (100x Speedup)
Instead of full `Path.glob()` and `json.loads()`, apply a low-level binary pre-filter:
```python
candidates = []
with os.scandir(receipt_dir) as it:
    for entry in it:
        if not entry.name.endswith(".json") or not entry.is_file():
            continue
        try:
            with open(entry.path, "rb") as fp:
                head = fp.read(512)
                # Skip already completed receipts without parsing JSON
                if b'"status": "completed"' in head or b'"status":"completed"' in head:
                    continue
            candidates.append(entry.path)
        except OSError:
            continue
```
### Benchmark Results
- **Naive Full Scan:** 37s to >120s (spiking to timeout under farm I/O load).
- **Binary Prefix Fast Filter:** **1.16s** across 9,524 files (drops 9,520 completed files instantly, only 4-5 pending files parsed with `json.loads`).

---

## Triage Rule for Operators & Agents
1. When a `no_agent: True` job reports `failed: provider timeout. Fallback chain was exhausted`, **do not check API keys, models, or gateway**.
2. Immediately read the corresponding `%LOCALAPPDATA%\hermes\cron\output\<job_id>\*.md` file to identify the exact local script error or `subprocess.TimeoutExpired`.
3. Eliminate naive directory scans over growing farm receipt/log directories using `os.scandir` + binary prefix filtering.
