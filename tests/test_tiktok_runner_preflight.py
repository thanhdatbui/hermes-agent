from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import tiktok_runner  # noqa: E402

_original_is_file = Path.is_file


def _mock_is_file(self: Path) -> bool:
    if "ensure_row_accounts" in str(self):
        return True
    return _original_is_file(self)


def test_preflight_kibe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_file", _mock_is_file)
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    monkeypatch.setattr(tiktok_runner.subprocess, "run", mock_run)

    state_file = tmp_path / "runner.json"
    cluster = {
        "name": "kibe",
        "state_file": state_file,
        "host_config": "kibe.yaml",
    }
    window_key = "2026-09-24_10"

    tiktok_runner._preflight_ensure_accounts(row=3, window_key=window_key, cluster=cluster)

    marker = tmp_path / f".preflight_kibe_{window_key}"
    assert marker.exists()
    data = json.loads(marker.read_text(encoding="utf-8"))
    assert data["status"] == "success"
    assert data["cluster"] == "kibe"
    assert mock_run.called
    args, kwargs = mock_run.call_args
    assert kwargs.get("env") is not None
    assert kwargs["env"].get("TAADAA_HOST_CONFIG") == "kibe.yaml"


def test_preflight_admin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_file", _mock_is_file)
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    monkeypatch.setattr(tiktok_runner.subprocess, "run", mock_run)

    state_file = tmp_path / "runner.json"
    cluster = {
        "name": "admin",
        "state_file": state_file,
        "host_config": "admin.yaml",
        "adb_server_socket": "tcp:192.168.110.119:5037",
    }
    window_key = "2026-09-24_11"

    tiktok_runner._preflight_ensure_accounts(row=5, window_key=window_key, cluster=cluster)

    marker = tmp_path / f".preflight_admin_{window_key}"
    assert marker.exists()
    data = json.loads(marker.read_text(encoding="utf-8"))
    assert data["status"] == "success"
    assert data["cluster"] == "admin"
    assert mock_run.called
    args, kwargs = mock_run.call_args
    assert kwargs.get("env") is not None
    assert kwargs["env"].get("TAADAA_HOST_CONFIG") == "admin.yaml"
    assert kwargs["env"].get("ADB_SERVER_SOCKET") == "tcp:192.168.110.119:5037"


def test_preflight_marker_exists_skips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_file", _mock_is_file)
    mock_run = MagicMock()
    monkeypatch.setattr(tiktok_runner.subprocess, "run", mock_run)

    state_file = tmp_path / "runner.json"
    cluster = {
        "name": "kibe",
        "state_file": state_file,
        "host_config": "kibe.yaml",
    }
    window_key = "2026-09-24_12"

    marker = tmp_path / f".preflight_kibe_{window_key}"
    marker.write_text("existing", encoding="utf-8")

    tiktok_runner._preflight_ensure_accounts(row=3, window_key=window_key, cluster=cluster)

    assert not mock_run.called
    assert marker.read_text(encoding="utf-8") == "existing"


def test_preflight_failure_unlinks_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_file", _mock_is_file)
    mock_run = MagicMock()
    mock_run.return_value.returncode = 1
    monkeypatch.setattr(tiktok_runner.subprocess, "run", mock_run)

    state_file = tmp_path / "runner.json"
    cluster = {
        "name": "admin",
        "state_file": state_file,
        "host_config": "admin.yaml",
    }
    window_key = "2026-09-24_13"

    tiktok_runner._preflight_ensure_accounts(row=5, window_key=window_key, cluster=cluster)

    marker = tmp_path / f".preflight_admin_{window_key}"
    assert not marker.exists()


def test_determine_row_4day_cycle() -> None:
    from datetime import datetime
    dt_m = datetime(2026, 10, 11, 8, 0, tzinfo=tiktok_runner.HCMC)
    res_m = tiktok_runner._determine_row(dt_m)
    assert res_m is not None and res_m[0] == 1 and not res_m[3]

    dt_d1 = datetime(2026, 10, 12, 12, 0, tzinfo=tiktok_runner.HCMC)
    res_d1 = tiktok_runner._determine_row(dt_d1)
    assert res_d1 is not None and res_d1[0] == 4 and not res_d1[3]

    dt_d2 = datetime(2026, 10, 13, 18, 0, tzinfo=tiktok_runner.HCMC)
    res_d2 = tiktok_runner._determine_row(dt_d2)
    assert res_d2 is not None and res_d2[3] is True and 1 <= res_d2[0] <= 8

    dt_d3 = datetime(2026, 10, 14, 8, 0, tzinfo=tiktok_runner.HCMC)
    res_d3 = tiktok_runner._determine_row(dt_d3)
    assert res_d3 is not None and res_d3[3] is True


