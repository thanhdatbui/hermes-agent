"""
NVIDIA NIM Account Registration Automation via GPM + Hotmail
"""
import urllib.request
import json
import time
from playwright.sync_api import sync_playwright

GPM_API = "http://127.0.0.1:19995"

def start_gpm_profile(profile_id: str) -> str:
    url = f"{GPM_API}/api/v3/profiles/start/{profile_id}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        if not data.get("success"):
            raise Exception(f"Failed to start profile: {data}")
        return data["data"]["remote_debugging_address"]

def stop_gpm_profile(profile_id: str):
    url = f"{GPM_API}/api/v3/profiles/stop/{profile_id}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print("Stop error:", e)

def register_nvidia(profile_id: str, email: str, hotmail_password: str, nvidia_password: str = "TaadaaNvidia#2026!"):
    cdp = start_gpm_profile(profile_id)
    print(f"Profile {profile_id} started at CDP {cdp}")
    time.sleep(3)
    
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://{cdp}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        
        print("Navigating to https://build.nvidia.com/explore/discover?modal=signin ...")
        page.goto("https://build.nvidia.com/explore/discover?modal=signin", timeout=60000)
        time.sleep(5)
        
        # 1. Fill email
        email_inp = page.locator("input[type='email'], input[placeholder*='email' i]")
        if email_inp.count() > 0:
            email_inp.first.fill(email)
            email_inp.first.press("Enter")
            time.sleep(5)
            
        # 2. Microsoft login if redirected
        if "login.live.com" in page.url:
            print("Entering Hotmail password...")
            pw_inp = page.locator("input[type='password'], input[name='passwd']")
            if pw_inp.count() > 0:
                pw_inp.first.fill(hotmail_password)
                submit_btn = page.locator("input[type='submit'], button[type='submit']")
                submit_btn.first.click()
                time.sleep(8)
                
        # 3. Handle Complete Profile page
        if "create-account" in page.url or "link-account" in page.url:
            print("On NVIDIA profile completion page...")
            pws = page.locator("input[type='password']").all()
            if len(pws) >= 2:
                pws[0].fill(nvidia_password)
                pws[1].fill(nvidia_password)
            
            # Check terms
            cbs = page.locator("input[type='checkbox']").all()
            for cb in cbs:
                try:
                    cb.check()
                except:
                    pass
            print("Form prepared. Awaiting hCaptcha resolution...")
            # Note: Integrate YesCaptcha or CapSolver here to solve hCaptcha automatically
            
if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4:
        register_nvidia(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python nvidia_gpm_flow.py <profile_id> <email> <hotmail_password>")
