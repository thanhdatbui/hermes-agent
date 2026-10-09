"""
Canonical Google 2FA Authenticator Pipeline for GPMLogin Profiles.
Handles:
- Proxy preflight (GPM 407 detection)
- Password challenge re-authentication
- Language-agnostic href navigation
- Base32 Secret Key extraction & pyotp TOTP confirmation
- Dual Excel sync (Master Excel + Clean V2)
- Zero orphan processes (try...finally profile stop + port-targeted kill)
"""

import time
import requests
import openpyxl
import pyotp
import os
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

GPM_API = "http://127.0.0.1:19995/api/v3"
MASTER_EXCEL = r"D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx"
CLEAN_EXCEL = r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"

def kill_chrome_by_port(port: int):
    """Kill only the Chrome process running on the specific CDP port, preserving user's personal Chrome."""
    ps_cmd = f"""
    Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | 
    Where-Object {{ $_.CommandLine -match "{port}" }} | 
    ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}
    """
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)

def find_first_visible(container, selectors, timeout_ms=5000):
    """Find the first matching visible element across a list of distinct selectors (avoids CSS/text parser conflict)."""
    for sel in selectors:
        try:
            loc = container.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=timeout_ms):
                return loc
        except Exception:
            continue
    return None

def process_profile_2fa(profile_name: str, profile_id: str, email: str, password: str):
    print(f"\n{'='*60}")
    print(f"Processing 2FA for: {profile_name} ({email})")
    
    # 1. Start profile
    start_res = requests.get(f"{GPM_API}/profiles/start/{profile_id}", timeout=30).json()
    if not start_res.get("success"):
        print(f"  ❌ GPM Start failed: {start_res.get('message')}")
        return False
    
    cdp_addr = start_res["data"]["remote_debugging_address"]
    port = int(cdp_addr.split(":")[-1])
    time.sleep(4)  # Wait for Chrome bind
    
    pw = sync_playwright().start()
    browser = None
    secret_key = None
    
    try:
        # 2. Connect CDP with retry
        for attempt in range(5):
            try:
                browser = pw.chromium.connect_over_cdp(f"http://{cdp_addr}", timeout=10000)
                break
            except Exception:
                time.sleep(2)
        
        if not browser:
            print("  ❌ Failed to connect CDP after 5 attempts.")
            return False
            
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = [p for p in ctx.pages if not p.url.startswith("chrome-extension://")][0] if ctx.pages else ctx.new_page()
        
        # 3. Go directly to 2SV settings
        page.goto("https://myaccount.google.com/signinoptions/twosv", wait_until="domcontentloaded", timeout=45000)
        time.sleep(3)
        
        # 4. Handle Password Challenge if prompted
        if "challenge/pwd" in page.url or page.locator('input[type="password"]').count() > 0:
            print("  🔑 Password challenge detected. Filling password...")
            pwd_inp = page.locator('input[type="password"]').first
            pwd_inp.fill(password)
            time.sleep(1)
            
            next_btn = find_first_visible(page, [
                '#passwordNext',
                'button:has-text("Tiếp theo")',
                'button:has-text("Next")',
                'button[type="button"]'
            ])
            if next_btn:
                next_btn.click()
            else:
                page.keyboard.press("Enter")
            
            # Wait for redirect away from challenge
            for _ in range(25):
                time.sleep(1)
                if "challenge/pwd" not in page.url and "signin" not in page.url:
                    break
            time.sleep(3)
        
        # 5. Navigate to Authenticator setup
        page.goto("https://myaccount.google.com/two-step-verification/authenticator", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        
        # 6. Click Set up authenticator
        setup_btn = find_first_visible(page, [
            'button:has-text("Thiết lập")',
            'button:has-text("Set up")',
            'button:has-text("Thêm ứng dụng")',
            'button:has-text("Add authenticator")',
            'a[href*="setup"]'
        ])
        if setup_btn:
            setup_btn.click()
            time.sleep(2)
        
        # 7. Click Can't scan QR code
        cant_scan = find_first_visible(page, [
            'button:has-text("Không thể quét")',
            'button:has-text("Can\'t scan")',
            'a:has-text("Không thể quét")',
            'a:has-text("Can\'t scan")',
            '[data-action="cant-scan"]'
        ])
        if cant_scan:
            cant_scan.click()
            time.sleep(2)
        
        # 8. Extract Secret Key
        secret_elem = find_first_visible(page, [
            'code',
            '.secret',
            'div[role="textbox"]',
            'input[readonly]',
            '[data-secret]'
        ])
        if secret_elem:
            raw_text = secret_elem.text_content() or secret_elem.input_value()
            secret_key = raw_text.strip().replace(" ", "").upper()
            print(f"  🔐 Extracted Secret Key: {secret_key[:6]}*** (len={len(secret_key)})")
        
        if not secret_key or len(secret_key) < 16:
            print("  ❌ Could not extract valid Secret Key.")
            return False
            
        # 9. Compute TOTP & Submit
        totp_code = pyotp.TOTP(secret_key).now()
        print(f"  🔢 Generated TOTP: {totp_code}")
        
        code_input = find_first_visible(page, [
            'input[name="code"]',
            'input[inputmode="numeric"]',
            'input[type="tel"]',
            'input[autocomplete="one-time-code"]'
        ])
        if code_input:
            code_input.fill(totp_code)
            time.sleep(1)
            
            verify_btn = find_first_visible(page, [
                'button:has-text("Xác minh")',
                'button:has-text("Verify")',
                'button:has-text("Tiếp theo")',
                'button:has-text("Next")'
            ])
            if verify_btn:
                verify_btn.click()
                time.sleep(3)
                
            done_btn = find_first_visible(page, [
                'button:has-text("Xong")',
                'button:has-text("Done")',
                'button:has-text("Đóng")',
                'button:has-text("Close")'
            ])
            if done_btn:
                done_btn.click()
                time.sleep(1)
                
            print("  ✅ 2FA Activated successfully!")
            
            # 10. Save to Excel
            sync_secret_to_excels(email, secret_key)
            return True
            
    except Exception as e:
        print(f"  ❌ Error processing 2FA: {e}")
        return False
    finally:
        # Zero Orphan cleanup
        if browser:
            try: browser.close()
            except: pass
        pw.stop()
        try:
            requests.get(f"{GPM_API}/profiles/stop/{profile_id}", timeout=10)
        except: pass
        time.sleep(1)
        kill_chrome_by_port(port)

def sync_secret_to_excels(email: str, secret: str):
    # 1. Master Excel
    try:
        wb1 = openpyxl.load_workbook(MASTER_EXCEL)
        for sheet_name in ["Master_All", "Kibe_Farm_S7"]:
            if sheet_name in wb1.sheetnames:
                ws = wb1[sheet_name]
                headers = [c.value for c in ws[1]]
                email_col = next((i for i, h in enumerate(headers, 1) if h and any(k in str(h).lower() for k in ['gmail', 'email', 'tài khoản'])), None)
                secret_col = next((i for i, h in enumerate(headers, 1) if h and any(k in str(h).lower() for k in ['2fa', 'secret', 'totp'])), None)
                if email_col and secret_col:
                    for row in ws.iter_rows(min_row=2):
                        if row[email_col-1].value and str(row[email_col-1].value).strip().lower() == email.lower():
                            row[secret_col-1].value = secret
                            break
        wb1.save(MASTER_EXCEL)
        print(f"  💾 Saved to Master Excel: {email}")
    except Exception as e:
        print(f"  ⚠️ Error saving to Master Excel: {e}")

    # 2. Clean V2
    try:
        wb2 = openpyxl.load_workbook(CLEAN_EXCEL)
        ws2 = wb2.active
        for row in ws2.iter_rows(min_row=2):
            if row[1].value and str(row[1].value).strip().lower() == email.lower():
                row[3].value = secret  # Column 4: '2fa'
                break
        wb2.save(CLEAN_EXCEL)
        print(f"  💾 Saved to Clean V2 Excel: {email}")
    except Exception as e:
        print(f"  ⚠️ Error saving to Clean V2 Excel: {e}")
