import os
import sys
import sqlite3
import json
import re
import tempfile
import zipfile
import time
from collections import defaultdict

CHROME_EPOCH_DELTA = 11644473600  # seconds between 1601-01-01 and 1970-01-01
CRITICAL_GOOGLE_COOKIES = {
    "SID", "HSID", "SSID", "APISID", "SAPISID",
    "__Secure-1PSID", "__Secure-3PSID", "__Secure-1PAPISID", "__Secure-3PAPISID",
    "OSID", "__Secure-OSID", "LOGIN_INFO"
}

def get_now_chrome():
    return int((time.time() + CHROME_EPOCH_DELTA) * 1000000)

def read_db_profiles(db_path):
    if not os.path.exists(db_path):
        return {}
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute("SELECT Id, Name, ProfilePath, JsonData, GroupId, CreatedAt, UpdatedAt FROM Profiles")
        rows = cur.fetchall()
        profiles = {}
        for r in rows:
            pid, name, ppath, js, gid, created, updated = r
            proxy = ""
            if js:
                try:
                    js_data = json.loads(js)
                    proxy = js_data.get("raw_proxy") or js_data.get("Proxy") or ""
                except:
                    pass
            profiles[ppath] = {
                "id": pid,
                "name": name,
                "path": ppath,
                "group_id": gid,
                "created_at": created,
                "updated_at": updated,
                "proxy": proxy
            }
        conn.close()
        return profiles
    except Exception as e:
        print(f"Error reading DB {db_path}: {e}")
        return {}

def inspect_login_data(db_path):
    results = {
        "gmail_logins": [],
        "google_acct_logins": [],
        "other_gmail_logins": []
    }
    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        return results
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='logins'")
        if not cur.fetchall():
            conn.close()
            return results
        cur.execute("SELECT origin_url, action_url, username_value, length(password_value) FROM logins")
        for row in cur.fetchall():
            orig, action, user, pass_len = row
            if not user:
                continue
            orig_str = orig or ""
            if "@gmail.com" in user.lower() or "accounts.google.com" in orig_str.lower():
                entry = {
                    "username": user.strip(),
                    "origin_url": orig_str,
                    "has_password": bool(pass_len and pass_len > 0)
                }
                results["gmail_logins"].append(entry)
                if "accounts.google.com" in orig_str.lower() or "google.com" in orig_str.lower():
                    results["google_acct_logins"].append(entry)
                else:
                    results["other_gmail_logins"].append(entry)
        conn.close()
    except Exception as e:
        results["error"] = str(e)
    return results

def inspect_cookies(db_path, now_chrome):
    results = {
        "google_cookies_count": 0,
        "critical_cookies": [],
        "has_active_session": False,
        "cookie_hosts": set()
    }
    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        return results
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cookies'")
        if not cur.fetchall():
            conn.close()
            return results
        cur.execute("SELECT host_key, name, expires_utc, length(value), length(encrypted_value) FROM cookies WHERE host_key LIKE '%.google.%' OR host_key LIKE '%google%'")
        rows = cur.fetchall()
        results["google_cookies_count"] = len(rows)
        for row in rows:
            host, name, expires_utc, vlen, evlen = row
            results["cookie_hosts"].add(host)
            if name in CRITICAL_GOOGLE_COOKIES:
                is_active = (expires_utc == 0 or expires_utc > now_chrome)
                results["critical_cookies"].append({
                    "name": name,
                    "host": host,
                    "active": is_active,
                    "expires_utc": expires_utc
                })
                if is_active and name in {"SID", "HSID", "SSID", "__Secure-1PSID", "__Secure-3PSID", "SAPISID"}:
                    results["has_active_session"] = True
        conn.close()
        results["cookie_hosts"] = list(results["cookie_hosts"])
    except Exception as e:
        results["error"] = str(e)
    return results

