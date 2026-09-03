# Caption identity fix patterns (Tiktok-video, F1/F2/F3/F6 — 2026-08-09)

Proven on `D:\Taadaa\Tiktok-video` `scripts/tiktok_workflow/state_machine.py`:
4 CONFIRMED caption identity holes fixed so `TestCaptionEvidencePhase` turned
GREEN with full suite green (362 passed). The durable shape: **every side
effect (MOVE_END/DEL keyevent, Dán/Paste tap) must be preceded by an exact
caption identity gate; then reconcile with legacy GREEN tests that assert the
OLD behavior on the same helper.** Reconciliations below are the non-obvious
part — a naive gate breaks a legacy test, and the fix is a presence/budget
scoping rule, not a test change.

## The 4 holes and their gates

| Hole | Function | Gate added |
|------|----------|------------|
| F1 | `_caption_field_text_from_xml` (match_bounds/match_center branch) | node at identity bounds must pass `_is_caption_field_node`; generic same-bounds node only honored while a semantic caption node still exists in the dump, else `None` |
| F2 | `_clear_caption_input` | after tap ACK, recapture dump; any focused generic EditText → return False with NO MOVE_END/DEL; exact caption node must still re-identify at identity bounds/center |
| F3 | `_fill_caption_clipboard` (paste path) | Dán/Paste tap gated on `_xml_has_caption_field(xml_text)` (pure-XML, same-dump identity); long-press path re-verifies identity on the post-long-press dump |
| F6 | `_find_caption_field` step 1 (allowlist) | `_xml_has_exact_resource_id_tail` re-verify when dump exposes EditText; `caption_edit_text_backup` rejected, exact `caption_edit_text` still selected |

## Rule 1: Dump-count budget (F2)

Legacy clear tests (`test_clear_caption_input_uses_single_long_delete`,
`test_clear_caption_input_taps_field_when_visible`,
`test_clear_caption_input_reidentifies_same_field_bounds`) provision EXACTLY
**2** `dump_ui()` responses: pre + post-clear. The current flow is
`find(dump1) → tap → keys → verify(dump2)`. If you insert an unconditional
post-tap dump for the F2 focus re-verify, the final verify consumes dump3 →
fake falls back to `"<hierarchy/>"`/`StopIteration` → `None` → False → legacy
tests break.

Working structure (exactly 2 dumps in the success path):
1. `field = _find_caption_field(adapter, adapter.dump_ui())`  # dump1
2. `tap(field.center)` — must be `is True` (None/False → fail-closed, no keys)
3. `post_tap_xml = adapter.dump_ui()`; `post_root = ET.fromstring(...)`  # dump2
4. Focus guard: any EditText with `focused="true"` and NOT
   `_is_caption_field_node` → return False (no keys)
5. `_caption_field_text_from_xml(post_root, match_bounds, match_center) is None`
   → return False (caption gone/moved)
6. Send MOVE_END + DEL
7. Final verify: **return True early when the post-tap root text is already
   empty; only otherwise re-dump** (dump3) to confirm cleared.

Legacy post-clear dumps carry `text=""` (simulating already-cleared), so step
7's early-True fires on dump2 and dump3 is never consumed. Production: post-tap
text is the OLD caption (non-empty) → keys sent → fresh dump shows cleared →
True. The early-True is what makes both worlds pass.

## Rule 2: Presence-gated bounds identity (F1)

`_caption_field_text_from_xml(root, match_bounds=..., match_center=...)`:
- node AT the identity bounds that IS a caption node → return its text (normal
  V3-01 re-identify).
- node at bounds that is GENERIC (search/comment reusing caption bounds):
  return its text ONLY if the dump still contains ANY semantic caption node
  (scan with `_is_caption_field_node`); caption gone → `None` (fail-closed —
  never report "cleared" from a generic field's emptiness).

This single rule satisfies BOTH:
- `test_f1_generic_edit_reusing_caption_bounds_returns_none` (caption node
  disappeared; generic occupies bounds → None), AND
- legacy `test_caption_field_text_respects_supplied_bounds_identity`
  (search-box bounds → its text, because a real `caption_edit_text` node is
  still present in the same dump).

The discriminator is **presence of a caption node anywhere in the dump**, not
the node's own identity.

## Rule 3: Scope exactness gates to real impostor risk (F6, F3)

- **F6**: production `TikTokAdapter._find_ui_element` matches resource-id by
  SUBSTRING (`expected not in rid`) → `caption_edit_text_backup` matches query
  `caption_edit_text`. Enforce exact terminal tail in `_find_caption_field`
  step 1, but ONLY when the dump exposes EditText
  (`_xml_has_any_edit_text`). An unconditional gate broke
  `test_caption_field_uses_live_gv0_resource` — that fake adapter returns a
  gv0 field from an EMPTY `<hierarchy />` (no impostor node exists), so the
  gate must defer to the adapter on dumps with no EditText.
- **F3**: gate paste taps with a pure-XML helper `_xml_has_caption_field(xml)`
  (parse + `_is_caption_field_node` on EditTexts), NOT `_find_caption_field` —
  several legacy FakeAdapters (`test_caption_unicode_uses_clipboard_and_verifies_paste`)
  lack `_find_ui_element`; calling it raises AttributeError → caught → False,
  silently breaking tests that expect the Dán tap to proceed. Long-press path
  must re-verify identity on the post-long-press dump before tapping paste.

## Verification recipe (EOL/diff)

- Focused: `PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" python -m pytest
  tests/test_tiktok_workflow.py::TestCaptionEvidencePhase -q` → 4 passed.
- Full: same file, `-q` → 362 passed (any 1 failure → run it alone; if it's a
  legacy test, it's your gate scoping, not a pre-existing failure).
- EOL: `state_machine.py` pure CRLF (`count(b'\r\n') == count(b'\n')`, 0 lone
  LF) — edit via CRLF-safe binary replace with `assert count(old)==1` per
  block (see SKILL.md "Multi-file mixed-EOL edits"); tests pure LF.
- `git diff --check` clean; only state_machine.py touched.
