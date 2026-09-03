# Snippet-splice edits — inserting large code payloads into LF/CRLF files

Verified 2026-08-09 (Tiktok-video RE-AUDIT v2, `tests/test_tiktok_workflow.py` — LF-pure
test file, CẤM patch tool/sed). Use when an edit script must INSERT many new lines of
code (new test methods, new handlers) whose content is backslash-heavy, has emoji /
Vietnamese diacritics, or nested quotes.

## Why not inline

Writing new code blocks inline in the edit script (even as `r'''...'''` raw strings)
failed 2× in one session:

- `\\#`-style escapes get collapsed/mangled (raw string ≠ what the file must contain);
- quotes inside the payload terminate the outer string;
- emoji/Vietnamese bytes get corrupted mid-block;
- re-typing the OLD block to anchor on it invites copy-paste typos (`RECEPTURED`,
  `C_CAPTION`, dropped words) that silently break `count == 1` matching.

## Pattern

1. **Payload = separate snippet file, wrapped in a dummy class** so `write_file`'s
   syntax checker validates the content:

   ```python
   class _SNIP:
       def test_p1_03_hashtag_caption_survives_sanitize_and_escape(self):
           """..."""
           from tiktok_workflow.state_machine import StateMachine
           ...
   ```

   - Methods are 4-space indented, `self` is just a parameter name → valid module-level
     syntax → lint passes.
   - If you write bare methods at module level, the linter reports
     `IndentationError: unexpected indent` — that is the signal to wrap in the class.

2. **Editor script reads the snippet, strips the wrapper, splices at a short anchor**:

   ```python
   def load_snip(path):
       lines = open(path, encoding="utf-8", newline="").read().split("\n")
       assert lines[0] == "class _SNIP:", lines[0]
       return "\n".join(lines[1:]).lstrip("\n")

   # LF-pure target: read/write with newline="" (no translation), assert no CR.
   src = open(TEST, encoding="utf-8", newline="").read()
   assert "\r" not in src, "test file must stay LF-pure"
   anchor = "        assert len(fallback_calls) == 1"   # SHORT unique trailing line
   assert src.count(anchor) == 1, src.count(anchor)
   src = src.replace(anchor, anchor + "\n" + load_snip("_snip_e.py"))
   open(TEST, "w", encoding="utf-8", newline="").write(src)
   ```

   - Anchor on a short, unique END line of the previous test — not on the whole old
     block (fewer characters to typo; insertion = `anchor + "\n" + snippet`).
   - CRLF targets: read with `newline=None` (universal), write with `newline=None`
     (default) so `\n` → `\r\n` on Windows. Only safe when the file is uniformly CRLF.

3. **Verify**: `py_compile.compile(path, doraise=True)`; for LF files assert
   `"\r" not in src` after write; run the focused `pytest -k` selector.

4. **Cleanup**: delete snippet files + editor script before handoff (they are untracked
   files in the repo root otherwise).

## Session artifact (worked example)

The 8 new regression tests for the v2 audit (P1-01..08 + P2-01) were composed this way:
`_snip_t1.py` … `_snip_t4end.py`, `_snip_e.py`, `_snip_f.py`, each `class _SNIP:`-wrapped,
spliced at unique anchors. Full per-finding detail: `tiktok-upload-ui-recovery` →
`references/reaudit-v2-fixes.md`.
