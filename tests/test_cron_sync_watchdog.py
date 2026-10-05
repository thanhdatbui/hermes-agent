"""Unit tests for the cron sync watchdog."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "deploy"
    / "hermes-home"
    / "scripts"
    / "cron_sync_watchdog.py"
)

_spec = importlib.util.spec_from_file_location("cron_sync_watchdog", SCRIPT_PATH)
if _spec is None or _spec.loader is None:  # pragma: no cover - collection guard
    raise ImportError(f"Unable to load {SCRIPT_PATH}")
cron_sync_watchdog = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cron_sync_watchdog)


def _set_mtime(path: Path, mtime: float) -> None:
    os.utime(path, (mtime, mtime))


def test_sync_file_copied_when_dst_missing(tmp_path: Path) -> None:
    src = tmp_path / "src.py"
    dst = tmp_path / "nested" / "dst.py"
    src.write_text("source", encoding="utf-8")

    assert cron_sync_watchdog.sync_file(src, dst) == "copied"
    assert dst.read_text(encoding="utf-8") == "source"


def test_sync_file_skipped_when_same_content(tmp_path: Path) -> None:
    src = tmp_path / "src.py"
    dst = tmp_path / "dst.py"
    src.write_text("same content", encoding="utf-8")
    dst.write_text("same content", encoding="utf-8")
    dst_mtime = dst.stat().st_mtime

    assert cron_sync_watchdog.sync_file(src, dst) == "skipped"
    assert dst.stat().st_mtime == dst_mtime


def test_sync_file_copied_when_src_newer(tmp_path: Path) -> None:
    src = tmp_path / "src.py"
    dst = tmp_path / "dst.py"
    src.write_text("new source", encoding="utf-8")
    dst.write_text("old destination", encoding="utf-8")
    now = 1_700_000_000.0
    _set_mtime(dst, now)
    _set_mtime(src, now + cron_sync_watchdog.MTIME_TOLERANCE_S + 1)

    assert cron_sync_watchdog.sync_file(src, dst) == "copied"
    assert dst.read_text(encoding="utf-8") == "new source"


def test_sync_file_skipped_when_dst_newer(tmp_path: Path) -> None:
    src = tmp_path / "src.py"
    dst = tmp_path / "dst.py"
    src.write_text("old source", encoding="utf-8")
    dst.write_text("new destination", encoding="utf-8")
    now = 1_700_000_000.0
    _set_mtime(src, now)
    _set_mtime(dst, now + cron_sync_watchdog.MTIME_TOLERANCE_S + 1)

    assert cron_sync_watchdog.sync_file(src, dst) == "skipped"
    assert dst.read_text(encoding="utf-8") == "new destination"


def test_sync_file_conflict_when_same_mtime(tmp_path: Path) -> None:
    src = tmp_path / "src.py"
    dst = tmp_path / "dst.py"
    src.write_text("source version", encoding="utf-8")
    dst.write_text("destination version", encoding="utf-8")
    mtime = 1_700_000_000.0
    _set_mtime(src, mtime)
    _set_mtime(dst, mtime)

    assert cron_sync_watchdog.sync_file(src, dst) == "conflict"
    assert dst.read_text(encoding="utf-8") == "destination version"


def test_sync_file_force_creates_backup_and_copies(tmp_path: Path) -> None:
    src = tmp_path / "src.py"
    dst = tmp_path / "dst.py"
    src.write_text("forced source", encoding="utf-8")
    dst.write_text("previous destination", encoding="utf-8")
    mtime = 1_700_000_000.0
    _set_mtime(src, mtime)
    _set_mtime(dst, mtime)

    assert cron_sync_watchdog.sync_file(src, dst, force=True) == "copied"
    assert dst.read_text(encoding="utf-8") == "forced source"
    backups = list(tmp_path.glob("dst.py.conflict-*.bak"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "previous destination"


def test_sync_jobs_updates_destinations(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "runtime" / "jobs.json"
    deploy = tmp_path / "deploy" / "jobs.json"
    onedrive = tmp_path / "onedrive" / "jobs.json"
    src.parent.mkdir()
    src.write_text('{"jobs": ["example"]}', encoding="utf-8")
    monkeypatch.setattr(cron_sync_watchdog, "KIBE_JOBS", src)
    monkeypatch.setattr(cron_sync_watchdog, "DEPLOY_JOBS", deploy)
    monkeypatch.setattr(cron_sync_watchdog, "ONEDRIVE_JOBS", onedrive)

    assert cron_sync_watchdog.sync_jobs() is True
    assert deploy.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")
    assert onedrive.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")
    assert cron_sync_watchdog.sync_jobs() is False


def test_sync_scripts_traverses_and_syncs(tmp_path: Path, monkeypatch) -> None:
    kibe = tmp_path / "kibe-scripts"
    deploy = tmp_path / "deploy-scripts"
    onedrive = tmp_path / "onedrive-scripts"
    kibe.mkdir()
    deploy.mkdir()
    onedrive.mkdir()
    monkeypatch.setattr(cron_sync_watchdog, "KIBE_SCRIPTS", kibe)
    monkeypatch.setattr(cron_sync_watchdog, "DEPLOY_SCRIPTS", deploy)
    monkeypatch.setattr(cron_sync_watchdog, "ONEDRIVE_SCRIPTS", onedrive)

    (deploy / "from_deploy.py").write_text("deploy", encoding="utf-8")
    (deploy / "ignored.txt").write_text("ignored", encoding="utf-8")
    assert cron_sync_watchdog.sync_scripts() == 2
    assert (kibe / "from_deploy.py").read_text(encoding="utf-8") == "deploy"
    assert (onedrive / "from_deploy.py").read_text(encoding="utf-8") == "deploy"
    assert not (kibe / "ignored.txt").exists()

    runtime = kibe / "from_runtime.py"
    runtime.write_text("runtime", encoding="utf-8")
    assert cron_sync_watchdog.sync_scripts() == 2
    assert (deploy / "from_runtime.py").read_text(encoding="utf-8") == "runtime"
    assert (onedrive / "from_runtime.py").read_text(encoding="utf-8") == "runtime"
