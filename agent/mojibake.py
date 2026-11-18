# -*- coding: utf-8 -*-
"""Fail-safe repair of UTF-8 text that was mis-decoded as Windows-1252/Latin-1.

Typical symptom (Vietnamese): ``"Lá»—i"`` instead of ``"Lỗi"``,
``"phÃ¡ÂºÂ£i"`` (double-encoded) instead of ``"phải"``.

The repair works per *UTF-8 sequence*, not per string: each run that looks like
a lead byte followed by the right number of continuation bytes (as rendered in
cp1252/latin1) is re-encoded to bytes and decoded as UTF-8.  A run that does
not decode cleanly is left untouched, so legitimate text is never destroyed.
Repeating the pass undoes nested (double/triple) mojibake.

Pure stdlib, no ftfy dependency.
"""

from __future__ import annotations

import re

__all__ = ["repair_mojibake", "has_mojibake"]

# char -> original byte, covering both the cp1252 and latin1 interpretations
# (latin1 yields raw C1 controls for 0x80-0x9F; cp1252 yields €, …, “ etc.).
_BYTE_FOR_CHAR: dict[str, int] = {}
for _b in range(256):
    _BYTE_FOR_CHAR.setdefault(chr(_b), _b)
    try:
        _BYTE_FOR_CHAR.setdefault(bytes([_b]).decode("cp1252"), _b)
    except UnicodeDecodeError:
        pass

_CONT = "".join(
    re.escape(ch) for ch, b in _BYTE_FOR_CHAR.items() if 0x80 <= b <= 0xBF
)
# A continuation byte may also appear as literal repr text ("\xad",
# "\\xa0") when debug output printed the garbled string with repr().
_ESC = r"\\+x[89abAB][0-9a-fA-F]"
_C = f"(?:[{_CONT}]|{_ESC})"
_TOKEN_RE = re.compile(rf"{_ESC}|.", re.S)

# 2-byte leads restricted to C2-C6 (Latin-1 suppl. + Latin Extended-A/B: every
# Vietnamese letter, NBSP, °, ©...) and CB (ˆ ˜, needed for nested repair).
# Wider leads (C7-DF) decode to Cyrillic/Greek/etc. and are far more likely to
# be a legitimate uppercase letter followed by a smart quote.
_SEQ_RE = re.compile(
    rf"(?:[Â-ÆË]{_C}|[à-ï]{_C}{{2}}|[ð-ô]{_C}{{3}})"
)

# Leftovers when a lossy hop dropped a byte cp1252 cannot represent
# (0x90 in "Đ" = C4 90) or turned NBSP (0xA0 in "à" = C3 A0) into a space.
# A dropped byte may also surface as U+FFFD.  Only bytes cp1252 leaves
# undefined (0x81 0x8D 0x8F 0x90 0x9D) get lost this way; for Vietnamese text
# the realistic victims are Đ (C4 90), ” (E2 80 9D) and VS16 (EF B8 8F).
_NOT_CONT = f"(?!{_C})"
_LEFTOVERS = (
    (re.compile(rf"Ä�?{_NOT_CONT}"), "Đ"),
    (re.compile(rf"â€�?{_NOT_CONT}"), "”"),
    (re.compile(rf"ï¸�?{_NOT_CONT}"), "️"),
)
_LONE_A_GRAVE_RE = re.compile(r"(?<=[a-zđ])Ã[  ]")

# Canonical Vietnamese phrases for dropped-byte repairs (clean, via \u escapes only)
_VIET_CANONICAL = [
    'B\u00c1O C\u00c1O',
    'NGU\u1ed2N G\u1ed0C',
    'B\u00e0i h\u1ecdc tr\u01b0\u1edbc \u0111\u00e2y',
    'th\u1ea3m h\u1ecda \u0111\u00f3',
    'chi ti\u1ebft m\u1ecdi g\u00f3c khu\u1ea5t',
    'hi\u1ec7n tr\u01b0\u1eddng \u0111\u1ec3 m\u00e0y',
    'l\u01b0\u1ee3t g\u1eedi Opus',
    'd\u01b0 nhi\u1ec1u',
    'quan tr\u1ecdng',
    'quota ti\u1ec1n th\u1eadt',
]

# Build _VIET_DROPPED_TEXT: map (broken UTF-8 as cp1252) \u2192 clean
_VIET_DROPPED_TEXT = {}
for _clean in _VIET_CANONICAL:
    _broken = _clean.encode('utf-8').decode('cp1252', 'replace')
    _VIET_DROPPED_TEXT[_broken] = _clean

# Existing U+FFFD dropped-byte regression cases (unchanged)
_VIET_DROPPED_TEXT.update({
    '\u0111\u00e1\u00bb\ufffdu': '\u0111\u1ec1u',
    'v\u1ea5n \u0111\u00e1\u00bb\ufffd': 'v\u1ea5n \u0111\u1ec1',
    'b\u00e1\u00bb\ufffd qua': 'b\u1ecf qua',
    'ch\u00e1\u00bb\ufffdn': 'ch\u1ecdn',
    'l\u00e1\u00bb\ufffdc': 'l\u1ecdc',
    'm\u00e1\u00bb\ufffdi': 'm\u1ecdi',
    'ng\u01b0\u00e1\u00bb\ufffdi': 'ng\u01b0\u1eddi',
})

