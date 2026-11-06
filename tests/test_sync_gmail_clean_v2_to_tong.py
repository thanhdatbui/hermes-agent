import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "deploy" / "hermes-home" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import sync_gmail_clean_v2_to_tong as syncer


def test_sync_reads_from_farm_master_db(tmp_path, monkeypatch):
    db_file = tmp_path / "farm_master.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE mailboxes (email TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO mailboxes VALUES ('test1@gmail.com')")
    conn.execute("INSERT INTO mailboxes VALUES ('test2@gmail.com')")
    conn.commit()
    conn.close()

    live_file = tmp_path / "gmail_live_tong.txt"
    hash_cache = tmp_path / "hash.txt"

    monkeypatch.setattr(syncer, "FARM_MASTER_DB", str(db_file))
    monkeypatch.setattr(syncer, "LIVE_FILE", str(live_file))
    monkeypatch.setattr(syncer, "HASH_CACHE", str(hash_cache))

    rc = syncer.sync(force=True)
    assert rc == 0
    assert live_file.exists()

    content = live_file.read_text(encoding="utf-8").splitlines()
    assert "test1@gmail.com" in content
    assert "test2@gmail.com" in content


def test_sync_fallback_to_excel(tmp_path, monkeypatch):
    import openpyxl

    excel_file = tmp_path / "gmail_clean_v2.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["STT", "Email"])
    ws.append([1, "fallback@gmail.com"])
    wb.save(excel_file)
    wb.close()

    live_file = tmp_path / "gmail_live_tong.txt"
    hash_cache = tmp_path / "hash.txt"

    monkeypatch.setattr(syncer, "FARM_MASTER_DB", str(tmp_path / "nonexistent.db"))
    monkeypatch.setattr(syncer, "GMAIL_CLEAN_V2", str(excel_file))
    monkeypatch.setattr(syncer, "LIVE_FILE", str(live_file))
    monkeypatch.setattr(syncer, "HASH_CACHE", str(hash_cache))

    rc = syncer.sync(force=True)
    assert rc == 0
    assert live_file.exists()

    content = live_file.read_text(encoding="utf-8").splitlines()
    assert "fallback@gmail.com" in content