def test_row_nurture_summary_starvation_and_formatting(tmp_path: Path) -> None:
    from feed_session_watchdog import get_row_nurture_summary
    summary, starved = get_row_nurture_summary(live_root=str(tmp_path), threshold_h=96.0)
    assert len(starved) == 8
    assert "R1:🔴--" in summary


def test_preflight_subprocess_exception_unlinks_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_file", _mock_is_file)
    mock_run = MagicMock(side_effect=RuntimeError("Subprocess boom"))
    monkeypatch.setattr(tiktok_runner.subprocess, "run", mock_run)
    state_file = tmp_path / "runner.json"
    cluster = {"name": "kibe", "state_file": state_file, "host_config": "kibe.yaml"}
    window_key = "2026-09-24_15"
    try:
        tiktok_runner._preflight_ensure_accounts(row=4, window_key=window_key, cluster=cluster)
    except RuntimeError:
        pass
    marker = tmp_path / f".preflight_kibe_{window_key}"
    assert not marker.exists()


# ---------------------------------------------------------------------------
# Lịch ca (schedule) - phủ toàn bộ slot x chu kỳ 4 ngày
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta  # noqa: E402

_BASE_DAY = datetime(2026, 10, 11, tzinfo=tiktok_runner.HCMC)

# (cycle_day, hour) -> (row, is_rest_day) trong chu kỳ đầu (cycle_idx chẵn)
_EXPECTED_CYCLE_0 = {
    (0, 6): (1, False), (0, 8): (1, False), (0, 12): (3, False), (0, 14): (3, False), (0, 18): (5, False), (0, 20): (5, False),
    (1, 6): (2, False), (1, 8): (2, False), (1, 12): (4, False), (1, 14): (4, False), (1, 18): (6, False), (1, 20): (6, False),
    (2, 6): (7, False), (2, 8): (7, False), (2, 12): (8, False), (2, 14): (8, False), (2, 18): (3, True), (2, 20): (3, True),
    (3, 6): (3, True), (3, 8): (3, True), (3, 12): (4, True), (3, 14): (4, True), (3, 18): (5, True), (3, 20): (5, True),
}


@pytest.mark.parametrize("cycle_day,hour", sorted(_EXPECTED_CYCLE_0))
def test_determine_row_full_schedule_first_cycle(cycle_day: int, hour: int) -> None:
    now = (_BASE_DAY + timedelta(days=cycle_day)).replace(hour=hour)
    res = tiktok_runner._determine_row(now)
    assert res is not None
    row, session_index, window_key, is_rest = res
    expected_row, expected_rest = _EXPECTED_CYCLE_0[(cycle_day, hour)]
    if expected_rest:
        assert is_rest is True and 1 <= row <= 8
    else:
        assert (row, is_rest) == (expected_row, expected_rest)
    assert session_index == (2 if hour in (8, 14, 20) else 1)
    assert window_key == f"{now.date().isoformat()}T{hour:02d}"


def test_determine_row_second_cycle_alternates_healing_rows() -> None:
    day2 = tiktok_runner._determine_row((_BASE_DAY + timedelta(days=6)).replace(hour=18))
    assert day2[3] is True and 1 <= day2[0] <= 8
    day3 = tiktok_runner._determine_row((_BASE_DAY + timedelta(days=7)).replace(hour=20))
    assert day3[3] is True and 1 <= day3[0] <= 8
    # parity cố định: mọi chu kỳ Day 0 = Row 1 lúc 6h, Day 1 = Row 2 lúc 6h
    day0 = tiktok_runner._determine_row((_BASE_DAY + timedelta(days=4)).replace(hour=6))
    assert (day0[0], day0[3]) == (1, False)
    day1 = tiktok_runner._determine_row((_BASE_DAY + timedelta(days=5)).replace(hour=6))
    assert (day1[0], day1[3]) == (2, False)


