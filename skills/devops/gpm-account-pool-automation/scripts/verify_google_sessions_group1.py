#!/usr/bin/env python3
"""
Google Session Verification for GPM Group 1 Profiles
Run: python verify_google_sessions_group1.py

Verifies all 29 Group 1 profiles have active Google sessions with matching emails.
Sequential execution with retry logic, proper cleanup, and incremental result saving.
"""
import os
import sys
import time
import json
import re
import requests
import psutil
from playwright.sync_api import sync_playwright

GPM_API_PORT = 19995
GPM_BASE_URL = f"http://127.0.0.1:{GPM_API_PORT}"
RESULTS_FILE = r"C:\Users\Kibe\gpm_group1_verification_results.json"

def kill_orphaned_chrome(target_port=None):
    """Clean up orphan chrome or gpmdriver processes."""
    killed = 0
    for p in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        try:
            name = (p.info['name'] or '').lower()
            exe = (p.info['exe'] or '').lower()
            cmd = ' '.join(p.info['cmdline'] or []).lower()
            if name == 'gpmlogin.exe':
                continue
            
            is_gpm = ('gpm_browser' in exe or 'gpmdriver' in name or 'chromedriver' in name or ('chrome.exe' in name and 'gpmlogin' in cmd))
            if is_gpm:
                if target_port:
                    if f'--remote-debugging-port={target_port}' in cmd or f':{target_port}' in cmd:
                        p.kill()
                        killed += 1
                else:
                    p.kill()
                    killed += 1
        except:
            pass
    return killed

def extract_expected_email(profile_name):
    """Extract expected email from profile name like '01 - thanhdatbui19951@gmail.com - 5101'"""
    match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', profile_name)
    if match:
        return match.group(1).lower()
    return "N/A (AMZ_Main)"

