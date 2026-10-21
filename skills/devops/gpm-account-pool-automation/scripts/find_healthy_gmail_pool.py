#!/usr/bin/env python3
"""Scan and return live Gmail accounts in GPM pool with active Google session cookies."""
import os
import sqlite3
import json
import time
import re
import openpyxl

CHROME_EPOCH_DELTA = 11644473600
now_chrome = int((time.time() + CHROME_EPOCH_DELTA) * 1000000)

def get_healthy_gmail_candidates():
    die_set = set()
    die_path = r"D:\OneDrive\TaadaaData\kibe\gmail_die_tong.txt"
    if os.path.exists(die_path):
        with open(die_path, "r", encoding="utf-8") as f:
            for line in f:
                em = line.strip().lower()
                if em:
                    die_set.add(em)

    excel_path = r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"
    excel_data = {}
    if os.path.exists(excel_path):
        wb = openpyxl.load_workbook(excel_path, read_only=True)
        ws = wb["Gmail Accounts"]
        for row in ws.iter_rows(values_only=True):
            if len(row) > 1 and row[1] and "@gmail.com" in str(row[1]).lower():
                em = str(row[1]).strip().lower()
                excel_data[em] = {
                    "machine": row[0],
                    "pass": row[2],
                    "2fa": row[3],
                    "recovery": row[4],
                    "created_at": str(row[6]) if len(row) > 6 else None
                }

    gpm_dir = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile"
    db_path = os.path.join(gpm_dir, "profile_data.db")
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("SELECT Id, Name, ProfilePath, JsonData FROM Profiles")
    rows = cur.fetchall()
    conn.close()

    healthy_candidates = []

    for r in rows:
        pid, name, ppath, js = r
        if not name or "@gmail.com" not in name.lower():
            continue
        
        match = re.search(r"([a-zA-Z0-9._%+-]+@gmail\.com)", name, re.I)
        if not match:
            continue
        email = match.group(1).lower()
        
        if email in die_set:
            continue
            
        cp = os.path.join(gpm_dir, ppath, "Default", "Network", "Cookies")
        if not os.path.exists(cp):
            cp = os.path.join(gpm_dir, ppath, "Default", "Cookies")
        if not os.path.exists(cp):
            continue
            
        try:
            cc = sqlite3.connect(f"file:{cp}?mode=ro", uri=True)
            crows = cc.cursor().execute("SELECT name, expires_utc FROM cookies WHERE host_key LIKE '%google%'").fetchall()
            cc.close()
            
            active_names = {row[0] for row in crows if row[1] == 0 or row[1] > now_chrome}
            if {"SID", "HSID", "SSID"}.issubset(active_names):
                info = excel_data.get(email, {})
                healthy_candidates.append({
                    "email": email,
                    "profile_id": pid,
                    "profile_name": name,
                    "machine": info.get("machine"),
                    "has_2fa": bool(info.get("2fa")),
                    "two_fa": info.get("2fa"),
                    "password": info.get("pass"),
                    "recovery": info.get("recovery"),
                    "created_at": info.get("created_at"),
                    "google_cookies": len(active_names)
                })
        except Exception:
            pass

    return healthy_candidates

if __name__ == "__main__":
    cands = get_healthy_gmail_candidates()
    print(f"Healthy Gmail Candidates Found: {len(cands)}")
    for c in cands[:5]:
        print(f"- {c['email']} (Profile: {c['profile_name']}, ID: {c['profile_id']})")
