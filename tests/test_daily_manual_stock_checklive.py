from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

scripts_dir = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import daily_manual_stock_checklive as checklive


def test_main_silent_when_no_changes(capsys):
    """Khi tất cả sản phẩm đều hết hàng từ trước (stock=0, prev_stock=0, sold_yesterday=0), không gửi bot."""
    fake_stock = {
        40: {"name": "TikTok Random Live", "stock": 0, "die_total": 5, "sold_yesterday": 0, "sold_month": 0, "sold_total": 10, "items": []},
        57: {"name": "IG 2FA On Aged 1-30d", "stock": 0, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
        38: {"name": "TikTok US Like New", "stock": 0, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
        39: {"name": "IG New Reg Has Avatar", "stock": 0, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
        60: {"name": "X Search Top 2025", "stock": 0, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
        61: {"name": "Gmail Log ALL có Mail khôi phục", "stock": 0, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
    }
    fake_state = {
        "40": {"stock": 0, "time": "29/09/2026 07:00", "live": 0, "die": 0, "fail": 0, "deleted": 0},
        "57": {"stock": 0, "time": "29/09/2026 07:00", "live": 0, "die": 0, "fail": 0, "deleted": 0},
    }

    with (
        patch.object(checklive, "get_all_up_stock", return_value=fake_stock),
        patch.object(checklive, "load_state", return_value=fake_state),
        patch.object(checklive, "save_state") as mock_save,
        patch.object(checklive, "ensure_cdp_browser"),
        patch.object(checklive, "send_telegram_bot") as mock_bot,
    ):
        ret = checklive.main()
        assert ret == 0
        mock_save.assert_called_once()
        mock_bot.assert_not_called()

    out = capsys.readouterr().out
    assert "im lặng không gửi bot" in out
    assert "[TELEMETRY_METRIC] silent_skip=1" in out


def test_main_reports_when_just_out_of_stock_today(capsys):
    """Khi có sản phẩm vừa hết hàng hôm nay (stock=0 nhưng prev_stock>0), bắt buộc gửi báo cáo 1 lần."""
    fake_stock = {
        40: {"name": "TikTok Random Live", "stock": 0, "die_total": 5, "sold_yesterday": 2, "sold_month": 5, "sold_total": 10, "items": []},
        57: {"name": "IG 2FA On Aged 1-30d", "stock": 0, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
    }
    fake_state = {
        "40": {"stock": 5, "time": "29/09/2026 07:00", "live": 5, "die": 0, "fail": 0, "deleted": 0},
        "57": {"stock": 0, "time": "29/09/2026 07:00", "live": 0, "die": 0, "fail": 0, "deleted": 0},
    }

    with (
        patch.object(checklive, "get_all_up_stock", return_value=fake_stock),
        patch.object(checklive, "load_state", return_value=fake_state),
        patch.object(checklive, "save_state") as mock_save,
        patch.object(checklive, "ensure_cdp_browser"),
        patch.object(checklive, "send_telegram_bot") as mock_bot,
    ):
        ret = checklive.main()
        assert ret == 0
        mock_save.assert_called_once()
        mock_bot.assert_called_once()
        sent_msg = mock_bot.call_args[0][0]
        assert "VỪA HẾT HÀNG hôm nay" in sent_msg
        assert "Đã bán: hôm qua 2" in sent_msg

    out = capsys.readouterr().out
    assert "[TELEMETRY_METRIC] silent_skip=0" in out


def test_main_reports_when_sold_yesterday_even_if_stock_zero(capsys):
    """Khi kho đang = 0 nhưng có phát sinh đơn bán hôm qua, phải gửi báo cáo biến động."""
    fake_stock = {
        40: {"name": "TikTok Random Live", "stock": 0, "die_total": 5, "sold_yesterday": 3, "sold_month": 3, "sold_total": 10, "items": []},
        57: {"name": "IG 2FA On Aged 1-30d", "stock": 0, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
    }
    fake_state = {
        "40": {"stock": 0, "time": "29/09/2026 07:00", "live": 0, "die": 0, "fail": 0, "deleted": 0},
        "57": {"stock": 0, "time": "29/09/2026 07:00", "live": 0, "die": 0, "fail": 0, "deleted": 0},
    }

    with (
        patch.object(checklive, "get_all_up_stock", return_value=fake_stock),
        patch.object(checklive, "load_state", return_value=fake_state),
        patch.object(checklive, "save_state") as mock_save,
        patch.object(checklive, "ensure_cdp_browser"),
        patch.object(checklive, "send_telegram_bot") as mock_bot,
    ):
        ret = checklive.main()
        assert ret == 0
        mock_save.assert_called_once()
        mock_bot.assert_called_once()
        sent_msg = mock_bot.call_args[0][0]
        assert "Đã bán: hôm qua 3" in sent_msg


def test_main_sends_bot_when_stock_present(capsys):
    """Khi có sản phẩm còn hàng tồn kho, gửi báo cáo về bot."""
    fake_stock = {
        40: {"name": "TikTok Random Live", "stock": 10, "die_total": 5, "sold_yesterday": 0, "sold_month": 0, "sold_total": 10, "items": []},
        57: {"name": "IG 2FA On Aged 1-30d", "stock": 0, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
        38: {"name": "TikTok US Like New", "stock": 0, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
        39: {"name": "IG New Reg Has Avatar", "stock": 0, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
        60: {"name": "X Search Top 2025", "stock": 0, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
        61: {"name": "Gmail Log ALL có Mail khôi phục", "stock": 0, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
    }
    fake_state = {
        "40": {"stock": 10, "time": "29/09/2026 07:00", "live": 10, "die": 0, "fail": 0, "deleted": 0},
    }

    with (
        patch.object(checklive, "get_all_up_stock", return_value=fake_stock),
        patch.object(checklive, "load_state", return_value=fake_state),
        patch.object(checklive, "save_state") as mock_save,
        patch.object(checklive, "ensure_cdp_browser"),
        patch.object(checklive, "send_telegram_bot") as mock_bot,
    ):
        ret = checklive.main()
        assert ret == 0
        mock_save.assert_called_once()
        mock_bot.assert_called_once()
        sent_msg = mock_bot.call_args[0][0]
        assert "BÁO CÁO CHECK LIVE KHO UP TAY" in sent_msg
        assert "SP 40 TikTok Random Live" in sent_msg


def test_sp_failure_isolation(capsys):
    """Khi check live của 1 SP bị lỗi mạng/cookie, runner bọc exception cô lập lỗi, không làm sập batch; các SP khác vẫn được cập nhật state."""
    fake_items = [{"id": 1, "uid": "user1", "product_code": "TT", "account": "acc1"}]
    fake_stock = {
        40: {"name": "TikTok Random Live", "stock": 1, "die_total": 0, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": fake_items},
        57: {"name": "IG 2FA On Aged 1-30d", "stock": 2, "die_total": 1, "sold_yesterday": 0, "sold_month": 0, "sold_total": 0, "items": []},
    }
    fake_state = {
        "40": {"stock": 1, "time": "29/09/2026 07:00", "live": 1, "die": 0, "fail": 0, "deleted": 0},
        "57": {"stock": 2, "time": "29/09/2026 07:00", "live": 2, "die": 0, "fail": 0, "deleted": 0},
    }

    def fake_check_tiktok_crash(items):
        raise ConnectionResetError("Mạng chập chờn timeout")

    saved_states = {}
    def fake_save_state(st):
        saved_states.update(st)

    with (
        patch.object(checklive, "get_all_up_stock", return_value=fake_stock),
        patch.object(checklive, "load_state", return_value=fake_state),
        patch.object(checklive, "save_state", side_effect=fake_save_state),
        patch.object(checklive, "ensure_cdp_browser"),
        patch.object(checklive, "check_tiktok", side_effect=fake_check_tiktok_crash),
        patch.object(checklive, "send_telegram_bot") as mock_bot,
    ):
        ret = checklive.main()
        # Vẫn hoàn thành êm đẹp không sập
        assert ret == 0
        mock_bot.assert_called_once()
        # Xác nhận SP 57 vẫn được bảo toàn và cập nhật state đúng
        assert "57" in saved_states
        assert saved_states["57"]["stock"] == 2
        # SP 40 ghi nhận fail nhưng không crash
        assert "40" in saved_states
        assert saved_states["40"]["stock"] == 1

    out = capsys.readouterr().out
    assert "LỖI checklive SP 40" in out
