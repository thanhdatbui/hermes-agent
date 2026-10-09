# Case 177: Auto-Advance Regex Delimiter Drift & False Post-Verification Failure

## 1. Context & Architecture
In the Taadaa phone farm TikTok upload pipeline:
- **Child process (`Tiktok-video/scripts/tiktok_workflow/state_machine.py`)**:
  When checking whether video `N` was already posted (via sha256 ledger or workbook cursor), it automatically skips to the next video (`auto-advance`) and outputs to stdout:
  ```text
  [AUTO-ADVANCE] Skipped 1 verified video(s); new video_number=2 (was 1)
  ```
  *(Note the whitespace in `new video_number=...`)*.

- **Parent caller (`tiktok-luot nuoi acc/python_runner/flows/multi_machine_feed_session.py`)**:
  `_run_upload_hook()` invokes `run_post.py` with an initial `--video-number <next_video>`.
  When the child finishes with `returncode == 0`, the parent inspects `report.json` and `stdout`.
  If `report.json` records a higher `video_number` than the caller's initial `next_video`, the parent requires a strict regex match against `stdout` to verify the auto-advance was legitimate.

## 2. The Pitfall: Strict Format Drift
If the parent caller's regex expects an underscore:
```python
# BUGGY REGEX:
aa_match = re.search(
    r"\[AUTO-ADVANCE\]\s+Skipped\s+\d+\s+verified\s+video\(s\);\s+new_video_number=(\d+)\s+\(was\s+(\d+)\)",
    stdout,
)
```
While the child logs with a space:
```python
logger.info(f"[AUTO-ADVANCE] Skipped {advanced} verified video(s); new video_number={new_video_number} (was {self.context.video_number})")
```
The regex fails to match. As a result:
- The upload actually **succeeded 100%** on TikTok and on disk (`status: SUCCESS, post_verified: True, video_number: 2`).
- The parent falsely marks the execution as `status: failed`, `reason: post_verification_failed`.
- The shift upload ledger does NOT record the success, causing false alarms in shift watchdogs.

## 3. Canonical Fix Pattern
Always make delimiters in cross-repo status markers resilient:
```python
# ROBUST REGEX:
aa_match = re.search(
    r"\[AUTO-ADVANCE\]\s+Skipped\s+\d+\s+verified\s+video\(s\);\s+new[ _]?video_number=(\d+)\s+\(was\s+(\d+)\)",
    stdout,
)
```
Match both `new video_number=` and `new_video_number=` with optional space or underscore (`new[ _]?video_number=`).
Ensure unit tests in `test_upload_hook.py` cover both representations so that cross-repo log formatting drifts do not trigger false verification failures.
