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

# ---------------------------------------------------------------------------
# Step 3: dropped-byte reconstruction (runs only AFTER step 2).
#
# cp1252 has no glyph for 0x81 0x8D 0x8F 0x90 0x9D, so a lossy hop deletes
# that byte (or turns it into U+FFFD / "?").  Once step 2 has decoded every
# *complete* sequence, any "á»" still in the text is the lead of a Vietnamese
# letter E1 BB xx whose last byte was lost: one of
#     0x81 ề   0x8D ọ   0x8F ỏ   0x90 Ố   0x9D ờ
# The byte is gone for good, so the letter is chosen from the syllable around
# it (Vietnamese phonotactics + the most frequent words).  This MUST run after
# step 2: run before it, a rule like "bá»" -> "bỏ" eats the lead of an intact
# "bá»™" (bộ) and leaves "bỏ™" behind.
# ---------------------------------------------------------------------------

_LETTER = r"[^\W\d_]"
_DROPPED_RE = re.compile(rf"\u00e1\u00bb(\ufffd|\?(?={_LETTER}))?(?!{_C})")
_SUFFIX_RE = re.compile(rf"{_LETTER}*")

_O_DOT, _O_HOOK, _O_GRAVE, _E_GRAVE = "\u1ecd", "\u1ecf", "\u1edd", "\u1ec1"

# rime -> (onset -> letter, default letter)
_DROPPED_BY_RIME: dict[str, tuple[dict[str, str], str]] = {
    "": ({"b": _O_HOOK, "nh": _O_HOOK, "x": _O_HOOK, "tr": _O_HOOK, "n": _E_GRAVE,
          "v": _E_GRAVE, "\u0111": _E_GRAVE, "k": _E_GRAVE, "ngh": _E_GRAVE,
          "h": _O_DOT, "l": _O_DOT}, _O_GRAVE),
    "i": ({"h": _O_HOOK, "kh": _O_HOOK, "gi": _O_HOOK, "s": _O_HOOK, "t": _O_HOOK,
           "m": _O_DOT, "g": _O_DOT, "ch": _O_DOT}, _O_GRAVE),
    "n": ({"v": _O_GRAVE, "h": _O_GRAVE, "s": _O_GRAVE,
           "n": _E_GRAVE, "\u0111": _E_GRAVE, "m": _E_GRAVE, "r": _E_GRAVE}, _O_DOT),
    "ng": ({"h": _O_HOOK, "l": _O_HOOK, "b": _O_HOOK, "x": _O_HOOK, "ph": _O_HOOK}, _O_DOT),
    "a": ({"th": _O_HOOK, "kh": _O_HOOK}, _O_DOT),
    "e": ({}, _O_HOOK),
    "nh": ({}, _E_GRAVE),
    "m": ({"kh": _O_DOT}, _E_GRAVE),
    "u": ({}, _E_GRAVE),
}
_STOP_FINALS = ("c", "t", "p")  # only sắc/nặng tones allowed -> "ọ"


def _pick_dropped_letter(prefix: str, suffix: str) -> str:
    p, s = prefix.lower(), suffix.lower()
    letters = prefix + suffix
    # In UPPERCASE text every other E1 BB xx capital survives cp1252; only
    # "Ố" (E1 BB 90) can be the lost one.
    if letters and letters.isupper() and (suffix or len(prefix) >= 2):
        return "\u1ed0"
    if p.endswith("\u01b0"):  # ư: "ườ" (người, trường) / "ượ" (được)
        return "\u1ee3" if s.startswith(_STOP_FINALS) else _O_GRAVE
    if p.endswith(("i", "y")) and p != "gi":  # "iề"/"yề" (điều, quyền)
        return _E_GRAVE
    if s.startswith(_STOP_FINALS):
        return _O_DOT
    rime = s if s in _DROPPED_BY_RIME else s[:1] if s[:1] in _DROPPED_BY_RIME else None
    if rime is None:
        return _O_DOT
    by_onset, default = _DROPPED_BY_RIME[rime]
    return by_onset.get(p, default)


def _repair_dropped_viet(text: str) -> str:
    def sub(m: "re.Match[str]") -> str:
        start = m.start()
        i = start
        while i > 0 and text[i - 1].isalpha():
            i -= 1
        prefix = text[i:start]
        suffix = _SUFFIX_RE.match(text, m.end()).group(0)
        if not m.group(1):
            # No loss marker: "á»" may be a real "á" + closing guillemet.
            if not prefix and not suffix:
                return m.group(0)
            if not suffix and text.rfind("\u00ab", 0, start) > text.rfind("\u00bb", 0, start):
                return m.group(0)
        return _pick_dropped_letter(prefix, suffix)

    if "\u00e1\u00bb" in text:
        text = _DROPPED_RE.sub(sub, text)
    if "\u00c4" in text:  # Đ = C4 90, 0x90 lost
        text = _DROPPED_D_RE.sub("\u0110", text)
    if "\u00c3\ufffd" in text:  # Á = C3 81 (Í/Ý share the lost-byte shape)
        text = text.replace("\u00c3\ufffd", "\u00c1")
    if "\u00e2\ufffd" in text:  # dingbats E2 9D xx (❌ ❗ ❤) lost their 0x9D
        text = _DROPPED_DINGBAT_RE.sub(_decode_dingbat, text)
    if "\u1edd\ufffd" in text:  # "mọi": an older repair's leftover of "mọi"
        text = _OLD_MOI_RE.sub(lambda m: m.group(1) + "\u1ecd\u0069", text)
    if "\u00f0\u0178" in text:  # 4-byte emojis F0 9F xx xx whose byte 3 was lost in cp1252
        text = _DROPPED_EMOJI_RE.sub(_decode_dropped_emoji, text)
        text = _STRAY_EMOJI_RE.sub("", text)
    return text


