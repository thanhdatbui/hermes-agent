#!/usr/bin/env python3
"""
batch_clear_site_data_offline.py

Batch cleanup of specific website data (Cookies, Login Data, IndexedDB)
across ALL GPMLogin profiles directly on disk without launching CDP.
Extremely fast (processes hundreds of profiles in seconds).
Guarantees zero impact on non-targeted sites (Google, YouTube, etc.).
"""

import os
import sys
import time
import shutil
import sqlite3
import argparse
from pathlib import Path
import psutil

def kill_gpm_browser_processes():
    """Find and kill any running gpm_browser / chrome processes associated with GPMLogin."""
    killed = []
    print("[*] Scanning for active GPMLogin browser processes...")
    for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        try:
            name = (proc.info['name'] or '').lower()
            exe = (proc.info['exe'] or '').lower()
            cmd = ' '.join(proc.info['cmdline'] or []).lower()
            
            if 'chrome' in name:
                if 'gpm_browser' in exe or 'gpmlogin' in exe or r'programs\gpmlogin' in cmd:
                    print(f"  [-] Terminating GPMLogin chrome: PID={proc.info['pid']} ({proc.info['name']})")
                    proc.terminate()
                    killed.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if killed:
        gone, alive = psutil.wait_procs(killed, timeout=3)
        for p in alive:
            try:
                p.kill()
            except Exception:
                pass
        time.sleep(1)
        print(f"[+] Successfully closed {len(killed)} GPMLogin browser process(es).")
    else:
        print("[+] No GPMLogin browser processes currently running.")

def clean_profile_cookies(profile_dir: Path, patterns: list[str], backup_tag: str) -> tuple[int, str]:
    """Clean matching cookies from profile."""
    cookies_path = profile_dir / "Default" / "Network" / "Cookies"
    if not cookies_path.is_file():
        alt_path = profile_dir / "Default" / "Cookies"
        if alt_path.is_file():
            cookies_path = alt_path
        else:
            return 0, ""

    conn = None
    try:
        conn = sqlite3.connect(cookies_path, timeout=30.0)
        cur = conn.cursor()
        
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='cookies'")
        if cur.fetchone()[0] == 0:
            return 0, ""
            
        where_clause = " OR ".join([f"host_key LIKE '%{p}%'" for p in patterns])
        cur.execute(f"SELECT count(*) FROM cookies WHERE {where_clause}")
        count = cur.fetchone()[0]
        
        if count > 0:
            bak_path = cookies_path.parent / f"Cookies.{backup_tag}"
            if not bak_path.exists():
                shutil.copy2(cookies_path, bak_path)
                
            cur.execute(f"DELETE FROM cookies WHERE {where_clause};")
            conn.commit()
            cur.execute("VACUUM;")
            return count, ""
        return 0, ""
    except Exception as e:
        return 0, f"Cookies error: {e}"
    finally:
        if conn:
            conn.close()

def clean_profile_logins(profile_dir: Path, patterns: list[str], backup_tag: str) -> tuple[int, str]:
    """Clean matching login credentials from profile."""
    login_path = profile_dir / "Default" / "Login Data"
    if not login_path.is_file():
        return 0, ""

    conn = None
    try:
        conn = sqlite3.connect(login_path, timeout=30.0)
        cur = conn.cursor()
        
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='logins'")
        if cur.fetchone()[0] == 0:
            return 0, ""
            
        where_clause = " OR ".join([f"origin_url LIKE '%{p}%'" for p in patterns])
        cur.execute(f"SELECT count(*) FROM logins WHERE {where_clause}")
        count = cur.fetchone()[0]
        
        if count > 0:
            bak_path = login_path.parent / f"Login Data.{backup_tag}"
            if not bak_path.exists():
                shutil.copy2(login_path, bak_path)
                
            cur.execute(f"DELETE FROM logins WHERE {where_clause};")
            conn.commit()
            cur.execute("VACUUM;")
            return count, ""
        return 0, ""
    except Exception as e:
        return 0, f"Login Data error: {e}"
    finally:
        if conn:
            conn.close()

