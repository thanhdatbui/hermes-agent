# Native Media, Visual Readback & Mechanical Gate (06/10/2026)

## 1. Operator Corrections and Incidents

- **Correction 1 (Folder link instead of image):**
  - Prompt: *"? hình đâu gửi link folder ăn l à"*
  - Prompt: *"lí do tại sao k gửi ảnh mà đi gửi link, rule k ép chặt mày à?"*
  - Root cause: The coordinator treated runner directory paths and file paths inside prose or Markdown code blocks as valid completion reports. Telegram renders these as plain text, not native media.
  - Requirement: Any visual artifact must be emitted as `MEDIA:<absolute_path>` on its own line so Telegram delivers the real photo. Never substitute a path or code fence.

- **Correction 2 (Reading before sending):**
  - Prompt: *"làm đi, và yêu cầu LLM phải đọc ảnh trc khi gửi tao, tránh việc gửi ảnh cho có lệ"*
  - Root cause: An assistant could locate an artifact path and attach it without checking whether it showed the right account, the right avatar, an error popup, or a black/dozing screen.
  - Requirement: Visual readback invariant. The assistant must call `browser_vision` (or OCR) to inspect the image, confirm the exact target screen, confirm the target account and change, and include a concise visual readback sentence in the final message.

## 2. Mechanical Gate Architecture

Prompt-level rules alone can be bypassed by attention drift, long contexts, or paraphrased wording. A production delivery system requires a mechanical gate in the outbound platform adapter:

1. **Trigger criteria:**
   - Detect explicit completion markers (`DONE`, `VERIFIED_SUCCESS`, `FIXED`, `HOÀN TẤT`, `ĐÃ XONG`, `THÀNH CÔNG`, `COMPLETED`, `FINISHED`, etc.).
   - Detect natural-language Vietnamese completion patterns (`_COMPLETION_REGEX` matching `đã ... xong/rồi/thành công/hoàn tất`, `thay xong avatar/ảnh`, `cập nhật xong`).
   - Allow ordinary conversational turns to pass through without forcing an image.

2. **Validation rules:**
   - Must contain at least one `MEDIA:<path>` token.
   - Reject tokens contained within Markdown code fences (```` ``` ````).
   - Require absolute, canonical file paths.
   - Restrict files to allowed roots (`run_dir`, `evidence_roots`) when roots are configured.
   - Reject missing files, unreadable files, or files below `min_bytes`.
   - Reject stale evidence (`mtime < run_start - leeway` or exceeding `max_age_seconds`).
   - Image content validation:
     - Mean grayscale <= 2.0 or >= 253.0: reject as black or blank/white screenshot.
     - Grayscale standard deviation < 3.0: reject as solid-color screenshot lacking visual detail.
     - Optional expected dimension check.

3. **Fail-closed delivery default:**
   - When a delivery caller omits explicit `evidence_context`, the delivery router must NOT bypass validation.
   - Fall back to a default `MediaEvidenceContext()` so un-contextualized completion claims are still evaluated for bare paths, fences, existence, and basic image quality.

4. **Structured telemetry:**
   - A plain `logger.warning` is insufficient for reviewer gates and production auditing.
   - Implement an append-only in-memory telemetry buffer (e.g. `record_evidence_gate_event`, `get_evidence_gate_telemetry`, `clear_evidence_gate_telemetry`).
   - Record: `event="validation"`, `platform`, `chat_id`, `valid`, `reason`, `paths`, and `timestamp`.
   - Provide unit tests asserting telemetry emission on both pass and reject.

## 3. Closeout Remediation Loop Lessons

During the closeout of the media evidence gate in `hermes-agent`, the Sol Auditor reviewer scored the initial implementation:

- **Round 1 (Score 81 / REJECTED):**
  - Gate validated only when `evidence_context is not None`. An un-contextualized completion message could still slip through.
  - Telemetry was absent.
  - Action: Enforce `context_to_use = evidence_context or MediaEvidenceContext()`, add warning log.

- **Round 2 (Score 83 / REJECTED):**
  - Reviewer noted that `logger.warning` is unstructured and cannot be programmatically observed or tested.
  - Missing tests for the default-context path.
  - Action: Build structured telemetry store (`_GATE_TELEMETRY`), export inspection helpers, and add regression tests for both default-context rejection and telemetry event recording.

- **Round 3 (Score 88 / APPROVED):**
  - Full suite: 9/9 focused tests passed.
  - Observability score increased from 8/15 to 12/15; Test Evidence reached 23/25.
  - Result: Approved for commit and merge.
