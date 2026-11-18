import json
import pytest

from agent.mojibake import has_mojibake, repair_mojibake

ORIGINALS = [
    "Chào bạn, đây là tiếng Việt chuẩn",
    "Lỗi kiểm tra 🛠️ — “ok” …",
    "Đúng 100%! phải",
    "ĐANG 100%!",
]


@pytest.mark.parametrize("orig", ORIGINALS)
@pytest.mark.parametrize("enc,depth", [
    ("cp1252", 1), ("cp1252", 2),  # cp1252 is lossy (0x81/8D/8F/90/9D)
    ("latin1", 1), ("latin1", 2), ("latin1", 3),
])
def test_repairs_nested_mojibake(orig, depth, enc):
    text = orig
    for _ in range(depth):
        text = text.encode("utf-8").decode(enc, "replace")
    assert has_mojibake(text)
    assert repair_mojibake(text) == orig


@pytest.mark.parametrize("clean", [
    "Chào bạn, đây là tiếng Việt chuẩn. Dự án đang chạy ổn định.",
    "ĐÃ AN TOÀN 100% “NÓ” — “CÔ” … 🛠️ café naïve Ä",
    "",
    "plain ascii",
])
def test_clean_text_untouched(clean):
    assert repair_mojibake(clean) == clean
    assert not has_mojibake(clean)


def test_dropped_byte_replacement_char():
    assert repair_mojibake("Ä\ufffdANG") == "ĐANG"


def test_non_string_passthrough():
    assert repair_mojibake(None) is None


def test_telegram_sanitizer_is_fail_safe():
    from agent.mojibake import repair_mojibake
    moji = "L\u1ed7i".encode("utf-8").decode("cp1252")
    assert repair_mojibake(moji) == "L\u1ed7i"
    assert repair_mojibake("") == ""
    assert repair_mojibake(None) is None


def test_repairs_repr_escaped_continuation_bytes():
    assert repair_mojibake("tháº\xadt sự") == "thật sự"
    assert repair_mojibake("lÃ\\xa0 không") == "là không"
    # A lone escape not preceded by a lead char is left alone.
    assert repair_mojibake("bytes \xad here") == "bytes \xad here"


# === Assistant-message repair (model responses) ===


def test_repair_assistant_message_object_and_dict():
    from types import SimpleNamespace
    from agent.mojibake import repair_assistant_message

    moji = lambda s: s.encode("utf-8").decode("cp1252")
    msg = SimpleNamespace(
        content=moji("Bóc tách sự thật"),
        reasoning=None,
        tool_calls=[SimpleNamespace(function=SimpleNamespace(
            name="session_search", arguments='{"query":"%s","limit":5}' % moji("thêm 7 acc")))],
    )
    assert repair_assistant_message(msg) == 2
    assert msg.content == "Bóc tách sự thật"
    assert msg.tool_calls[0].function.arguments == '{"query":"thêm 7 acc","limit":5}'

    d = {"content": "sạch", "tool_calls": [{"function": {"arguments": '{"q":"%s"}' % moji("lỗi")}}]}
    assert repair_assistant_message(d) == 1
    assert d["tool_calls"][0]["function"]["arguments"] == '{"q":"lỗi"}'
    assert d["content"] == "sạch"


def test_repair_assistant_message_clean_is_noop():
    from types import SimpleNamespace
    from agent.mojibake import repair_assistant_message

    msg = SimpleNamespace(content="ĐÃ AN TOÀN “NÓ”", tool_calls=None)
    assert repair_assistant_message(msg) == 0
    assert msg.content == "ĐÃ AN TOÀN “NÓ”"


# === Tool-output and shell-hook encoding ===


def test_tool_result_message_repairs_mojibake():
    from agent.tool_dispatch_helpers import make_tool_result_message

    moji = "HƯỚNG DẪN: grep đệ quy".encode("utf-8").decode("cp1252")
    msg = make_tool_result_message("terminal", '{"error": "%s"}' % moji, "call_1")
    assert "HƯỚNG DẪN: grep đệ quy" in msg["content"]

    parts = [{"type": "text", "text": moji}, {"type": "image_url", "image_url": {"url": "x"}}]
    msg = make_tool_result_message("terminal", parts, "call_2")
    flat = json.dumps(msg["content"], ensure_ascii=False)
    assert "HƯỚNG DẪN" in flat and "image_url" in flat