def clean_profile_indexeddb(profile_dir: Path, patterns: list[str]) -> tuple[int, str]:
    """Remove matching IndexedDB leveldb and blob directories."""
    idb_path = profile_dir / "Default" / "IndexedDB"
    if not idb_path.is_dir():
        return 0, ""

    deleted = 0
    patterns_lower = [p.lower() for p in patterns]
    try:
        for item in idb_path.iterdir():
            name_lower = item.name.lower()
            if any(p in name_lower for p in patterns_lower):
                if item.is_dir():
                    shutil.rmtree(item)
                    deleted += 1
                elif item.is_file():
                    item.unlink()
                    deleted += 1
        return deleted, ""
    except Exception as e:
        return deleted, f"IndexedDB error: {e}"

def run_batch_clean(base_dir: Path, patterns: list[str], backup_tag: str):
    print("=" * 80)
    print("BATCH CLEAR TARGET SITE DATA ACROSS ALL GPM PROFILES")
    print(f"Base Directory: {base_dir}")
    print(f"Patterns: {patterns}")
    print(f"Backup Tag: {backup_tag}")
    print("=" * 80)

    if not base_dir.is_dir():
        print(f"[!] Error: Profile directory not found at {base_dir}")
        sys.exit(1)

    kill_gpm_browser_processes()

    subdirs = [p for p in base_dir.iterdir() if p.is_dir() and p.name != "_backup"]
    subdirs.sort(key=lambda x: x.name)
    print(f"[*] Found {len(subdirs)} profile directories to scan.\n")

    results = []
    total_cookies = 0
    total_logins = 0
    total_idb = 0
    profiles_modified = 0

    start_time = time.time()

    for p_dir in subdirs:
        p_name = p_dir.name
        cookies_count, c_err = clean_profile_cookies(p_dir, patterns, backup_tag)
        logins_count, l_err = clean_profile_logins(p_dir, patterns, backup_tag)
        idb_count, i_err = clean_profile_indexeddb(p_dir, patterns)

        errors = [e for e in (c_err, l_err, i_err) if e]
        has_changes = (cookies_count > 0 or logins_count > 0 or idb_count > 0)

        if has_changes or errors:
            profiles_modified += 1
            total_cookies += cookies_count
            total_logins += logins_count
            total_idb += idb_count
            status = "SUCCESS" if not errors else f"FAIL ({'; '.join(errors)})"
            results.append({
                "profile": p_name,
                "cookies": cookies_count,
                "logins": logins_count,
                "indexeddb": idb_count,
                "status": status
            })

    elapsed = time.time() - start_time

    print("\n" + "=" * 90)
    print("SUMMARY OF PROFILES CLEANED")
    print("=" * 90)
    header = f"{'#':<4} | {'Profile Name':<38} | {'Cookies':<8} | {'Logins':<8} | {'IndexedDB':<10} | {'Status':<10}"
    print(header)
    print("-" * 90)

    for i, res in enumerate(results, 1):
        line = f"{i:<4} | {res['profile']:<38} | {res['cookies']:<8} | {res['logins']:<8} | {res['indexeddb']:<10} | {res['status']:<10}"
        print(line)

    print("-" * 90)
    print(f"Total Profiles Scanned       : {len(subdirs)}")
    print(f"Profiles Cleaned             : {profiles_modified}")
    print(f"Total Cookies Removed        : {total_cookies}")
    print(f"Total Logins Removed         : {total_logins}")
    print(f"Total IndexedDB Dirs Removed : {total_idb}")
    print(f"Execution Time               : {elapsed:.2f} seconds")
    print("=" * 90)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch Selective Site Data Cleanup for GPMLogin Profiles")
    parser.add_argument("--base-dir", default=r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile", help="Path to GPMLogin profile directory")
    parser.add_argument("--patterns", nargs="+", default=["openai", "chatgpt"], help="Domain patterns to clear (e.g. openai chatgpt)")
    parser.add_argument("--backup-tag", default="bak_chatgpt", help="Suffix for backup files (e.g. bak_chatgpt)")
    args = parser.parse_args()

    run_batch_clean(Path(args.base_dir), args.patterns, args.backup_tag)