_DROPPED_DINGBAT_RE = re.compile(rf"\u00e2\ufffd({_C})")
_OLD_MOI_RE = re.compile(r"(?<![^\W\d_])([mM])\u1edd\ufffdi")
_DROPPED_EMOJI_RE = re.compile(rf"\u00f0\u0178[\ufffd\?]?(?:([\x81\x8d\x8f\x90\x9d])|({_C}))")
_STRAY_EMOJI_RE = re.compile(r"\u00f0\u0178[\ufffd\?]?")
_EMOJI_DEFAULT_B3: dict[int, int] = {
    0x9B: 0x8F, 0x86: 0x8F, 0x85: 0x8F, 0x94: 0x8F, 0xA0: 0x8F, 0xA2: 0x8F,
    0xA5: 0x8F, 0xA6: 0x8F, 0xB7: 0x8F, 0x80: 0x8D, 0x8E: 0x8D, 0x95: 0x8D,
    0xBA: 0x8D, 0xBB: 0x8D, 0xB6: 0x90, 0xB1: 0x90,
}


def _decode_dropped_emoji(m: "re.Match[str]") -> str:
    tok = m.group(2)
    if not tok:
        return ""
    b4 = int(tok[-2:], 16) if len(tok) > 1 else _BYTE_FOR_CHAR.get(tok)
    if b4 is None or not (0x80 <= b4 <= 0xBF):
        return ""
    b3 = _EMOJI_DEFAULT_B3.get(b4, 0x8F)
    try:
        return bytes([0xF0, 0x9F, b3, b4]).decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        return ""


def _decode_dingbat(m: "re.Match[str]") -> str:
    try:
        return bytes([0xE2, 0x9D, _BYTE_FOR_CHAR[m.group(1)]]).decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        return m.group(0)


_VIET_VOWELS = (
    "aàáảãạăằắẳẵặâầấẩẫậeèéẻẽẹêềếểễệiìíỉĩịoòóỏõọôồốổỗộơờớởỡợuùúủũụưừứửữựyỳýỷỹỵ"
)
_DROPPED_D_RE = re.compile(
    rf"\u00c4\ufffd?(?=[{_VIET_VOWELS}{_VIET_VOWELS.upper()}])"
)

# Damage left by the pre-2026-11-18 repair, which ran "bá»"->"bỏ",
# "vá»"->"về", "giá»"->"giờ" BEFORE decoding and so split intact sequences:
# "bá»™" (bộ) became "bỏ™", "vá»¡" (vỡ) "về¡", "giá»¯a" (giữa) "giờ¯a".
# Undo it by re-reading the orphaned continuation char as the third byte.
# Punctuation-looking continuation chars (smart quotes, dashes, NBSP, «»...)
# are excluded so legitimate text like `“giờ”` is never touched.
_PUNCT_CONT = set("\u2026\u2018\u2019\u201c\u201d\u2022\u2013\u2014\u00a0\u00a9\u00ae\u00b0\u00b1\u00b7\u00bb")
_SPLIT_CONT = "".join(
    re.escape(ch) for ch, b in _BYTE_FOR_CHAR.items()
    if 0x80 <= b <= 0xBF and ch not in _PUNCT_CONT and ch != "\u00ab"
)
_OLD_SPLIT_RE = re.compile(
    rf"(?<!{_LETTER})([bB]\u1ecf|[vV]\u1ec1|[gG]i\u1edd)"
    rf"(?:([{_SPLIT_CONT}])|\u00ab(?={_LETTER}))"
)


def _undo_old_split(text: str) -> str:
    def sub(m: "re.Match[str]") -> str:
        ch = m.group(2) or "\u00ab"
        try:
            letter = bytes([0xE1, 0xBB, _BYTE_FOR_CHAR[ch]]).decode("utf-8")
        except (KeyError, UnicodeDecodeError):
            return m.group(0)
        return m.group(1)[:-1] + letter

    return _OLD_SPLIT_RE.sub(sub, text)


_MAX_PASSES = 4


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
        # Step 1: patch byte-loss leftovers that are never legitimate.
        if "�" in out:
            # "Ä�" / "â€�" / "ï¸�" are never legitimate: always patch.
            for pattern, repl in _LEFTOVERS:
                out = re.sub(pattern.pattern.replace("�?", "�"), repl, out)
        # Undo splits left by the old pre-decode repair ("bỏ™" -> "bộ").
        new = _undo_old_split(out)
        if new != out:
            repaired = True
            out = new
        # Step 2: decode mojibake sequences, repeating to undo nesting.
        for _ in range(_MAX_PASSES):
            new = _SEQ_RE.sub(_decode_seq, out)
            if new == out:
                break
            repaired = True
            out = new
        # Step 3: rebuild letters whose last byte was lost (needs step 2
        # done first, so only genuinely incomplete sequences are left).
        new = _repair_dropped_viet(out)
        if new != out:
            repaired = True
            out = new
        if repaired:
            for pattern, repl in _LEFTOVERS:
                out = pattern.sub(repl, out)
            out = _LONE_A_GRAVE_RE.sub("à", out)
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
