"""Automated pipeline to batch OAuth Codex accounts into 9Router via GPM and Microsoft Graph API OTP."""

import os
import sys
import time
import json
import re
import datetime
import urllib.request
import urllib.parse
import sqlite3
import openpyxl
from playwright.sync_api import sync_playwright

sys.path.append(r'D:\Taadaa\GPM auto\scripts')
from chatgpt_gpm_direct_reg import get_hotmail_credentials, MicrosoftGraphOTPProvider

def bind_proxy_pool_in_9router(conn_id: str, port_num: int):
    """Binds the per-account 4G mobile proxy pool to the newly imported connection."""
    db_path = r'C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    pool = cur.execute("SELECT id FROM proxyPools WHERE data LIKE ?", (f'%{port_num}%',)).fetchone()
    if pool:
        r = cur.execute("SELECT data FROM providerConnections WHERE id = ?", (conn_id,)).fetchone()
        if r:
            d = json.loads(r[0])
            d.setdefault('providerSpecificData', {})
            d['providerSpecificData']['proxyPoolId'] = pool[0]
            cur.execute("UPDATE providerConnections SET data = ? WHERE id = ?", (json.dumps(d), conn_id))
            conn.commit()
            print(f"  [+] Bound proxy pool {pool[0]} (port {port_num}) to connection {conn_id}!")
    conn.close()

def try_oauth_account(pid: str, email: str, port_num: int) -> bool:
    """Carries out the full automated PKCE OAuth flow for a single GPM profile."""
    print(f"\n[*] Processing OAuth for {email} (Proxy Port: {port_num})...")

    creds = get_hotmail_credentials(email)
    if not creds:
        print(f"[-] No Graph API credentials for {email}")
        return False
    
    otp_prov = MicrosoftGraphOTPProvider(refresh_token=creds['refresh_token'], client_id=creds['client_id'])

    # 1. Generate 9Router PKCE authorization URL
    auth_res = json.loads(urllib.request.urlopen(
        'http://127.0.0.1:20128/api/oauth/codex/authorize?redirect_uri=http://localhost:1455/auth/callback',
        timeout=10
    ).read().decode())
    auth_url = auth_res['authUrl']
    state = auth_res['state']
    code_verifier = auth_res['codeVerifier']

    params = urllib.parse.urlencode({
        'app_port': '1455',
        'state': state,
        'code_verifier': code_verifier,
        'redirect_uri': 'http://localhost:1455/auth/callback'
    })
    urllib.request.urlopen(f'http://127.0.0.1:20128/api/oauth/codex/start-proxy?{params}', timeout=10)

    # 2. Launch GPM profile via GPM API
    gpm_res = json.loads(urllib.request.urlopen(
        f'http://127.0.0.1:19995/api/v3/profiles/start/{pid}?win_scale=0.8',
        timeout=30
    ).read().decode())
    cdp = gpm_res.get('data', {}).get('remote_debugging_address')
    if not cdp:
        return False

    success = False
    try:
        with sync_playwright() as p:
            b = p.chromium.connect_over_cdp(f'http://{cdp}')
            page = b.contexts[0].new_page()
            page.goto(auth_url, timeout=30000)
            time.sleep(3)

            # Fill email
            email_inp = page.locator('input[type="email"], input[name="email"]').first
            if email_inp.is_visible(timeout=3000):
                email_inp.fill(email)
                time.sleep(1)
                page.locator('button:has-text("Tiếp tục"), button[type="submit"]').first.click()
                time.sleep(4)

            # Handle password screen if prompt for one-time code link
            pwd_inp = page.locator('input[type="password"]').first
            if pwd_inp.is_visible(timeout=2000):
                otp_link = page.locator('button:has-text("dùng một lần"), a:has-text("dùng một lần")').first
                if otp_link.is_visible(timeout=1500):
                    otp_link.click()
                    time.sleep(3)

            # Capture OTP from Microsoft Graph API
            cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2)
            code = None
            for _ in range(12):
                time.sleep(3)
                code = otp_prov.fetch_otp(received_after=cutoff)
                if code:
                    break

            if code:
                code_inp = page.locator('input[name="code"], input[autocomplete="one-time-code"]').first
                if code_inp.is_visible(timeout=3000):
                    code_inp.fill(code)
                    time.sleep(1)
                    page.locator('button:has-text("Tiếp tục"), button[type="submit"]').first.click()
                    time.sleep(6)

            body_txt = page.locator('body').inner_text().lower()
            if 'account_deactivated' in body_txt or 'vô hiệu hóa' in body_txt:
                print(f"[-] Account {email} deactivated by OpenAI.")
                return False
            if 'phone' in page.url or 'số điện thoại' in body_txt:
                print(f"[-] Account {email} blocked by Phone Verification gate.")
                return False

            # Workspace step: click card and submit button
            card = page.locator('button:has-text("Tài khoản cá nhân"), div:has-text("Tài khoản cá nhân")').first
            if card.is_visible(timeout=3000):
                card.click()
                time.sleep(1)
            btn = page.locator('button:has-text("Tiếp tục"), button[type="submit"]').first
            if btn.is_visible(timeout=3000):
                btn.click()
                time.sleep(6)

            # Consent step
            consent_btn = page.locator('button:has-text("Cho phép"), button:has-text("Ủy quyền"), button:has-text("Tiếp tục"), button:has-text("Continue"), button:has-text("Authorize"), button[type="submit"]').first
            if consent_btn.is_visible(timeout=3000):
                consent_btn.click()
                time.sleep(5)

            # Poll 9Router status
            for _ in range(10):
                poll = json.loads(urllib.request.urlopen(
                    f'http://127.0.0.1:20128/api/oauth/codex/poll-status?state={state}',
                    timeout=10
                ).read().decode())
                if poll.get('status') == 'done':
                    conn_id = poll.get('connectionId')
                    print(f"[+] OAuth successful in 9Router! Connection ID: {conn_id}")
                    bind_proxy_pool_in_9router(conn_id, port_num)
                    success = True
                    break
                time.sleep(2)

            page.close()
            b.close()
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        urllib.request.urlopen(f'http://127.0.0.1:19995/api/v3/profiles/close/{pid}', timeout=10)

    return success
