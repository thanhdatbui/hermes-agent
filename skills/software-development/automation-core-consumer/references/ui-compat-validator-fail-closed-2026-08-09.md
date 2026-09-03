# UI-compatibility validator: fail-closed NEW records / legacy OLD (user rule 2026-08-09)

Session: `automation-core/tools/check_ui_compatibility.py` + tests updated per user rule
2026-08-09. Result: validator exit 0 with `OK: 9/9 consumers` on STDOUT while the
pre-existing 66 incomplete-record findings became legacy warnings on STDERR.

## The rule (user's words, 2026-08-09)

- Record consumer MỚI (ngày/ID >= 2026-08-09) thiếu concept → FAIL (fail-closed).
- Record CŨ thiếu concept → chỉ legacy warning, không fail (không retroactive,
  vận hành trơn).
- No commit/push; files must stay pure CRLF.

## Validator architecture (current)

- `CONSUMERS` tuple: 9 consumers, each with `registry` path
  (`docs/ui-compatibility.md`, except `Tiktok-video` → `docs/tiktok-ui-compatibility.md`).
- `REQUIRED_CONCEPTS` — 9 concepts with Vietnamese+English markers; per-record
  subset is `RECORD_CONCEPTS` (7: id_owner, ui_signature, fallback_order,
  safety_bounds, verification, regression_tests, affected_consumers).
- `_split_records` splits on `##`/`###` headings after stripping fences;
  `_has_concept_label_bullet` skips structural sections (`## Mẫu contract`,
  `## Quy tắc thay đổi`) — only blocks that open a bullet with a known concept
  label count as records.
- `check_workspace(root, legacy_warnings: list[str] | None = None)` — returns
  findings list; optionally collects legacy warnings into a caller list
  (backward compatible: existing tests call with 1 arg).
- `main()`: prints findings to stdout (exit 1 if any); prints legacy warnings to
  **stderr** + summary `[check-ui-compatibility] total legacy warnings: N (không
  fail, không retroactive)`; otherwise stdout `OK: 9/9 consumers`, exit 0.

## New classification logic (`_is_new_record`)

```python
_NEW_RECORD_CUTOFF = "2026-08-09"  # string compare works: ISO dates

def _heading_date(heading: str) -> str:
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", heading)
    return m.group(1) if m else ""

def _record_owner_id(body: str) -> str:
    m = re.search(r"-\s*(?:id/)?owner\s*:\s*`([^`]+)`", body, flags=re.IGNORECASE)
    return m.group(1) if m else ""

def _is_new_record(heading: str, body: str) -> bool:
    hd = _heading_date(heading)
    if hd and hd >= _NEW_RECORD_CUTOFF:   # heading carries date >= cutoff
        return True
    owner_id = _record_owner_id(body)     # no heading date → fall back to ID
    return "20260809" in owner_id or "2026-08-09" in owner_id
```

- Heading examples that classify NEW: `## Record thiếu field 2026-08-09`.
- ID-only NEW: heading `## Record mới theo ID` + `- ID/owner:
  \`ui-open-tiktok-auto-ladder-per-signature-20260809\`` → NEW via ID.
- `- Owner:` lines (no `id/`) are matched by the `(?:id/)?owner` alternation —
  Tiktok-video records use `- Owner:`.

## Real-workspace baseline numbers (D:\Taadaa, 2026-08-09)

- Before: 66 findings `registry_record_incomplete:*`, exit 1, core 0 findings.
  All 66 were pre-existing debt (oldest consumer records, latest real date
  2026-08-08 in Tiktok_Reg).
- After: exit 0, stdout `OK: 9/9 consumers`, 66 legacy warnings on stderr.
- The one genuinely NEW record present (`COMPAT-OPEN-TIKTOK-002`, canonical
  `ui-open-tiktok-auto-ladder-per-signature-20260809`) was complete → no finding,
  as expected.

## Tests updated (tests/test_check_ui_compatibility.py — 7 passed)

Kept 5 old tests (they still pass because their fixtures use 2026-08-09 dates →
still NEW → still fail-closed), added 2:
- `test_legacy_record_missing_concepts_warns_without_failing` — old record
  (2026-08-01) missing concepts → 0 findings, warning in legacy list, warning
  contains heading.
- `test_new_record_missing_concepts_fails_for_heading_date_and_id` — heading
  NEW + ID-only NEW → exactly 2 findings, 0 warnings.

## EOL-preserving python patch script pattern (used here)

Mandate: "python binary, KHÔNG patch tool/sed" (byte-exact CRLF). Recipe:
1. write_file the script (never heredoc — braces/quotes/unicode mangle in bash).
2. read bytes → decode utf-8 (strip BOM if present, keep it on write) →
   assert `\r\n` present → normalize `\r\n`→`\n` in memory.
3. every hunk: `assert text.count(old) == 1` then `text.replace(old, new)`.
4. write: `("\ufeff" if bom else "") + text.replace("\n", "\r\n")` → utf-8 bytes.
5. verify: `crlf == lf and cr == crlf` → pure CRLF.

Pitfalls hit:
- **Unterminated last line**: `old_tail` anchor ending in `\n` fails to match a
  file ending `findings)` with no EOL. Diagnose with `tail -c 200 f | od -c`;
  anchor without trailing newline.
- **`/c/Users/...` path mangling**: from a `cd /d/Taadaa/*` cwd,
  `python /c/Users/Kibe/x.py` → uv python can't open `D:\c\Users\...`; even
  `python "$HOME/x.py"` mangles to `C:\c\Users\...`. Working invocation:
  `python "$(cygpath -w /c/Users/Kibe/x.py)"`.
- **`$?` after pipe**: `python ... | tail -15; echo $?` reports tail's exit (0)
  — use `> /tmp/out 2>&1; echo "REAL_EXIT=$?"` to capture the validator's code.
- Two-stage patch (tool file patched first, then tests) split into two scripts
  so a failing anchor in the second doesn't restart the first.