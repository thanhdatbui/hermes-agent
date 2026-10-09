# Script re-usable: Giải reCAPTCHA OAuth & Onboarding ChatGPT Web trên GPM Profile

Script Playwright CDP kết nối GPM profile đang chạy, giải quyết checkbox/audio reCAPTCHA, vượt luồng Google OAuth / Account Chooser và lưu ảnh GATE 6.

```python
import asyncio
import json
import os
import tempfile
import urllib.request
import pydub
import speech_recognition as sr
from playwright.async_api import async_playwright

GPM_API = "http://127.0.0.1:19995/api/v3"

def transcribe_audio_from_url(audio_url):
    temp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_mp3_path, temp_wav_path = temp_mp3.name, temp_wav.name
    temp_mp3.close()
    temp_wav.close()

    try:
        urllib.request.urlretrieve(audio_url, temp_mp3_path)
        sound = pydub.AudioSegment.from_mp3(temp_mp3_path)
        sound.export(temp_wav_path, format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_wav_path) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data)
    finally:
        for p in (temp_mp3_path, temp_wav_path):
            if os.path.exists(p):
                os.remove(p)

async def solve_recaptcha_if_present(page):
    anchor_frame = next((f for f in page.frames if "recaptcha" in f.url and "anchor" in f.url), None)
    if anchor_frame:
        try:
            checkbox = await anchor_frame.query_selector("#recaptcha-anchor")
            if checkbox and await checkbox.get_attribute("aria-checked") != "true":
                await checkbox.click()
                await asyncio.sleep(4)
                if await checkbox.get_attribute("aria-checked") == "true":
                    return True
        except Exception:
            pass

    bframe = next((f for f in page.frames if "recaptcha" in f.url and "bframe" in f.url), None)
    if bframe:
        try:
            audio_btn = await bframe.query_selector("#recaptcha-audio-button")
            if audio_btn and await audio_btn.is_visible():
                await audio_btn.click()
                await asyncio.sleep(3)
            audio_src_el = await bframe.query_selector("#audio-source")
            if audio_src_el:
                src = await audio_src_el.get_attribute("src")
                text = transcribe_audio_from_url(src)
                resp_input = await bframe.query_selector("#audio-response")
                if resp_input:
                    await resp_input.fill(text)
                    btn = await bframe.query_selector("#recaptcha-verify-button")
                    if btn:
                        await btn.click()
                        await asyncio.sleep(3)
                        return True
        except Exception:
            pass
    return False

async def pass_gate6_chatgpt(profile_id: str, report_png_path: str):
    # Start profile
    res = urllib.request.urlopen(f"{GPM_API}/profiles/start/{profile_id}").read()
    remote_port = json.loads(res)["data"]["remote_debugging_address"]
    
    os.makedirs(os.path.dirname(report_png_path), exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(f"http://{remote_port}")
        context = browser.contexts[0]
        page = next((pg for pg in context.pages if "chatgpt.com" in pg.url or "google.com" in pg.url), context.pages[0])
        if "chrome://" in page.url:
            await page.goto("https://chatgpt.com", timeout=60000)

        for _ in range(25):
            await asyncio.sleep(2)
            for pg in context.pages:
                if pg != page and ("google.com" in pg.url or "chatgpt.com" in pg.url):
                    page = pg
                    break

            curr_url = page.url
            if "chatgpt.com" in curr_url and "/auth" not in curr_url and "/login" not in curr_url:
                login_btn = await page.query_selector("button[data-testid='login-button']")
                if not login_btn:
                    # Dismiss modals
                    for close_sel in ["button:has-text('Dismiss')", "button:has-text('Stay logged out')", "button:has-text('Close')"]:
                        c = await page.query_selector(close_sel)
                        if c and await c.is_visible():
                            await c.click()
                    await page.screenshot(path=report_png_path)
                    break

            # Handle challenge & next buttons
            await solve_recaptcha_if_present(page)
            for nxt in ["button:has-text('Tiếp')", "button:has-text('Next')", "button:has-text('Continue')"]:
                btn = await page.query_selector(nxt)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(3)
                    break

        await browser.close()
    urllib.request.urlopen(f"{GPM_API}/profiles/close/{profile_id}")
```
