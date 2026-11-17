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
    from plugins.platforms.telegram.adapter import TelegramAdapter
    moji = "Lỗi".encode("utf-8").decode("cp1252")
    assert TelegramAdapter._sanitize_outgoing_text(moji) == "Lỗi"
    assert TelegramAdapter._sanitize_outgoing_text("") == ""
    assert TelegramAdapter._sanitize_outgoing_text(None) is None


def test_repairs_repr_escaped_continuation_bytes():
    assert repair_mojibake("tháº\xadt sự") == "thật sự"
    assert repair_mojibake("lÃ\\xa0 không") == "là không"
    # A lone escape not preceded by a lead char is left alone.
    assert repair_mojibake("bytes \xad here") == "bytes \xad here"


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