def verify_single_profile(profile_info):
    p_id = profile_info["id"]
    name = profile_info["name"]
    expected_email = extract_expected_email(name)
    
    print(f"\n==================================================")
    print(f"Profile: {name} | ID: {p_id}")
    print(f"Expected: {expected_email}")
    print(f"Proxy: {profile_info.get('raw_proxy')}")
    
    start_resp = {}
    try:
        start_resp = requests.get(f"{GPM_BASE_URL}/api/v3/profiles/start/{p_id}", timeout=25).json()
    except Exception as e:
        print(f"Start request exception: {e}")
        return {
            "profile_name": name,
            "profile_id": p_id,
            "expected_email": expected_email,
            "actual_email": "Start Exception",
            "match": "NO",
            "has_valid_session": False,
            "details": f"Start request failed: {e}"
        }
        
    if not start_resp.get("success"):
        print(f"Failed to start profile: {start_resp}")
        return {
            "profile_name": name,
            "profile_id": p_id,
            "expected_email": expected_email,
            "actual_email": "Start Failed",
            "match": "NO",
            "has_valid_session": False,
            "details": f"Start failed: {start_resp.get('message')}"
        }
    
    cdp_addr = start_resp["data"]["remote_debugging_address"]
    port = cdp_addr.split(":")[-1]
    print(f"CDP Address: {cdp_addr} (Port: {port})")
    
    time.sleep(2.5)
    
    actual_emails = []
    has_valid_session = False
    details = ""
    
    try:
        with sync_playwright() as pw:
            browser = None
            for attempt in range(5):
                try:
                    browser = pw.chromium.connect_over_cdp(f"http://{cdp_addr}", timeout=6000)
                    break
                except Exception as e:
                    time.sleep(1.5)
            
            if not browser:
                raise RuntimeError(f"Could not connect to CDP at {cdp_addr}")
            
            context = browser.contexts[0]
            pages = [p for p in context.pages if not p.url.startswith("chrome-extension://")]
            page = pages[0] if pages else context.new_page()
            
            try:
                page.goto("https://myaccount.google.com/", wait_until="domcontentloaded", timeout=20000)
            except Exception as e:
                print(f"Navigation error/timeout: {e}")
            
            time.sleep(2.5)
            current_url = page.url
            title = page.title()
            print(f"Navigated URL: {current_url} | Title: {title}")
            
            if "about" in current_url.lower() or "signin" in current_url.lower() or "servicelogin" in current_url.lower():
                has_valid_session = False
                details = f"Not logged in (Redirected to: {current_url})"
            else:
                extracted = page.evaluate('''() => {
                    const emails = new Set();
                    const accountElements = document.querySelectorAll('a[href*="SignOutOptions"], [aria-label*="@"], [title*="@"], [data-email], a[href*="accounts.google.com"]');
                    for (const el of accountElements) {
                        const aria = el.getAttribute('aria-label') || '';
                        const title = el.getAttribute('title') || '';
                        const dataEmail = el.getAttribute('data-email') || '';
                        const text = el.innerText || '';
                        [aria, title, dataEmail, text].forEach(str => {
                            const matches = str.match(/[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+/g);
                            if (matches) matches.forEach(m => emails.add(m.toLowerCase()));
                        });
                    }
                    const header = document.querySelector('header');
                    if (header) {
                        const matches = header.innerText.match(/[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+/g);
                        if (matches) matches.forEach(m => emails.add(m.toLowerCase()));
                    }
                    if (document.body) {
                        const bodyMatches = document.body.innerText.match(/[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+/g);
                        if (bodyMatches) bodyMatches.forEach(m => emails.add(m.toLowerCase()));
                    }
                    return Array.from(emails);
                }''')
                
                # Filter out system emails
                clean_emails = [e for e in extracted if not (e.endswith('@google.com') and 'support' not in e)]
                actual_emails = clean_emails if clean_emails else extracted
                
                if actual_emails:
                    has_valid_session = True
                    details = f"Session active. Email(s): {', '.join(actual_emails)}"
                else:
                    if "tài khoản google" in title.lower() or "google account" in title.lower():
                        has_valid_session = True
                        details = f"Session active (Title: {title})"
                    else:
                        details = f"Ambiguous state: URL={current_url}, Title={title}"
            
            try:
                browser.close()
            except:
                pass
    except Exception as e:
        details = f"Exception: {str(e)}"
        print(f"Error during CDP evaluation: {e}")
    finally:
        try:
            requests.get(f"{GPM_BASE_URL}/api/v3/profiles/stop/{p_id}", timeout=10)
        except:
            pass
        time.sleep(0.5)
        kill_orphaned_chrome(target_port=port)
    
    actual_str = ", ".join(actual_emails) if actual_emails else "None"
    match_status = "NO"
    if expected_email == "N/A (AMZ_Main)":
        match_status = "N/A"
    else:
        if any(e.lower() == expected_email.lower() for e in actual_emails):
            match_status = "YES"
        elif has_valid_session and expected_email in actual_str:
            match_status = "YES"
        else:
            match_status = "NO"
            
    result = {
        "profile_name": name,
        "profile_id": p_id,
        "expected_email": expected_email,
        "actual_email": actual_str,
        "match": match_status,
        "has_valid_session": has_valid_session,
        "details": details
    }
    print(f"Outcome: Actual={actual_str} | Match={match_status} | Session={has_valid_session}")
    return result

def main():
    print("Fetching Group 1 profiles from GPM API...")
    r = requests.get(f"{GPM_BASE_URL}/api/v3/profiles?page=1&per_page=100").json()
    profiles = r.get("data", [])
    print(f"Total profiles fetched: {len(profiles)}")
    
    # Load existing results if any to allow resume/caching
    results_map = {}
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                prev_results = json.load(f)
                for res in prev_results:
                    # Only cache if successful / conclusive
                    if res.get("actual_email") not in ["Start Exception", "Start Failed", None]:
                        results_map[res["profile_id"]] = res
        except:
            pass
            
    final_results = []
    for idx, p in enumerate(profiles, 1):
        p_id = p["id"]
        print(f"\n>>> [{idx}/{len(profiles)}] {p.get('name')}")
        if p_id in results_map:
            print(f"Using cached result for {p.get('name')}")
            res = results_map[p_id]
        else:
            res = verify_single_profile(p)
            results_map[p_id] = res
            
            # Save progress immediately
            with open(RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(list(results_map.values()), f, ensure_ascii=False, indent=2)
            time.sleep(1)
            
        final_results.append(res)
    
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
    print(f"\nAll {len(final_results)} profiles processed! Results saved to {RESULTS_FILE}")

if __name__ == "__main__":
    main()