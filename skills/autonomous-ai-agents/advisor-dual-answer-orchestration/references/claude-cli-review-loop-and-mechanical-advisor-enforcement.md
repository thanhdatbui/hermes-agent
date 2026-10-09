# Claude CLI Review Loop & Mechanical Advisor Enforcement (Case Study 2026-10-10)

## 1. Context & Operator Frustration
- Operator severely reprimanded Coordinator: *"sao bữa nay t đéo hề thấy mày gọi advisor nữa?"* and *"gọi advisor plan trc"*.
- Root cause of Coordinator silence on Advisor:
  1. **Immediate-Response Bias:** Coordinator models naturally rush to answer analytical/architectural questions directly rather than dispatching a dual consultation.
  2. **Fear of Timeout / Waterfall Hangs:** OmniRoute `:20129` `review` (Sol Web High) frequently experiences reasoning latency (25-45s) or rate-limit waterfall penalties across web accounts. Coordinator avoided calling it to prevent session hangs.
  3. **Lack of Mechanical Gate:** Kicking off Advisor was left to prompt discipline rather than a deterministic script with fast fallback and hard exit deadlines.

## 2. 3-Tier Fast Fallback Architecture
To guarantee Advisor availability without hanging the user session (>35s), `advisor_consult.py` was architected with a bounded 3-tier cascade:
- **Tier 1 (OmniRoute :20129 `review` - Sol Primary):** Fail-fast 5s budget. If TTFT exceeds 5s (web pool saturation or reasoning delay), abort immediately to tier 2.
- **Tier 2 (OmniRoute :20129 `antigravity/gemini-3.7-flash-high` - Sol Fast Fallback):** 18s budget. Responds reliably in ~10s with high-quality architectural reasoning.
- **Tier 3 (9Router :20128 `ag/gemini-2.5-flash` - Port 20128 Backup):** 7s budget on independent proxy port using `$NINEROUTER_API_KEY`.
- **Fail-Safe Mode:** If all tiers fail or timeout, cleanly outputs `Advisor: unavailable (upstream timeout / pool limits; primary answer shown)`. Never hallucinate or synthesize fake advice.

## 3. Classifier Precision (Eliminating False Positives & Negatives)
Reviewer Claude CLI subjected the classifier to 16 edge cases across 4 review rounds:
- **Compound Intent (Imperative + Advice):**
  - Messages like *"chạy batch rồi cho tao biết nên làm gì"* or *"git log xem có gì lạ không"* start with an imperative verb but contain explicit advice questions. The classifier must detect these compound patterns and route to Advisor.
- **False-Positive Traps:**
  - Substring collision on `liệu`: Nouns like `dữ liệu`, `tài liệu`, `vật liệu` collided with `\bliệu\b` (e.g., *"sửa dữ liệu avatar máy 62"* was falsely flagged as advice).
  - Imperative combos: Commands like *"chạy review combo"*, *"chạy lại review combo"*, *"tạo plan cho phase 2"*, *"lên plan cho phase 2"* contain keywords `review` or `plan` but are imperative commands.
  - Status/Progress questions: *"kiểm tra xem avatar máy 62 sao rồi"* or adverbs like *"sửa cái này sao cho nhanh"* contain `sao` but are not requests for advice.
- **Rule Formulation:** Strip out known noun phrases and imperative action targets before matching `ADVICE_PATTERNS`.

## 4. Leak-Proof Redaction Engine
Before queries or contextual snippets leave the machine:
- Strip OpenAI/Hermes keys: `sk-[a-zA-Z0-9_\-]{20,}`.
- Strip Bearer tokens: `Bearer [token]`.
- Strip URL Basic Auth: `://user:pass@`.
- Strip JSON-quoted key-values: `(?i)(["']?(?:password|passwd|pass|api_key|token|access_token|session_id)["']?\s*:\s*)["'][^"']+["']`.
- Strip unquoted Vietnamese phrases: `\bmật khẩu\s+là\s+[^\s,;]+`.

## 5. Reviewer Claude CLI 4-Round Remediation Progression
Operator ordered: *"Thi công đi xong đưa claude cli chấm điểm đến khi đạt"*.
The implementation was audited across 4 independent rounds:
- **Round 1 (62/100 - REJECTED):** Failed on unanchored SSOT in `path_resolver`, mock-only tests, uncalibrated timeouts, missing JSON redaction.
- **Round 2 (72/100 - REJECTED):** Redaction missed `access_token` and unquoted Vietnamese phrases; classifier had false-positives on `dữ liệu`; stream reader accepted truncated text on premature EOF.
- **Round 3 (86/100 - APPROVED):** Exceeded threshold (86 >= 85), but noted minor hygiene gaps (raw strings for docstrings with backslashes, `vg_tmp` cleanup in `finally`, import-time heavy scanning in `ALL_TARGETS`).
- **Round 4 (91/100 - APPROVED):** All 5 technical items resolved cleanly. 14/14 offline unit tests passed, 5/5 pytest passed with 0 deprecation/syntax warnings.
