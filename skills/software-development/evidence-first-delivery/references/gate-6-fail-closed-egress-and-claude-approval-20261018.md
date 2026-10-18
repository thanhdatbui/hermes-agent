# Gate 6 Mechanical Guard & Fail-Closed Egress Evidence Enforcement

## 1. Context & Incident (18/10/2026)
During the normalization of account `@huynhdiem0806` on Machine 23 (`ce0117113acfd47e0c`), Coordinator completed pinning the top video and updating the bio, but ended its conversational turn with a prose status summary / narrative explanation ("Báo cáo tổng kết hiện trường sau khi toàn bộ chuỗi subagent hoàn tất...") without attaching a `MEDIA:<path>` token.
Operator flagged the violation:
> *"Lí do sai phạm? Gọi claude cli vào điều tra, đkm tao rào bn gate guủad mày vẫn óc lồn"*
> *"R thi công xong gọi claude review"*

## 2. Root Cause Analysis by Claude Sonnet 5.5 (`--role planner`)
An independent architectural review by Claude Sonnet 5.5 identified three structural loopholes in `guard_media_vision_gate.py`:
1. **Denylist / Verb-Matching Fail-Open Trap:** The guard previously checked only explicit completion verbs (`da doi`, `thanh cong`, `hoan tat`, `renamed`). When Coordinator used narrative/progress framing (`bao cao`, `tien do`, `hien truong`, `kich ban`, `da tat popup`), the message bypassed the regex and passed open without any media.
2. **Missing Physical File & SHA-256 Tamper Checks:** Merely having `MEDIA:\S+` was previously treated as having media evidence, without verifying if the file actually existed on disk or if its SHA-256 had been tampered with after receipt creation.
3. **Egress Hook Enforcement Gap:** The gate logic was only invoked as a helper rather than being wired fail-closed at egress.

## 3. Mechanical Implementation
The gate in `D:/Taadaa/tools/guard_media_vision_gate.py` was upgraded:
- Expanded `ACTION_COMPLETION_PATTERNS` & `UI_COMPLETION_ACTIONS` to 23 clusters: includes `bao cao`, `tien do`, `hien truong`, `ket qua`, `kich ban`, `da thuc thi`, `da thuc hien`, `da xong`, `da ghim`, `da tat`, `da dong`, `tong ket`, `thay doi`, `cap nhat`.
- Expanded `SUBJECT_PATTERNS` & `UI_COMPLETION_SUBJECTS` to 21 entities: includes `ghim`, `pin`, `video`, `kenh`, `tai khoan`, `nick`, `may`, `thiet bi`, `popup`, `story`, `anh dai dien`.
- Added `_media_file_verdict()`: checks physical file existence on disk and recalculates SHA-256 against the HMAC-signed receipt. Missing, unreadable, or tampered files return `INVALID_MEDIA_FILE`.
- Test suite in `tests/test_guard_media_vision_gate.py` expanded from 33 to 70 tests, covering all action/subject tokens, missing files, tampered files, and CLI exit codes.

## 4. Independent Review by Claude Sonnet 5.5 (`--role reviewer`)
Claude Sonnet 5.5 reviewed the diff and test execution:
- **Test execution:** `pytest tests/test_guard_media_vision_gate.py` passed 70/70 in 0.42s (100% GREEN).
- **Adversarial probes:** Missing files and tampered files successfully blocked with `INVALID_MEDIA_FILE`; narrative claims blocked with `MISSING_MEDIA_EVIDENCE`.
- **Verdict:** `VERDICT: APPROVED`.

## 5. Invariants for Future Sessions
1. **Zero-Prose Completion Rule:** Every turn asserting device/UI actions must include a valid `MEDIA:<path>` token. Narrative framing is caught by the extended 23-action pattern.
2. **Physical Evidence Integrity:** The attached media file must exist on disk and match its recorded HMAC receipt SHA-256 hash.
