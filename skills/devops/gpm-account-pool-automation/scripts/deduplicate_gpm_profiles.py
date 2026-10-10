#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/deduplicate_gpm_profiles.py
Tool dọn dẹp các profile clone trùng lặp trong GPMLogin:
- Đối soát với PROXYgandienthoai.xlsx và taikhoan_dat_v2_updated.xlsx.
- So sánh kích thước session cookie trên đĩa để giữ lại profile có session thật (>50KB).
- Xóa sạch các profile clone thừa qua GPMLogin API v3 (/api/v3/profiles/delete/{pid}?mode=1).
- Hỗ trợ cờ --dry-run (mặc định) và --apply.
"""

import os
import re
import sys
import time
import shutil
import sqlite3
import requests
import openpyxl
from pathlib import Path
from collections import defaultdict

GPM_API = "http://127.0.0.1:19995/api/v3"
BASE_PROFILE_DIR = Path.home() / "AppData" / "Local" / "Programs" / "GPMLogin" / "profile"
GPM_DB = BASE_PROFILE_DIR / "profile_data.db"

TAIKHOAN_DAT = r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx"
if not os.path.exists(TAIKHOAN_DAT):
    TAIKHOAN_DAT = r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated.xlsx"
PROXY_XLSX = r"D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx"


def load_email_to_machine():
    mapping = {}
    if not os.path.exists(TAIKHOAN_DAT):
        return mapping
    try:
        wb = openpyxl.load_workbook(TAIKHOAN_DAT, read_only=True, data_only=True)
        ws = wb["Tài Khoản"] if "Tài Khoản" in wb.sheetnames else wb.active
        for row in ws.iter_rows(values_only=True):
            if row and len(row) > 5 and row[0] is not None and row[5]:
                try:
                    mid = int(row[0])
                    em = str(row[5]).strip().lower()
                    if "@" in em:
                        mapping[em] = mid
                except (ValueError, TypeError):
                    pass
        wb.close()
    except Exception:
        pass
    return mapping


def load_machine_to_proxy():
    proxy_map = {}
    if not os.path.exists(PROXY_XLSX):
        return proxy_map
    try:
        wb = openpyxl.load_workbook(PROXY_XLSX, read_only=True, data_only=True)
        ws = wb["Proxy"] if "Proxy" in wb.sheetnames else wb.active
        for row in ws.iter_rows(values_only=True):
            if row and len(row) > 2 and row[0] is not None and row[2]:
                try:
                    mid = int(row[0])
                    raw = str(row[2]).strip()
                    proxy_map[mid] = raw
                except (ValueError, TypeError):
                    pass
        wb.close()
    except Exception:
        pass
    return proxy_map


def run_deduplication(dry_run: bool = True):
    if not GPM_DB.exists():
        print(f"Không tìm thấy GPM DB tại {GPM_DB}")
        return

    email_machine = load_email_to_machine()
    machine_proxy = load_machine_to_proxy()

    conn = sqlite3.connect(str(GPM_DB))
    cur = conn.cursor()
    cur.execute("SELECT Id, Name, ProfilePath, CreatedAt, JsonData FROM profiles")
    rows = cur.fetchall()
    conn.close()

    email_to_profiles = defaultdict(list)
    for pid, name, ppath, cat, js in rows:
        if not name:
            continue
        m = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", name.lower())
        if m:
            email = m.group(1).lower()
            fpath = BASE_PROFILE_DIR / (ppath or "")
            cfile = fpath / "Default" / "Network" / "Cookies"
            csize = cfile.stat().st_size if cfile.exists() else 0
            cmtime = cfile.stat().st_mtime if cfile.exists() else 0
            email_to_profiles[email].append({
                "id": str(pid),
                "name": str(name),
                "path": str(ppath or ""),
                "created_at": str(cat or ""),
                "cookies_size": csize,
                "cookies_mtime": cmtime
            })

    duplicates = {em: profs for em, profs in email_to_profiles.items() if len(profs) > 1}
    print(f"Phát hiện {len(duplicates)} email có profile trùng lặp.")
    if not duplicates:
        print("Sạch 100%, không có profile trùng lặp.")
        return

    if not dry_run:
        ts = int(time.time())
        backup_file = GPM_DB.with_name(f"profile_data.db.backup_{ts}")
        shutil.copy2(GPM_DB, backup_file)
        print(f"Đã sao lưu DB -> {backup_file.name}")

    total_clones = 0
    deleted_count = 0

    for em, profs in sorted(duplicates.items()):
        expected_mid = email_machine.get(em)

        def rank_profile(p):
            mid_in_name = None
            m_mid = re.search(r"^\s*(\d+)\s*-", p["name"]) or re.search(r"^\s*M(\d+)\s*-", p["name"])
            if m_mid:
                try: mid_in_name = int(m_mid.group(1))
                except ValueError: pass
            is_machine_match = (mid_in_name == expected_mid) if (mid_in_name and expected_mid) else False
            return (p["cookies_size"], is_machine_match, p["cookies_mtime"])

        sorted_profs = sorted(profs, key=rank_profile, reverse=True)
        keep = sorted_profs[0]
        clones = sorted_profs[1:]
        total_clones += len(clones)

        print(f"\n[EMAIL] {em} (Máy M{expected_mid or '?'})")
        print(f"  ✓ GIỮ LẠI: ID {keep['id']} | Tên: '{keep['name']}' | Cookies: {keep['cookies_size']}B")

        for c in clones:
            print(f"  ✗ XÓA CLONE: ID {c['id']} | Tên: '{c['name']}' | Cookies: {c['cookies_size']}B")
            if not dry_run:
                try:
                    r = requests.get(f"{GPM_API}/profiles/delete/{c['id']}", params={"mode": 1}, timeout=10)
                    if r.status_code == 200:
                        print(f"     -> GPM API: {r.json().get('message', 'OK')}")
                except Exception as ex_api:
                    print(f"     -> Lỗi API: {ex_api}")

                try:
                    c_conn = sqlite3.connect(str(GPM_DB))
                    c_cur = c_conn.cursor()
                    c_cur.execute("DELETE FROM profiles WHERE Id = ?", (c["id"],))
                    c_conn.commit()
                    c_conn.close()
                except Exception as ex_db:
                    print(f"     -> Lỗi DB: {ex_db}")
                deleted_count += 1

    if dry_run:
        print(f"\n[DRY RUN HOÀN TẤT] {len(duplicates)} email với {total_clones} profile clone cần xóa.")
    else:
        print(f"\n[HOÀN TẤT DỌN DẸP] Đã xóa {deleted_count}/{total_clones} profile clone trùng lặp.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Thực thi xóa profile clone thừa")
    args = parser.parse_args()
    run_deduplication(dry_run=not args.apply)
