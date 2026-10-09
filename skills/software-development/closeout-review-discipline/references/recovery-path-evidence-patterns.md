# Recovery-path evidence patterns for Closeout Reviewers

Lessons from production closeout loops where a reviewer rejected code because resilience/retry logic lacked direct test evidence and structured observability:

## 1. The "Resilience without Evidence" Trap
Adding a retry loop, fallback normalization, or `except Exception` increases code complexity in the eyes of Sol/Terra reviewers. Even if the existing test suite passes 100%, the reviewer will penalize the diff if the newly added branches are unexercised:
- **Symptom:** "Cơ chế retry và fallback giúp tăng khả năng chịu lỗi, nhưng chưa có bằng chứng test trực tiếp cho nhánh retry hoặc khi thất bại."
- **Remediation:** Always pair new retry/fallback code with two minimal test cases:
  1. *Transient failure recovers:* Mock external call to fail on attempt 1 with a typed error, then succeed on attempt 2. Assert retry count incremented and final output succeeded.
  2. *Permanent failure fails gracefully:* Mock external call to fail on all N attempts. Assert attempt count reached max, failure sentinel (e.g. `None` / `""`) is returned, and caller/pipeline does not crash.

## 2. Downstream Degradation Contract
When an upstream component fails and returns a sentinel or empty artifact (e.g. `segment.audio_path = None`):
- Reviewer checks whether the downstream consumer (renderer, merger, exporter) will crash with a `TypeError` or `FileNotFoundError`.
- Provide an explicit integration test: Feed a mixture of valid and empty/None segments into the renderer/pipeline.
- Prove that downstream gracefully skips or falls back (e.g. keeping background audio without crashing) and exports a valid output file.

## 3. Real Telemetry vs. Synthetic Logging
- A generic `logger.warning("failed: %s", e)` is often marked as "che giấu nguyên nhân lỗi vận hành".
- Include:
  - Attempt index (`attempt N of MAX`).
  - Typed error classification (`type(e).__name__`).
  - Production telemetry dataclass or state object (`total`, `success`, `failure`, `retry_count`, `last_errors`).
  - Assert the actual production telemetry object in tests—never assert fake JSON written only inside the test body.