def inspect_preferences(pref_path):
    results = {
        "account_info": [],
        "gmail_matches": set()
    }
    if not os.path.exists(pref_path) or os.path.getsize(pref_path) == 0:
        return results
    try:
        with open(pref_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            emails = set(re.findall(r"[a-zA-Z0-9_.+-]+@gmail\.com", content, re.IGNORECASE))
            results["gmail_matches"] = emails
            try:
                data = json.loads(content)
                accs = data.get("account_info", [])
                if isinstance(accs, list):
                    for a in accs:
                        if isinstance(a, dict) and "email" in a:
                            results["account_info"].append(a["email"])
                prof = data.get("profile", {})
                info_cache = prof.get("info_cache", {})
                for k, v in info_cache.items():
                    if isinstance(v, dict):
                        if "user_name" in v and "@gmail.com" in v["user_name"].lower():
                            results["account_info"].append(v["user_name"])
            except:
                pass
    except Exception as e:
        results["error"] = str(e)
    results["gmail_matches"] = list(results["gmail_matches"])
    return results

def inspect_web_data(db_path):
    results = {
        "autofill_gmail": set()
    }
    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        return results
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='autofill'")
        if cur.fetchall():
            cur.execute("SELECT name, value FROM autofill WHERE value LIKE '%@gmail.com%' OR name LIKE '%@gmail.com%'")
            for row in cur.fetchall():
                for cell in row:
                    if cell and "@gmail.com" in cell.lower():
                        matches = re.findall(r"[a-zA-Z0-9_.+-]+@gmail\.com", cell, re.IGNORECASE)
                        for m in matches:
                            results["autofill_gmail"].add(m.lower())
        conn.close()
    except Exception as e:
        results["error"] = str(e)
    results["autofill_gmail"] = list(results["autofill_gmail"])
    return results

def inspect_folder(folder_path, now_chrome):
    candidates = {
        "login_data": [
            os.path.join(folder_path, "Default", "Login Data"),
            os.path.join(folder_path, "Login Data")
        ],
        "cookies": [
            os.path.join(folder_path, "Default", "Network", "Cookies"),
            os.path.join(folder_path, "Default", "Cookies"),
            os.path.join(folder_path, "Network", "Cookies"),
            os.path.join(folder_path, "Cookies")
        ],
        "preferences": [
            os.path.join(folder_path, "Default", "Preferences"),
            os.path.join(folder_path, "Preferences")
        ],
        "web_data": [
            os.path.join(folder_path, "Default", "Web Data"),
            os.path.join(folder_path, "Web Data")
        ]
    }
    res = {}
    for lp in candidates["login_data"]:
        if os.path.exists(lp):
            res["logins"] = inspect_login_data(lp)
            break
    if "logins" not in res:
        res["logins"] = {"gmail_logins": [], "google_acct_logins": [], "other_gmail_logins": []}
    for cp in candidates["cookies"]:
        if os.path.exists(cp):
            res["cookies"] = inspect_cookies(cp, now_chrome)
            break
    if "cookies" not in res:
        res["cookies"] = {"google_cookies_count": 0, "critical_cookies": [], "has_active_session": False, "cookie_hosts": []}
    for pp in candidates["preferences"]:
        if os.path.exists(pp):
            res["preferences"] = inspect_preferences(pp)
            break
    if "preferences" not in res:
        res["preferences"] = {"account_info": [], "gmail_matches": []}
    for wp in candidates["web_data"]:
        if os.path.exists(wp):
            res["web_data"] = inspect_web_data(wp)
            break
    if "web_data" not in res:
        res["web_data"] = {"autofill_gmail": []}
    return res

def run_inventory_scan(output_json=None):
    now_chrome = get_now_chrome()
    gpm_profile_dir = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile"
    gpm_db_path = os.path.join(gpm_profile_dir, "profile_data.db")
    backup_db_path = r"D:\OneDrive\backup\GPM\profile_data.db"
    
    db_profiles = read_db_profiles(gpm_db_path)
    backup_db_profiles = read_db_profiles(backup_db_path)
    
    disk_entries = os.listdir(gpm_profile_dir)
    disk_folders = [d for d in disk_entries if os.path.isdir(os.path.join(gpm_profile_dir, d)) and d not in {"_backup"}]
    
    all_results = {}
    for folder_name in disk_folders:
        folder_path = os.path.join(gpm_profile_dir, folder_name)
        data = inspect_folder(folder_path, now_chrome)
        db_info = db_profiles.get(folder_name)
        backup_db_info = backup_db_profiles.get(folder_name)
        gmails_found = set()
        for l in data["logins"]["gmail_logins"]:
            if "@gmail.com" in l["username"].lower():
                gmails_found.add(l["username"].lower())
        for a in data["preferences"]["account_info"]:
            if "@gmail.com" in a.lower():
                gmails_found.add(a.lower())
        for g in data["preferences"]["gmail_matches"]:
            gmails_found.add(g.lower())
        for af in data["web_data"]["autofill_gmail"]:
            gmails_found.add(af.lower())
        all_results[folder_name] = {
            "source": "disk",
            "folder_name": folder_name,
            "db_info": db_info,
            "backup_db_info": backup_db_info,
            "inspection": data,
            "gmails_found": sorted(list(gmails_found)),
            "has_gmail": len(gmails_found) > 0,
            "has_active_cookies": data["cookies"]["has_active_session"],
            "google_cookies_count": data["cookies"]["google_cookies_count"],
            "has_saved_password": any(l["has_password"] for l in data["logins"]["gmail_logins"]),
            "google_acct_logins": data["logins"]["google_acct_logins"]
        }
    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
    return all_results

if __name__ == "__main__":
    results = run_inventory_scan("gpm_gmail_inventory.json")
    print(f"Scan complete. Scanned {len(results)} profiles.")