def test_tool_result_message_clean_content_unchanged():
    from agent.tool_dispatch_helpers import make_tool_result_message

    clean = '{"output": "ĐÃ AN TOÀN “NÓ” — xong"}'
    assert make_tool_result_message("terminal", clean, "c")["content"] == clean


def test_shell_hook_spawn_round_trips_utf8(tmp_path):
    import sys
    from agent import shell_hooks

    script = tmp_path / "hook.py"
    script.write_text(
        "import sys, json\n"
        "data = json.loads(sys.stdin.read())\n"
        "print(json.dumps({'message': 'HƯỚNG DẪN: ' + data['q']}, ensure_ascii=False))\n",
        encoding="utf-8",
    )
    cmd = f'"{sys.executable}" "{script}"'.replace("\\", "/")
    spec = shell_hooks.ShellHookSpec(event="pre_tool_call", command=cmd, matcher=None)
    res = shell_hooks._spawn(spec, json.dumps({"q": "đệ quy"}, ensure_ascii=False))
    assert res["error"] is None, res
    assert json.loads(res["stdout"])["message"] == "HƯỚNG DẪN: đệ quy"


# Define canonical Vietnamese phrases using \u escapes only
_VIETNAMESE_CLEAN = [
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

def _gen_viet_test_data():
    """Generate (broken, expected) pairs from canonical clean Vietnamese."""


def test_new_viet_dropped_patterns():
    samples = [
        ("Ä\u00f3n", "Đón"),
        ("Ä‘\u00f3n", "đón"),
        ("Ä\u00f4n", "Đôn"),
        ("Ä‘\u00f4n", "đôn"),
        ("Ä\ufffdÆ¡n", "Đơn"),
        ("Ä‘Æ¡n", "đơn"),
        ("Giá»\ufffd", "Giờ"),
        ("giá»\ufffd", "giờ"),
        ("B\u00e1»\ufffd?", "Bỏ"),
        ("b\u00e1»\ufffd?", "bỏ"),
        ("B\u00c3\u00b2", "Bò"),
        ("b\u00c3\u00b2", "bò"),
        ("Ä\u01b0\u00e1\u00bb\ufffdng", "Đường"),
        ("Ä‘\u01b0\u00e1\u00bb\ufffdng", "đường"),
        ("V\u00e1\u00bb\ufffd?", "Về"),
        ("v\u00e1\u00bb\ufffd?", "về"),
        ("H\u00e1\u00bb\ufffd?", "Hỗ"),
        ("h\u00e1\u00bb\ufffd?", "hỗ"),
        ("L\u00e1\u00bb\ufffd?t", "Lót"),
        ("l\u00e1\u00bb\ufffd?t", "lót"),
        ("á»\ufffd?c l\u00e1\u00bb\ufffd?ng", "ốc lỏng"),
        ("Á»\ufffd?c l\u00e1\u00bb\ufffd?ng", "Ốc lỏng"),
        ("S\u00e1\u00bb\ufffd? c\u00e1\u00bb\ufffd?", "Sự cố"),
        ("s\u00e1\u00bb\ufffd? c\u00e1\u00bb\ufffd?", "sự cố"),
    ]
    for broken, expected in samples:
        assert repair_mojibake(broken) == expected

def _gen_viet_test_data():
    """Generate (broken, expected) pairs from canonical clean Vietnamese."""
    return [
        (clean.encode('utf-8').decode('cp1252', 'replace'), clean)
        for clean in _VIETNAMESE_CLEAN
    ]

@pytest.mark.parametrize(('broken', 'expected'), _gen_viet_test_data())
def test_repairs_vietnamese_dropped_cp1252_bytes(broken, expected):
    assert repair_mojibake(broken) == expected
    assert has_mojibake(broken)


@pytest.mark.parametrize(('sample', 'expected', 'is_mojibake'), [
    (u'\u0111\u00e1\u00bb\ufffdu', u'\u0111\u1ec1u', True),
    (u'v\u1ea5n \u0111\u00e1\u00bb\ufffd', u'v\u1ea5n \u0111\u1ec1', True),
    (u'b\u00e1\u00bb\ufffd qua', u'b\u1ecf qua', True),
    (u'ch\u00e1\u00bb\ufffdn l\u00e1\u00bb\ufffdc', u'ch\u1ecdn l\u1ecdc', True),
    (u'm\u00e1\u00bb\ufffdi ng\u01b0\u00e1\u00bb\ufffdi', u'm\u1ecdi ng\u01b0\u1eddi', True),
    (u'h\u1ecdc t\u1eadp', u'h\u1ecdc t\u1eadp', False),
    (u'qu\u1ea3n l\u00fd', u'qu\u1ea3n l\u00fd', False),
    (u'X\u1eed l\u00fd', u'X\u1eed l\u00fd', False),
])
def test_repair_cp1252_replacement_char_loss_regression(sample, expected, is_mojibake):
    assert has_mojibake(sample) == is_mojibake
    assert repair_mojibake(sample) == expected


_VIET_DROPPED_WORD_CASES = [
    ("Trưá»\ufffdng", "Trường"), ("Trưá»ng", "Trường"),
    ("trưá»\ufffdng", "trường"), ("trưá»ng", "trường"),
    ("lưá»\ufffdi", "lười"), ("lưá»i", "lười"),
    ("Đưá»\ufffdc", "Được"), ("Đưá»c", "Được"),
    ("đưá»\ufffdc", "được"), ("đưá»c", "được"),
    ("Điá»\ufffdu", "Điều"), ("Điá»u", "Điều"),
    ("điá»\ufffdu", "điều"), ("điá»u", "điều"),
    ("Tiá»\ufffdn", "Tiền"), ("Tiá»n", "Tiền"),
    ("tiá»\ufffdn", "tiền"), ("tiá»n", "tiền"),
    ("Đá»\ufffdc", "Đọc"), ("Đá»c", "Đọc"),
    ("đá»\ufffdc", "đọc"), ("đá»c", "đọc"),
    ("Thá»\ufffdi", "Thời"), ("Thá»i", "Thời"),
    ("thá»\ufffdi", "thời"), ("thá»i", "thời"),
    ("Lá»\ufffdng", "Lồng"), ("Lá»ng", "Lồng"),
    ("lá»\ufffdng", "lồng"), ("lá»ng", "lồng"),
    ("Ngá»\ufffdng", "Ngóng"), ("Ngá»ng", "Ngóng"),
    ("ngá»\ufffdng", "ngóng"), ("ngá»ng", "ngóng"),
    ("lá»\ufffdi", "lời"), ("lá»i", "lời"),
    ("há»\ufffdi", "hỏi"), ("há»i", "hỏi"),
    ("Đá»\ufffdu", "Đều"), ("Đá»u", "Đều"),
    ("đá»\ufffdu", "đều"), ("đá»u", "đều"),
]


@pytest.mark.parametrize(("broken", "expected"), _VIET_DROPPED_WORD_CASES)
def test_repairs_viet_dropped_phonetic_patterns(broken, expected):
    assert repair_mojibake(broken) == expected


@pytest.mark.parametrize("phrase", [
    "trả lời",
    "chấm hỏi",
    "sự cố",
    "người được điều phối",
])
def test_viet_dropped_patterns_do_not_corrupt_clean_text(phrase):
    assert repair_mojibake(phrase) == phrase
    assert not has_mojibake(phrase)


def test_viet_dropped_phonetic_phrases_in_context():
    assert repair_mojibake("trả lá»i") == "trả lời"
    assert repair_mojibake("chấm há»i") == "chấm hỏi"
    assert repair_mojibake("người lưá»i") == "người lười"
