# Telegram arrow-sanitization and provider-dispatch diagnostic

## Purpose

Use this reference when a Telegram message still displays a LaTeX arrow or when a provider error appears alongside a formatting complaint.

## Diagnostic split

- `ALL_TARGETS_SKIPPED`, quota exhaustion, and provider-unavailable errors occur before a model response is generated. They do not reach the outbound Telegram formatter.
- A formatting bug can only be proven on a successfully generated and delivered message. A provider failure cannot prove that the sanitizer failed.

## Required implementation contract

1. Normalize at the final Telegram adapter boundary, after model output assembly and immediately before the send API.
2. Cover both escaped and math-delimited forms, including:
   - `$\\rightarrow$` and `\\rightarrow` -> `→` or `->`
   - `$\\Rightarrow$` and `\\Rightarrow` -> `⇒` or `->`
   - Preserve normal prose and avoid double-conversion.
3. Keep the sanitizer independent of the selected model/provider.
4. Add focused tests for all spellings, ordinary text, idempotence, and a final-payload assertion that banned LaTeX arrow tokens are absent.
5. Verify one real successful Telegram delivery before claiming end-to-end fixed.
6. If dispatch fails, report: `provider dispatch failed before formatter; outbound rendering unverified`.

## Reporting template

- Provider dispatch: PASS / FAILED / UNAVAILABLE
- Formatter test: PASS / FAIL / NOT RUN
- End-to-end Telegram delivery: VERIFIED / UNVERIFIED
- Actual delivered text: quote only after inspecting the successful message
