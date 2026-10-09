"""
Script template for verifying logged-in Google session in GPMLogin profiles via Playwright CDP.
Handles Hairpin NAT / LAN proxy translation (mirotik1.taadaa.click -> 192.168.110.2)
and cleanly starts/stops each profile one by one to avoid resource leaks.
"""
import requests
import json
import time
import re
import psutil
from playwright.sync_api import sync_playwright

GPM_API_PORT = 19995
GPM_BASE_URL = f"http://127.0.0.1:{GPM_API_PORT}"

def kill_orphaned_chrome():
    killed = 0
    for p in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        try:
            name = (p.info['name'] or '').lower()
            exe = (p.info['exe'] or '').lower()
            cmd = ' '.join(p.info['cmdline'] or []).lower()
            if ('gpm_browser' in exe or 'gpmdriver' in name or 'chromedriver' in name or ('chrome.exe' in name and 'gpmlogin' in cmd)) and name != 'gpmlogin.exe':
                p.kill()
                killed += 1
        except:
            pass
    return killed

def verify_single_gpm_profile(profile_id, port, expected_email, pw):
    # Fetch profile details
    r = requests.get(f'{GPM_BASE_URL}/api/v3/profiles/{profile_id}', timeout=10)
    p_data = r.json().get('data', {})
    name = p_data.get('name', str(profile_id))
    orig_proxy = p_data.get('raw_proxy', '')

    # Fix Hairpin NAT: map external domain to internal LAN gateway for GPM proxy pre-flight check
    lan_proxy = orig_proxy
    if 'mirotik1.taadaa.click' in orig_proxy:
        lan_proxy = orig_proxy.replace('mirotik1.taadaa.click', '192.168.110.2')
    elif 'test.taadaa.click' in orig_proxy:
        lan_proxy = orig_proxy.replace('test.taadaa.click', '192.168.110.2')
    
    if lan_proxy != orig_proxy:
        requests.post(f'{GPM_BASE_URL}/api/v3/profiles/update/{profile_id}', json={'raw_proxy': lan_proxy}, timeout=10)

    start_resp = requests.get(f'{GPM_BASE_URL}/api/v3/profiles/start/{profile_id}', timeout=30).json()
    if not start_resp.get('success'):
        if lan_proxy != orig_proxy:
            requests.post(f'{GPM_BASE_URL}/api/v3/profiles/update/{profile_id}', json={'raw_proxy': orig_proxy}, timeout=10)
        return {
            "profile_name": name,
            "expected_email": expected_email,
            "actual_email": "Start Error",
            "match": "NO",
            "status": f"Start failed: {start_resp.get('message')}"
        }

    cdp_addr = start_resp['data']['remote_debugging_address']
    time.sleep(3)

    actual_email = None
    status = "Unknown"

    try:
        browser = None
        for _ in range(5):
            try:
                browser = pw.chromium.connect_over_cdp(f'http://{cdp_addr}', timeout=8000)
                break
            except Exception:
                time.sleep(2)

        if not browser:
            status = "CDP Connect Failed"
            actual_email = "CDP Error"
        else:
            context = browser.contexts[0]
            pages = [pg for pg in context.pages if not pg.url.startswith('chrome-extension://')]
            page = pages[0] if pages else context.new_page()

            page.goto("https://myaccount.google.com/", wait_until="domcontentloaded", timeout=25000)
            time.sleep(3)

            final_url = page.url
            title = page.title()

            if "about" in final_url.lower() or "signin" in final_url.lower() or "servicelogin" in final_url.lower():
                actual_email = "None (Not Logged In)"
                status = "Not Logged In (Redirected to Google About/SignIn)"
            else:
                extracted = page.evaluate('''() => {
                    const emails = new Set();
                    const accountElements = document.querySelectorAll('a[href*="SignOutOptions"], [aria-label*="@"], [title*="@"], [data-email]');
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
                    return Array.from(emails);
                }''')
                if extracted:
                    actual_email = extracted[0]
                    status = f"Logged In ({actual_email})"
                else:
                    actual_email = "Logged In (Email not found in DOM)"
                    status = f"Logged In ({title})"

            try:
                browser.close()
            except:
                pass
    except Exception as e:
        status = f"Exception: {str(e)[:50]}"
        actual_email = "Error"
    finally:
        requests.get(f'{GPM_BASE_URL}/api/v3/profiles/stop/{profile_id}', timeout=10)
        if lan_proxy != orig_proxy:
            requests.post(f'{GPM_BASE_URL}/api/v3/profiles/update/{profile_id}', json={'raw_proxy': orig_proxy}, timeout=10)
        kill_orphaned_chrome()

    match = "YES" if actual_email and actual_email.lower() == expected_email.lower() else "NO"
    return {
        "profile_name": name,
        "expected_email": expected_email,
        "actual_email": actual_email,
        "match": match,
        "status": status
    }
