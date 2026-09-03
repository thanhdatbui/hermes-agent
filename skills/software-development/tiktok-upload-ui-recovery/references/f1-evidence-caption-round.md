# Sol evidence-round fixes: P1-1 focused-proof + P1-2 exact-tail correlation (2026-08-09)

Round after R9b (`r9b-caption-exact-identity-fixes.md`). Sol re-audit rejected with two
numeric-proof holes. Fix source ONLY (`scripts/tiktok_workflow/state_machine.py`), no
test/doc edits, no commit; keep 362 green + EOL/diff clean (state_machine.py CRLF pure,
tests LF pure, `git diff --check` clean). Final state: source FIXED, focused phase 4/4,
full suite 362/362, both Sol proofs satisfied, NO commit.

## The evidence phase (TestCaptionEvidencePhase)

`tests/test_tiktok_workflow.py` has class `TestCaptionEvidencePhase` (F1/F2/F3/F6) — the
Sol "design-audit evidence" regressions. They were GREEN before this round; the two P1
holes were NOT covered by them:

- F1: generic EditText reusing old caption bounds → `_caption_field_text_from_xml` must
  return None (fail-closed), not `""`/generic text.
- F2: post-tap dump = caption `focused="false"` + generic `comment_input` `focused="true"`
  at same bounds → `_clear_caption_input` False + ZERO keyevents.
- F3: clipboard path never taps Dán/Paste before caption identity established.
- F6: production `TikTokAdapter._find_ui_element` substring match — dump with ONLY
  `caption_edit_text_backup` → `_find_caption_field` None; exact ID still returns field.

## P1-1 — `_clear_caption_input` focused-proof

**Sol proof**: post-tap XML containing ONLY the same exact caption node (`focused="false"`)
triggered zero generic-focus guards (F2 guard only catches a *focused generic* node),
`_caption_field_text_from_xml` still re-identified OK, then 2 ADB shell keyevents
(MOVE_END + batched DEL) were sent into whatever control was actually focused.
Expected side effects: zero.

**Fix shape** (before the MOVE_END shell): scan post-tap `post_root` for EditText nodes
passing `_is_caption_field_node` at the captured identity bounds/center (bounds-equal OR
center-contained, mirroring `_caption_field_text_from_xml` hit logic):
- explicit `focused="false"` on that exact node → `return False`, no keyevents;
- at least one identity node that is NOT explicitly unfocused → proceed;
- none found → fail-closed (keep the pre-existing re-identify guard too).

**CRITICAL semantics decision — missing `focused` attr counts as OK, only explicit
`focused="false"` fails** (`node.attrib.get("focused", "true") == "false"`). The old
green tests (`test_clear_caption_input_taps_field_when_visible`, `..._uses_single_long_delete`,
`..._reidentifies_same_field_bounds`) dump the post-tap caption node WITHOUT any
`focused` attribute and expect success; strictly requiring `focused="true"` breaks them.
Constraint was "362 stay green" → missing attr must proceed. Real dumps always carry the
attr, so production strictness lives in the explicit-false branch.

## P1-2 — `_find_caption_field` exact-tail correlation

**Root proof**: two-node dump — `caption_edit_text_backup` FIRST at center (50,50),
exact `caption_edit_text` SECOND at (250,250). Production adapter substring-match returns
the FIRST node (backup, (50,50)), while the global `_xml_has_exact_resource_id_tail`
check passes because the exact node exists elsewhere in the dump.

**Fix shape**: after an adapter hit with `has_edit_text = _xml_has_any_edit_text(xml_text)`:
1. keep the global exact-tail gate;
2. NEW: `if has_edit_text and not _xml_has_caption_at_center(xml_text, field["center"]): continue`
   — parse the dump, the node containing the returned center must pass
   `_is_caption_field_node`; if it's an impostor at that center, skip the candidate and
   let the parsed-exact-nodes path (code-path 2, `_is_caption_field_node` allowlist scan)
   select the exact node → returns (250,250).
- **Do NOT verify when the dump has no EditText** — `test_caption_field_uses_live_gv0_resource`
  (`_find_caption_field(Adapter(), "<hierarchy />") == {"center": (330,460)}`) requires the
  adapter-only gv0 live-resource compat path. Only correlation when impostor risk is real.
- `_xml_has_caption_at_center` must NOT require `class EditText` on the verified node —
  `test_clear_caption_input_taps_field_when_visible` first-find dump has
  `<node resource-id="caption_edit_text" .../>` with NO class attr; identity check
  (`_is_caption_field_node` on resource-id tail OR name) alone is the correct gate.

## Verification (all real runs)

1. Focused: `PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" python -m pytest tests/test_tiktok_workflow.py -q -k TestCaptionEvidencePhase` → 4 passed.
2. Full: `... pytest tests/test_tiktok_workflow.py -q` → **362 passed, 0 failed** (count unchanged).
3. EOL: binary count check — state_machine.py CRLF=line-count, 0 lone LF/CR; tests LF
   pure; `git diff --check` clean.
4. Direct proof simulation (no test-file changes): production `TikTokAdapter` +
   `StateMachine` — P1-2 two-node dump returns center (250,250); P1-1 fake adapter with
   pre/post dump (post = only exact caption node `focused="false"`) → `False` +
   `keyevents == []`. Assert both, matching Sol's expected side-effect counts.