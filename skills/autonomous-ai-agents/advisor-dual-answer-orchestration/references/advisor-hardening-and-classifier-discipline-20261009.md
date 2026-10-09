# Lessons from Advisor Review & Strict Dual-Answer Enforcement (2026-10-09)

## 1. User Feedback & Tone Discipline
- **User Scolding:** "sao bữa nay t đéo hề thấy mày gọi advisor nữa?"
- **Root Cause:** Coordinator had immediate-response bias and feared upstream timeout on Sol review combo (:20129), leading to solo answering and abandoning the mandatory dual-answer protocol.
- **Enforcement Invariant:** Never answer solo when message exhibits advice intent. Always query Advisor Sol or fast fallback and append the `--- Advisor (<model>) ---` block.

## 2. Intent Classifier Hardening
- **False-Negative Elimination:**
  - Compound intent ("chạy batch rồi cho tao biết nên làm gì", "git log xem có gì lạ không"): Imperative verb prefix must not block advice detection when a clear advice/evaluative clause follows.
  - "vì sao" and "thấy sao" are strong evaluative signals even without a trailing question mark `?`.
- **False-Positive Elimination:**
  - Exclude progress/status inquiries ("sao rồi", "tiến trình ra sao rồi") which are operational status checks, not architectural queries.
  - Exclude adverbial phrases ("sao cho", e.g., "sửa cái này sao cho nhanh").
  - Exclude commands targeting tools named review or plan ("chạy review combo", "tạo plan phase 2").
  - Exclude simple execution permission checks ("Đăng ký bù, được không?").

## 3. Streaming & Timeout Defense
- **Wall-Clock vs Socket Read Timeout:** `urllib.request.urlopen(timeout=...)` only governs per-chunk read timeout. A loop over `resp` can easily exceed the overall budget. A strict wall-clock timer (`time.time() - t_start > deadline`) is mandatory inside the line iterator.
- **Premature EOF vs [DONE] Marker:** A server closing the connection prematurely without `data: [DONE]` must be treated as failure (`return False`), never as success with truncated advice.
- **Pseudo-200 Usage Limits:** Filter `[Error: You've hit your limit]` across all fallback tiers.

## 4. Secret Redaction Standard
Before sending prompts to external or secondary LLM routes:
- Redact `sk-[a-zA-Z0-9_\-]{20,}` -> `[REDACTED_API_KEY]`
- Redact `Bearer [token]` -> `Bearer [REDACTED_TOKEN]`
- Redact URL basic auth `://user:pass@` -> `://[REDACTED_USER_PASS]@`
- Redact query params / fields: `password`, `passwd`, `pass`, `mật khẩu`, `token=`, `api_key=`, `sessionid=` -> `[REDACTED]`