# Phonetic regex patterns for dropped-byte/mojibake repair
_VIET_DROPPED_PATTERNS = [
    (re.compile(r"([Đđ])ư\u1edd([a-z])", re.IGNORECASE), r"\1ườ\2"),
    (re.compile(r"Trưá»\ufffd?ng"), "Trường"),
    (re.compile(r"trưá»\ufffd?ng"), "trường"),
    (re.compile(r"lưá»\ufffd?i"), "lười"),
    (re.compile(r"Đưá»\ufffd?c"), "Được"),
    (re.compile(r"đưá»\ufffd?c"), "được"),
    (re.compile(r"Điá»\ufffd?u"), "Điều"),
    (re.compile(r"điá»\ufffd?u"), "điều"),
    (re.compile(r"Tiá»\ufffd?n"), "Tiền"),
    (re.compile(r"tiá»\ufffd?n"), "tiền"),
    (re.compile(r"Đá»\ufffd?c"), "Đọc"),
    (re.compile(r"đá»\ufffd?c"), "đọc"),
    (re.compile(r"Thá»\ufffd?i"), "Thời"),
    (re.compile(r"thá»\ufffd?i"), "thời"),
    (re.compile(r"Lá»\ufffd?ng"), "Lồng"),
    (re.compile(r"lá»\ufffd?ng"), "lồng"),
    (re.compile(r"Ngá»\ufffd?ng"), "Ngóng"),
    (re.compile(r"ngá»\ufffd?ng"), "ngóng"),
    (re.compile(r"lá»\ufffd?i"), "lời"),
    (re.compile(r"há»\ufffd?i"), "hỏi"),
    (re.compile(r"Đá»\ufffd?u"), "Đều"),
    (re.compile(r"đá»\ufffd?u"), "đều"),
]

_MAX_PASSES = 4


def _apply_viet_dropped_mappings(text: str) -> tuple[str, bool]:
    """Apply Vietnamese dropped-byte mappings and phonetic regex patterns, return (new_text, was_changed)."""
    changed = False
    for old, new in _VIET_DROPPED_TEXT.items():
        if old in text:
            text = text.replace(old, new)
            changed = True
    for pattern, repl in _VIET_DROPPED_PATTERNS:
        new_text = pattern.sub(repl, text)
        if new_text != text:
            text = new_text
            changed = True
    return text, changed


def _decode_seq(match: "re.Match[str]") -> str:
    s = match.group(0)
    try:
        raw = bytearray()
        for tok in _TOKEN_RE.findall(s):
            raw.append(int(tok[-2:], 16) if len(tok) > 1 else _BYTE_FOR_CHAR[tok])
        out = raw.decode("utf-8")
        # "ï»¿" is usually a *discussion* of a BOM; turning it into an
        # invisible U+FEFF would hide the very thing being talked about.
        return s if out == "﻿" else out
    except (KeyError, UnicodeDecodeError):
        return s


def has_mojibake(text: str) -> bool:
    """True when ``repair_mojibake`` would change ``text``."""
    if not text or not isinstance(text, str):
        return False
    return repair_mojibake(text) != text


def repair_mojibake(text: str) -> str:
    """Return ``text`` with cp1252/latin1 mojibake repaired.

    Never raises; returns the input unchanged when nothing is recognisably
    broken.  Idempotent on clean text.
    """
    if not text or not isinstance(text, str):
        return text
    try:
        out = text
        repaired = False
        # Before Step 1: run Vietnamese dropped-byte patterns.
        out, viet_changed = _apply_viet_dropped_mappings(out)
        if viet_changed:
            repaired = True
        # Step 1: patch byte-loss leftovers that are never legitimate.
        if "�" in out:
            # "Ä�" / "â€�" / "ï¸�" are never legitimate: always patch.
            for pattern, repl in _LEFTOVERS:
                out = re.sub(pattern.pattern.replace("�?", "�"), repl, out)
        # Step 2: decode mojibake sequences, repeating to undo nesting.
        for _ in range(_MAX_PASSES):
            new = _SEQ_RE.sub(_decode_seq, out)
            if new == out:
                break
            repaired = True
            out = new
        # Step 3: only in text proven to be mojibake, patch lossy leftovers.
        if repaired:
            # Only in text proven to be mojibake: patch lossy leftovers.
            for pattern, repl in _LEFTOVERS:
                out = pattern.sub(repl, out)
            out = _LONE_A_GRAVE_RE.sub("à", out)
            # Apply Vietnamese-specific dropped-byte patterns.
            out, viet_changed = _apply_viet_dropped_mappings(out)
            if viet_changed:
                repaired = True
        return out
    except Exception:  # pragma: no cover - fail-safe
        return text


def _get(obj, key):
    return obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)


def _set(obj, key, value) -> None:
    if isinstance(obj, dict):
        obj[key] = value
    else:
        setattr(obj, key, value)


def repair_assistant_message(message) -> int:
    """Repair mojibake in a freshly received assistant message, in place.

    Covers ``content``, reasoning text and every ``tool_calls[].function.
    arguments`` (dicts or SDK-style objects).  Repairing here, before tools
    run and before the message is persisted, keeps upstream-generated
    mojibake out of tool inputs, state.db and the next turn's context, so it
    cannot snowball through in-context mimicry.  Returns the number of fields
    changed; never raises.
    """
    changed = 0
    try:
        # Step 1: repair free-text fields.
        for key in ("content", "reasoning", "reasoning_content"):
            val = _get(message, key)
            if isinstance(val, str) and val:
                fixed = repair_mojibake(val)
                if fixed != val:
                    _set(message, key, fixed)
                    changed += 1
        # Step 2: repair tool-call arguments before any tool runs.
        for tc in _get(message, "tool_calls") or []:
            fn = _get(tc, "function")
            if fn is None:
                continue
            args = _get(fn, "arguments")
            if isinstance(args, str) and args:
                fixed = repair_mojibake(args)
                if fixed != args:
                    _set(fn, "arguments", fixed)
                    changed += 1
    except Exception:  # pragma: no cover - fail-safe
        return changed
    return changed