@pytest.mark.parametrize("hour", [6, 8, 12, 14, 18, 20])
def test_determine_row_main_rows_recur_exactly_every_96h(hour: int, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tiktok_runner, "_load_determine_healing_row", lambda: (lambda *a, **k: 3, Path(".")))
    # Mỗi row chính (1-8) quay lại đúng 96h ở mọi chu kỳ, không phụ thuộc cycle_idx.
    seen: dict[int, list[datetime]] = {}
    for day in range(0, 4 * 12):
        now = (_BASE_DAY + timedelta(days=day)).replace(hour=hour)
        res = tiktok_runner._determine_row(now)
        assert res is not None
        row, _, _, is_rest = res
        if not is_rest:
            seen.setdefault(row, []).append(now)
    assert seen
    for row, times in seen.items():
        gaps = {(b - a) for a, b in zip(times, times[1:])}
        assert gaps == {timedelta(hours=96)}, (row, gaps)


@pytest.mark.parametrize(
    "hour,minute",
    [(0, 0), (1, 30), (3, 0), (5, 59), (7, 0), (10, 0), (16, 0), (21, 30), (22, 0), (23, 59)],
)
def test_determine_row_dead_zone_and_unmapped_hours(hour: int, minute: int) -> None:
    assert tiktok_runner._determine_row(_BASE_DAY.replace(hour=hour, minute=minute)) is None


def test_determine_row_late_cron_within_window_still_maps() -> None:
    res = tiktok_runner._determine_row(_BASE_DAY.replace(hour=8, minute=40))
    assert res is not None and res[0] == 1 and res[2].endswith("T08")


# ---------------------------------------------------------------------------
# _count_valid_accounts_for_row
# ---------------------------------------------------------------------------

def _make_workbook(path: Path, rows: list[tuple]) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["machine", "x", "account"])
    for r in rows:
        ws.append(list(r))
    wb.save(path)


def test_count_valid_accounts_counts_machines_with_account_in_row(tmp_path: Path) -> None:
    wb = tmp_path / "safe.xlsx"
    _make_workbook(wb, [
        (1, None, "alice"), (1, None, "none"),
        (2, None, None), (2, None, "bob"),
        (3, None, "  "), (3, None, "carol"),
        ("abc", None, "ignored"),
    ])
    assert tiktok_runner._count_valid_accounts_for_row(1, workbook_path=str(wb)) == 1
    assert tiktok_runner._count_valid_accounts_for_row(2, workbook_path=str(wb)) == 2
    assert tiktok_runner._count_valid_accounts_for_row(8, workbook_path=str(wb)) == 0


def test_count_valid_accounts_missing_workbook_returns_zero(tmp_path: Path) -> None:
    assert tiktok_runner._count_valid_accounts_for_row(1, workbook_path=str(tmp_path / "nope.xlsx")) == 0


def test_count_valid_accounts_corrupt_workbook_retries_then_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    wb = tmp_path / "corrupt.xlsx"
    wb.write_text("not a zip", encoding="utf-8")
    assert tiktok_runner._count_valid_accounts_for_row(1, workbook_path=str(wb)) == 0
    assert len(sleeps) == 2


# ---------------------------------------------------------------------------
# _spawn_feed_session
# ---------------------------------------------------------------------------

@pytest.fixture
def spawn_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "run-feed-session.ps1").write_text("", encoding="utf-8")
    monkeypatch.setattr(tiktok_runner, "repo_root", lambda: repo)
    monkeypatch.setattr(tiktok_runner, "target_python", lambda: "python.exe")
    monkeypatch.setattr(tiktok_runner.subprocess, "run", MagicMock())
    popen = MagicMock()
    popen.return_value.pid = 4242
    monkeypatch.setattr(tiktok_runner.subprocess, "Popen", popen)
    monkeypatch.delenv("TAADAA_REST_DAY_NO_FOLLOW", raising=False)
    monkeypatch.delenv("ADB_SERVER_SOCKET", raising=False)
    return popen


