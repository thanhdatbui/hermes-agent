# Profile identity: Unicode normalization & Bidi Control Stripping

## Symptom
1. A feed/session profile verification returns `profile account mismatch` or `profile verification mismatch`, even though the expected account is visibly active.
2. Mode 2 follower list or Path B cross-verification stops with `MANUAL_REVIEW: Path B fail (row nói followed nhưng profile manual)` or `missing_header_handle`, even though the target profile was opened and displays "Đã follow" / "Bạn bè".

## Root cause
TikTok UI XML frequently wraps `@username` with invisible bidi/isolate/zero-width formatting characters, including:
- LRM / RLM: `\u200e`, `\u200f`
- Unicode Isolates: `\u2066`, `\u2067`, `\u2068`, `\u2069`
- Legacy Bidi Embeddings: `\u202a`, `\u202b`, `\u202c`, `\u202d`, `\u202e`
- Zero-Width / Invisible Markers: `\u200b`, `\u200c`, `\u200d`, `\ufeff`, `\u061c`, `\u2060`

When `_find_header_handle_node` or `_extract_row_handle` applies a strict regex like `r"^@[a-zA-Z0-9_.]+$"` or `_normalize_handle` strips `@` on raw strings, the leading/trailing invisible characters prevent regex match (`_HANDLE_FIELD_RE.fullmatch(raw_text)` returns `False`). This results in `missing_header_handle` or identity extraction failure, falsely classifying a valid followed profile as `MANUAL_REVIEW`.

## Correct fix
Define canonical format character set `_FORMAT_CHARS` and clean all handles and raw XML strings before regex checking, parsing, or equality checks:

```python
_FORMAT_CHARS = {
    "\u200e", "\u200f",  # LRM / RLM
    "\u2066", "\u2067", "\u2068", "\u2069",  # LRI / RLI / FSI / PDI
    "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",  # legacy bidi
    "\u200b", "\u200c", "\u200d", "\ufeff",  # ZWSP / ZWNJ / ZWJ / BOM
    "\u061c", "\u2060",  # ALM / WJ
}

def _clean_handle_text(text: str) -> str:
    """Strip Unicode bidi, isolate, and invisible format characters."""
    if not text:
        return ""
    return "".join(ch for ch in text if ch not in _FORMAT_CHARS).strip()

def _clean_xml_format_chars(xml_text: str) -> str:
    """Strip Unicode bidi and invisible format characters from XML string."""
    if not xml_text:
        return ""
    return "".join(ch for ch in xml_text if ch not in _FORMAT_CHARS)

def _normalize_handle(handle: str) -> str:
    """Normalize handle for exact comparison: strip bidi/format chars, casefold and strip @."""
    cleaned = _clean_handle_text(handle)
    return cleaned.lstrip("@").casefold()
```

Apply `_clean_handle_text` on node `text` and `content_desc` BEFORE evaluating `_HANDLE_FIELD_RE.fullmatch()`, and wrap XML dumps with `_clean_xml_format_chars()` before invoking `profile_identity_from_xml()`.

## Regression Fixtures & Tests
- `test_normalize_handle_strips_unicode_bidi_and_isolate_characters`
- `test_find_header_handle_node_matches_bidi_wrapped_handles`
- `test_path_b_verify_accepts_bidi_wrapped_profile_header`
- `test_extract_row_handle_strips_bidi_format_chars`

## Git Workspace Operational Discipline
- **CẤM TỰ Ý GIT RESET**: Tuyệt đối không chạy `git reset --hard` hoặc các thao tác hủy bỏ/rollback git nguy hiểm trên workspace farm/live repos khi chưa có yêu cầu hoặc xác nhận rõ ràng từ user.
- Khi gặp tình trạng diverged/stale commit do rebase trước đó, kiểm tra diff chi tiết, xác định nguyên nhân và thông báo rõ cho user thay vì tự động reset.
