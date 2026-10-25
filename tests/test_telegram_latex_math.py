import sys
import pytest

def test_telegram_format_message_latex_cleaning():
    from plugins.platforms.telegram.adapter import TelegramAdapter
    t = TelegramAdapter.__new__(TelegramAdapter)
    sample = r"""$$\begin{aligned}
\text{User Request} &\xrightarrow{\text{Gate 1-5 \& Plugin Pre-Tool}} \text{Coordinator Lập Contract} \\
&\xrightarrow{\text{Gate 4 \& Dispatch Hook}} \text{Worker Thi Công (hoặc L2 Emergency Surgery)} \\
&\xrightarrow{\text{Gate A-C \& Pyright/Diff Guard}} \text{Acceptance Test Focus < 30s} \\
&\xrightarrow{\text{Gate 6 \& Vision Hook}} \text{Soi Mắt Ảnh Thực Tế (MEDIA:)} \\
&\xrightarrow{\text{Closeout Gate (Sol/Claude)}} \text{Chấm Điểm } \ge 85 \text{ (Cấp HMAC Token)} \\
&\xrightarrow{\text{Git Pre-Push Hook}} \text{Đối Soát SHA \& Push Git An Toàn}
\end{aligned}$$"""
    res = t.format_message(sample)
    assert r"\begin" not in res
    assert r"\end" not in res
    assert r"\text" not in res
    assert r"\xrightarrow" not in res
    assert r"──\[" in res
    assert "Gate 1" in res
    assert "≥ 85" in res
    assert "Plugin Pre" in res