def test_spawn_feed_session_admin_cluster_env_and_args(tmp_path: Path, spawn_env: MagicMock) -> None:
    now = _BASE_DAY.replace(hour=8)
    rc = tiktok_runner._spawn_feed_session(
        2, 2, now, is_rest_day=False, account_workbook="D:/wb/admin.xlsx", artifact_base=tmp_path / "live",
        host_config="admin.yaml", adb_server_socket="tcp:192.168.110.119:5037",
    )
    assert rc == 0
    argv, kwargs = spawn_env.call_args[0][0], spawn_env.call_args[1]
    assert argv[argv.index("-Row") + 1] == "2"
    assert argv[argv.index("-SessionIndex") + 1] == "2"
    assert "-AllowUploadHook" in argv
    assert argv[argv.index("-AccountWorkbook") + 1] == "D:\\wb\\admin.xlsx"
    assert "row-2-080000" in argv[argv.index("-ArtifactRoot") + 1]
    env = kwargs["env"]
    assert env["TAADAA_HOST_CONFIG"] == "admin.yaml"
    assert env["ADB_SERVER_SOCKET"] == "tcp:192.168.110.119:5037"
    assert "TAADAA_REST_DAY_NO_FOLLOW" not in env


def test_spawn_feed_session_kibe_rest_day_sets_no_follow_and_drops_socket(
    tmp_path: Path, spawn_env: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADB_SERVER_SOCKET", "tcp:stale:5037")
    rc = tiktok_runner._spawn_feed_session(
        3, 1, _BASE_DAY.replace(hour=6), is_rest_day=True, artifact_base=tmp_path / "live", host_config="kibe.yaml",
    )
    assert rc == 0
    argv, env = spawn_env.call_args[0][0], spawn_env.call_args[1]["env"]
    assert "-AllowUploadHook" in argv
    assert env["TAADAA_REST_DAY_NO_FOLLOW"] == "1"
    assert "ADB_SERVER_SOCKET" not in env
    assert env["TAADAA_HOST_CONFIG"] == "kibe.yaml"


def test_spawn_feed_session_missing_ps1_returns_3(tmp_path: Path, spawn_env: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    empty_repo = tmp_path / "empty"
    empty_repo.mkdir()
    monkeypatch.setattr(tiktok_runner, "repo_root", lambda: empty_repo)
    assert tiktok_runner._spawn_feed_session(1, 1, _BASE_DAY.replace(hour=6), artifact_base=tmp_path) == 3
    assert not spawn_env.called


# ---------------------------------------------------------------------------
# main(): dual-cluster execution
# ---------------------------------------------------------------------------

@pytest.fixture
def dual_clusters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    clusters = []
    for name, sock in (("kibe", None), ("admin", "tcp:192.168.110.119:5037")):
        clusters.append({
            "name": name,
            "account_workbook": str(tmp_path / f"{name}.xlsx"),
            "state_file": tmp_path / name / "cron-state" / "runner_simple_state.json",
            "artifact_base": tmp_path / name / "live",
            "host_config": f"{name}.yaml",
            "adb_server_socket": sock,
        })
    monkeypatch.setattr(tiktok_runner, "CLUSTERS", clusters)
    monkeypatch.setenv(tiktok_runner.ACTIVATION_ENV, "1")
    monkeypatch.setenv(tiktok_runner.NOW_ENV, "2026-10-11T06:05:00")
    monkeypatch.setattr(tiktok_runner, "merged_env", lambda env: dict(env))
    preflight, count, spawn = MagicMock(), MagicMock(return_value=5), MagicMock(return_value=0)
    monkeypatch.setattr(tiktok_runner, "_preflight_ensure_accounts", preflight)
    monkeypatch.setattr(tiktok_runner, "_count_valid_accounts_for_row", count)
    monkeypatch.setattr(tiktok_runner, "_spawn_feed_session", spawn)
    return clusters, preflight, count, spawn


def test_main_runs_both_clusters_and_saves_state(dual_clusters) -> None:
    clusters, preflight, count, spawn = dual_clusters
    assert tiktok_runner.main([]) == 0
    assert [c.kwargs["cluster"]["name"] for c in preflight.call_args_list] == ["kibe", "admin"]
    assert spawn.call_count == 2
    kibe_kw, admin_kw = spawn.call_args_list[0].kwargs, spawn.call_args_list[1].kwargs
    assert kibe_kw["host_config"] == "kibe.yaml" and kibe_kw["adb_server_socket"] is None
    assert admin_kw["host_config"] == "admin.yaml" and admin_kw["adb_server_socket"] == "tcp:192.168.110.119:5037"
    assert spawn.call_args_list[0].args[:2] == (1, 1)
    for c in clusters:
        state = json.loads(c["state_file"].read_text(encoding="utf-8"))
        assert state["last_row"] == 1 and state["last_window"] == "2026-10-11T06"


def test_main_second_tick_is_deduplicated(dual_clusters) -> None:
    _, _, _, spawn = dual_clusters
    tiktok_runner.main([])
    spawn.reset_mock()
    assert tiktok_runner.main([]) == 0
    assert not spawn.called


def test_main_cluster_without_accounts_skipped_without_saving_state(dual_clusters) -> None:
    clusters, _, count, spawn = dual_clusters
    count.side_effect = lambda row, workbook_path: 0 if workbook_path.endswith("admin.xlsx") else 3
    assert tiktok_runner.main([]) == 0
    assert spawn.call_count == 1
    assert clusters[0]["state_file"].is_file()
    assert not clusters[1]["state_file"].exists()


def test_main_spawn_failure_in_one_cluster_does_not_block_other(dual_clusters) -> None:
    clusters, _, _, spawn = dual_clusters
    spawn.side_effect = [3, 0]
    assert tiktok_runner.main([]) == 3
    assert spawn.call_count == 2
    assert not clusters[0]["state_file"].exists()
    assert clusters[1]["state_file"].is_file()


def test_main_rest_day_passes_flag_to_every_cluster(dual_clusters, monkeypatch: pytest.MonkeyPatch) -> None:
    _, _, _, spawn = dual_clusters
    monkeypatch.setenv(tiktok_runner.NOW_ENV, "2026-10-14T08:00:00")
    assert tiktok_runner.main([]) == 0
    assert [c.kwargs["is_rest_day"] for c in spawn.call_args_list] == [True, True]


def test_main_inactive_dead_zone_and_args(dual_clusters, monkeypatch: pytest.MonkeyPatch) -> None:
    _, _, _, spawn = dual_clusters
    assert tiktok_runner.main(["--x"]) == 2
    monkeypatch.setenv(tiktok_runner.NOW_ENV, "2026-10-11T23:00:00")
    assert tiktok_runner.main([]) == 0
    monkeypatch.setenv(tiktok_runner.NOW_ENV, "2026-10-11T06:05:00")
    monkeypatch.setenv(tiktok_runner.ACTIVATION_ENV, "0")
    monkeypatch.setattr(tiktok_runner, "_default_permit_file", lambda: Path("/nonexistent/permit"))
    assert tiktok_runner.main([]) == 0
    assert not spawn.called


# ---------------------------------------------------------------------------
# feed_session_watchdog: sức khỏe nuôi 8 row + xử lý workbook lỗi
# ---------------------------------------------------------------------------

def _mk_run(live: Path, row: int, hours_ago: float) -> None:
    import feed_session_watchdog as w

    dt = datetime.now(w.HCMC) - timedelta(hours=hours_ago)
    (live / dt.strftime("%Y-%m-%d") / f"row-{row}-{dt.strftime('%H%M')}00").mkdir(parents=True, exist_ok=True)


def test_row_nurture_summary_health_levels(tmp_path: Path) -> None:
    from feed_session_watchdog import get_row_nurture_summary

    from feed_session_watchdog import NURTURE_CYCLE_H, STARVATION_THRESHOLD_H

    assert (NURTURE_CYCLE_H, STARVATION_THRESHOLD_H) == (96.0, 108.0)
    _mk_run(tmp_path, 1, 1)
    _mk_run(tmp_path, 2, 100)  # quá chu kỳ 96h nhưng còn trong dung sai
    _mk_run(tmp_path, 3, 120)  # quá ngưỡng bỏ đói
    _mk_run(tmp_path, 4, 95)  # sát cuối chu kỳ vẫn xanh
    for r in range(5, 9):
        _mk_run(tmp_path, r, 10)
    summary, starved = get_row_nurture_summary(live_root=str(tmp_path))
    assert starved == [3]
    parts = summary.split(" | ")
    assert len(parts) == 8
    assert parts[0].startswith("R1:🟢") and parts[1].startswith("R2:🟡") and parts[2].startswith("R3:🔴")
    assert parts[3].startswith("R4:🟢")


def test_row_nurture_summary_uses_latest_run_and_ignores_junk(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    from feed_session_watchdog import get_row_nurture_summary

    _mk_run(tmp_path, 1, 200)
    _mk_run(tmp_path, 1, 2)
    (tmp_path / "notes").mkdir()
    (tmp_path / "2026-99-99-extra").mkdir()
    bad_day = tmp_path / "2026-10-01"
    (bad_day / "row-2-9999").mkdir(parents=True)
    (bad_day / "row-9-0600").mkdir()
    with caplog.at_level("WARNING", logger="feed_session_watchdog"):
        summary, starved = get_row_nurture_summary(live_root=str(tmp_path), threshold_h=96.0)
    assert 1 not in starved
    assert 2 in starved and 9 not in starved
    assert any("row-2-9999" in rec.getMessage() for rec in caplog.records)
    assert summary.startswith("R1:🟢")


def test_row_nurture_summary_missing_live_root(tmp_path: Path) -> None:
    from feed_session_watchdog import get_row_nurture_summary

    summary, starved = get_row_nurture_summary(live_root=str(tmp_path / "absent"), threshold_h=96.0)
    assert starved == list(range(1, 9))
    assert summary.count("🔴--") == 8


def test_reconcile_following_missing_workbook_returns_empty(tmp_path: Path) -> None:
    from feed_session_watchdog import reconcile_cluster_following

    assert reconcile_cluster_following({"account_workbook": str(tmp_path / "absent.xlsx")}, ["1"], {}, 1) == []
    assert reconcile_cluster_following({}, ["1"], {}, 1) == []


def test_reconcile_following_corrupt_workbook_reports_and_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import feed_session_watchdog as w

    monkeypatch.setattr(w.time, "sleep", lambda s: None)
    wb = tmp_path / "corrupt.xlsx"
    wb.write_text("not a zip", encoding="utf-8")
    with caplog.at_level("WARNING", logger="feed_session_watchdog"):
        out = w.reconcile_cluster_following({"account_workbook": str(wb)}, ["1"], {"1": {"followed": ["a"]}}, 1)
    assert len(out) == 1 and "Không đọc được workbook" in out[0]
    assert sum("workbook hỏng" in rec.getMessage() for rec in caplog.records) == 1


def test_reconcile_following_no_username_in_workbook_reports(tmp_path: Path) -> None:
    import feed_session_watchdog as w

    wb = tmp_path / "wb.xlsx"
    _make_workbook(wb, [(2, None, "someone")])
    out = w.reconcile_cluster_following({"account_workbook": str(wb)}, ["1"], {"1": {"followed": ["a"]}}, 1)
    assert out == ["  + Đối soát TikTok Web: Không tìm thấy username trong workbook cho 1 máy follow"]


def test_dispatch_split_reports_one_chat_failure_does_not_block_other(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import types
    import urllib.request

    import feed_session_watchdog as w

    alerts = types.ModuleType("automation_core.alerts")
    alerts._load_bot_token = lambda: "TOKEN"
    pkg = types.ModuleType("automation_core")
    pkg.alerts = alerts
    monkeypatch.setitem(sys.modules, "automation_core", pkg)
    monkeypatch.setitem(sys.modules, "automation_core.alerts", alerts)
    monkeypatch.setattr(w.time, "sleep", lambda s: None)
    sent: list[str] = []

    def fake_urlopen(req, timeout=0):
        if "5435853713" in req.data.decode():
            raise OSError("boom")
        sent.append(req.data.decode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    block = "🏢 Cụm kibe\n• Tổng máy: 3\n• Lướt feed: 3\n• Follow chéo: 3\n  + ok\n• Đăng Video: 3\n  + ok"
    with caplog.at_level("WARNING", logger="feed_session_watchdog"):
        msg = w.dispatch_split_reports("hdr", [block], [], "Ca 1", 1)
    assert sent == []
    assert any("DISPATCH_FAIL" in rec.getMessage() for rec in caplog.records)
    assert "Follow chéo" not in msg and "Đăng Video" not in msg
