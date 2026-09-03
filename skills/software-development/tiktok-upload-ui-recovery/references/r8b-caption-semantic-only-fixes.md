# R8b — Sol R7 caption P1 fixes: semantic-caption-only verification (2026-08-09)

Audit source: `C:\Users\Kibe\AppData\Local\Temp\hermes-audit-sol-r7-standard-output-<ts>.txt` (Sol REJECT, 5 P1s). R8b scope = P1-4 + P1-5 (caption). Status: tests + source + docs done, full pytest pass, EOL verified, NO commit.

## P1-4 — Remove whole-screen success path (`_caption_is_visible`)

`_caption_is_visible(xml, caption)` accepts the full caption substring OR every hashtag ANYWHERE on screen (suggestion/search/preview). That let typing fallback return True while the caption field was empty/wrong.

**Fix**: every caption typing postcondition now verifies ONLY via `_caption_typing_ratio_ok` (semantic field text → hashtag ≥70% + SequenceMatcher ≥60% / short caption edit distance ≤25%). Call sites changed in `state_machine.py`:
- `_fill_caption_clipboard` tokenized path (was `if self._caption_is_visible(adapter.dump_ui(), caption)`)
- `_fill_caption_clipboard` paste path (2 re-check dumps after `Dán`/`Paste`)
- `_fill_caption_typing_fallback` final verify (was `_caption_is_visible` OR ratio — whole-screen branch DELETED)
- `_fill_caption_with_tiktok_hashtag_button` final verify

`_caption_is_visible` kept only as an unused evidence-only helper (do not delete wholesale without checking callers; now 0 call sites).

## P1-5 — Exact caption component IDs only (no generic substrings)

Old `_is_caption_field_node` used substring markers (`edit_text`, `edittext`, `desc`, `describe`, `text_input`, `input_edit`, `caption`) → `...:id/search_edit_text` qualified as a caption field.

**Fix**: class constant + exact matcher:

```python
KNOWN_CAPTION_COMPONENT_IDS = frozenset({
    "caption_edit_text", "description_edit_text", "post_description",
    "composer_caption", "g9u", "gv0",
})

# _is_caption_field_node: resource-id tail after '/' or `name`, casefold, IN set.
# search_edit_text / comment / message controls / anonymous EditText → False
# even when focused and holding the exact caption text (false-clean guard).
```

Also in `_find_caption_field`:
- resource-id lookup loop now iterates `sorted(KNOWN_CAPTION_COMPONENT_IDS)` (exact), no `"edit_text"` bare tail.
- text-hint loop dropped generic `"caption"` marker; kept only `Suy nghĩ của bạn / Thêm mô tả / Viết mô tả / Add caption`.
- anonymous wide-EditText fallback (≥400×60 px) now gated by `_xml_has_composer_post_proof(root)`: post label `đăng/post/tiếp/next` (text OR content-desc, NFC+casefold) or resource-id tail in `{rbp, sh8, shd}`. No composer proof → None (fail-closed).

Bounds/center identity path in `_caption_field_text_from_xml` unchanged (exact-bounds match still wins).

## Regression tests added (RED first, then GREEN)

- `test_caption_semantic_matcher_exact_ids_only` — all 6 valid IDs pass chunk+ratio+field_text; all 9 generic IDs (`search_edit_text`, `edit_text`, `edittext`, `text_input`, `input_edit`, `desc`, `description`, `comment_input`, `message_edit`) fail all three.
- `test_caption_field_text_respects_supplied_bounds_identity` — supplied bounds selects that exact node; no-identity path picks caption_edit_text over focused search_edit_text.
- `test_caption_typing_success_requires_semantic_caption_field` — full E2E: caption text in focused `search_edit_text` + empty `caption_edit_text` → `_fill_caption_clipboard` False, ratio/chunk False (old code returned True → this was the RED).
- `test_caption_typing_success_with_exact_caption_edit_text` — `caption_edit_text` holding text → clipboard-fail → typing fallback True.

## Existing test-fixture updates (predictable patterns — update, don't fight)

Tests whose dump was `<node text="caption"/>` (whole-screen) must expose a semantic field or they now fail-closed:
- `test_caption_ascii_input_is_verified`, `test_ascii_hashtags_are_sent_as_tokens_with_real_spaces`, `test_tokenized_caption_token_fail_clears_field_before_fallback`, `test_caption_clipboard_fail_falls_back_to_hashtag_button`, `test_caption_unicode_uses_clipboard_and_verifies_paste` → dump gains `<node class="android.widget.EditText" resource-id="caption_edit_text" bounds="[30,200][1050,300]" text="{caption}"/>`.
- Clear tests (`test_clear_caption_input_*` using anonymous EditText) → add `<node text="Đăng"/>` to each dump_seq entry so the composer-proof gate passes (they no longer match bare anonymous EditText alone).
- `test_caption_field_falls_back_to_wide_edit_text` → inverted: bare wide EditText now `None`; add second fixture with `Đăng` marker → field found, center (540, 1000).

## EOL-safe edit-script recipe (this round hit TWO new pitfalls)

Files: `state_machine.py` + `docs/tiktok-ui-compatibility.md` = pure CRLF; `tests/test_tiktok_workflow.py` = pure LF. Never patch tool/sed these; use a Python patcher:

1. Read bytes → `is_crlf = b"\r\n" in raw` → decode → `content = content.replace("\r\n", "\n")` **FIRST**. Anchors written with plain `\n` will NOT match raw CRLF content (hit this round: `assert known_anchor in content` failed).
2. Patch with `\n` anchors, `assert old in content` for every block (abort on 0/multiple).
3. Write back `content.replace("\n", "\r\n")` if `is_crlf`, via `io.open(path, "w", encoding="utf-8", newline="")`.
4. Verify: `open(path,'rb').read()` → CRLF count == line count, bare LF == 0 (or vice versa for tests).

**Pitfall (new)**: `write_file` writing a Python patcher whose content contains `"""` docstrings → the tool escapes them (`\"\"\"`), so anchors embedding `"""` never match the real file. Use `'''` triple-single-quoted strings for any anchor/new block that contains `"""`. Verify with `python -c` reading the written file back before running the patcher.

## Verification sequence (this round)

```bash
# RED
PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" \
  -m pytest tests/test_tiktok_workflow.py -q -k "test_caption_semantic_matcher_exact_ids_only or test_caption_field_text_respects_supplied_bounds_identity or test_caption_typing_success_requires_semantic_caption_field or test_caption_typing_success_with_exact_caption_edit_text"
# expect 2 failed 2 passed (2 new E2E/matcher tests RED on old code)
# GREEN + full caption class
... -k "CaptionFill or caption or composer or hashtag"   # 52 passed
# full suite
... -m pytest tests/test_tiktok_workflow.py -q            # expect all green
```

Note: pytest cache warning `Permission denied .pytest_cache` is benign (dirty worktree permission). `_caption_is_visible` remaining 3 hits = definition + 2 comment strings.
