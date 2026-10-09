import os
import sys
import shutil
import sqlite3
import time
import argparse
import requests
import psutil

def cleanup_orphan_chrome(profile_dir_name: str):
    killed = 0
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and 'chrome' in p.info['name'].lower():
            try:
                cmd = ' '.join(p.cmdline() or [])
                if profile_dir_name in cmd:
                    p.kill()
                    killed += 1
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
    return killed

def clear_site_data(profile_dir: str, patterns: list[str], backup_tag: str = "bak_clean"):
    default_dir = os.path.join(profile_dir, "Default")
    cookie_file = os.path.join(default_dir, "Network", "Cookies")
    cookie_bak = os.path.join(default_dir, "Network", f"Cookies.{backup_tag}")
    login_file = os.path.join(default_dir, "Login Data")
    login_bak = os.path.join(default_dir, "Login Data.{backup_tag}")
    
    # 1. Backup files
    if os.path.exists(cookie_file):
        shutil.copy2(cookie_file, cookie_bak)
        print(f"[OK] Backed up Cookies -> {cookie_bak}")
    if os.path.exists(login_file):
        shutil.copy2(login_file, login_bak)
        print(f"[OK] Backed up Login Data -> {login_bak}")
        
    # 2. SQLite Cookies
    con = sqlite3.connect(cookie_file)
    cur = con.cursor()
    where_clauses = " OR ".join([f"host_key LIKE '%{p}%'" for p in patterns])
    cur.execute(f"SELECT COUNT(*) FROM cookies WHERE {where_clauses}")
    before_cookies = cur.fetchone()[0]
    
    cur.execute(f"DELETE FROM cookies WHERE {where_clauses}")
    con.commit()
    cur.execute("VACUUM")
    con.commit()
    
    cur.execute(f"SELECT COUNT(*) FROM cookies WHERE {where_clauses}")
    after_cookies = cur.fetchone()[0]
    con.close()
    
    # 3. SQLite Login Data
    con = sqlite3.connect(login_file)
    cur = con.cursor()
    where_logins = " OR ".join([f"origin_url LIKE '%{p}%'" for p in patterns])
    cur.execute(f"SELECT COUNT(*) FROM logins WHERE {where_logins}")
    before_logins = cur.fetchone()[0]
    
    cur.execute(f"DELETE FROM logins WHERE {where_logins}")
    con.commit()
    cur.execute("VACUUM")
    con.commit()
    
    cur.execute(f"SELECT COUNT(*) FROM logins WHERE {where_logins}")
    after_logins = cur.fetchone()[0]
    con.close()
    
    # 4. Clean IndexedDB & Local Storage
    cleaned_dirs = 0
    for sub in ['IndexedDB', os.path.join('Local Storage', 'leveldb')]:
        target_dir = os.path.join(default_dir, sub)
        if os.path.exists(target_dir):
            for item in os.listdir(target_dir):
                if any(p.lower() in item.lower() for p in patterns):
                    item_path = os.path.join(target_dir, item)
                    print(f"Removing {item_path}...")
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)
                    else:
                        os.remove(item_path)
                    cleaned_dirs += 1
                    
    print(f"[RESULT] Cookies deleted: {before_cookies - after_cookies} (Remaining: {after_cookies})")
    print(f"[RESULT] Logins deleted: {before_logins - after_logins} (Remaining: {after_logins})")
    print(f"[RESULT] Storage items removed: {cleaned_dirs}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Selective Site Data Cleanup for GPMLogin Profiles")
    parser.add_argument("--profile-dir", required=True, help="Path to profile directory")
    parser.add_argument("--patterns", nargs="+", required=True, help="Domain patterns to clear (e.g. openai chatgpt)")
    parser.add_argument("--backup-tag", default="bak_clean", help="Suffix for backup files")
    args = parser.parse_args()
    
    dir_name = os.path.basename(os.path.normpath(args.profile_dir))
    cleanup_orphan_chrome(dir_name)
    clear_site_data(args.profile_dir, args.patterns, args.backup_tag)
