# Google reCAPTCHA Enterprise Audio Solver with Playwright & SpeechRecognition

Tài liệu kỹ thuật và mẫu tích hợp bộ giải reCAPTCHA Enterprise Audio tự động trên Playwright CDP trong luồng xác thực Google / Antigravity OAuth.

---

## 1. Yêu cầu môi trường & Thư viện

- **FFmpeg (Windows)**: Cần thiết để `pydub` decode `.mp3` tải về từ Google reCAPTCHA thành `.wav`.
  - Đường dẫn chuẩn trên máy:
    ```python
    FFMPEG_DIR = r"C:\Users\Kibe\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin"
    if os.path.exists(FFMPEG_DIR):
        os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")
        pydub.AudioSegment.converter = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
    ```
- **Thư viện Python**:
  - `pydub`
  - `speech_recognition` (`import speech_recognition as sr`)
  - `playwright.sync_api`

---

## 2. Cấu trúc iframe của Google reCAPTCHA

reCAPTCHA hiển thị thông qua 2 iframe chính:
1. **Anchor Frame**: URL chứa `anchor` (ví dụ `enterprise/anchor` hoặc `api2/anchor`).
   - Chứa checkbox `#recaptcha-anchor` hoặc `.recaptcha-checkbox`.
   - Nếu `aria-checked == "true"` ngay sau khi click -> đã pass tự động (green checkmark).
2. **Bframe (Challenge Frame)**: URL chứa `bframe` (ví dụ `enterprise/bframe` hoặc `api2/bframe`).
   - Xuất hiện sau khi click anchor nếu bị yêu cầu thử thách.
   - Nút audio: `#recaptcha-audio-button`, `button[title*='audio']`, `button[title*='âm thanh']`.
   - Nguồn âm thanh: `#audio-source`, `.rc-audiochallenge-tdownload-link`, `audio`.
   - Ô nhập text: `#audio-response`, `input[name='audio-response']`.
   - Nút xác minh: `#recaptcha-verify-button`, `button:has-text('Verify')`, `button:has-text('Xác minh')`.

---

## 3. Mẫu hàm chuẩn: `solve_recaptcha_audio`

```python
import os
import time
import urllib.request
import pydub
import speech_recognition as sr
from playwright.sync_api import Page

def solve_recaptcha_audio(page: Page, logger=None) -> bool:
    """Tự động phát hiện và giải reCAPTCHA Enterprise Audio Challenge trên trang Google/Antigravity."""
    def _log(msg):
        if logger:
            logger.info(msg)
        else:
            print(f"[reCAPTCHA] {msg}")

    anchor_frame = None
    bframe = None

    _log("Searching for reCAPTCHA iframes...")
    for _ in range(8):
        for f in page.frames:
            if "enterprise/anchor" in f.url or "api2/anchor" in f.url or ("recaptcha" in f.url and "anchor" in f.url):
                anchor_frame = f
            if "enterprise/bframe" in f.url or "api2/bframe" in f.url or ("recaptcha" in f.url and "bframe" in f.url):
                bframe = f
        if anchor_frame:
            break
        time.sleep(1)

    if not anchor_frame:
        return False

    try:
        # 1. Click checkbox anchor
        anchor_btn = anchor_frame.locator("#recaptcha-anchor, .recaptcha-checkbox")
        if anchor_btn.count() > 0:
            _log("Clicking reCAPTCHA checkbox...")
            anchor_btn.first.click()
            time.sleep(3)

        if anchor_frame.locator("#recaptcha-anchor").get_attribute("aria-checked") == "true":
            _log("reCAPTCHA checkbox passed automatically (green check)!")
            return True

        # 2. Tìm bframe thử thách
        for _ in range(6):
            for f in page.frames:
                if "enterprise/bframe" in f.url or "api2/bframe" in f.url or "bframe" in f.url:
                    bframe = f
                    break
            if bframe:
                break
            time.sleep(1)

        if not bframe:
            _log("No reCAPTCHA bframe found after clicking anchor.")
            return False

        # 3. Click nút Audio Challenge
        audio_btn = bframe.locator("#recaptcha-audio-button, button[title*='audio'], button[title*='âm thanh']")
        if audio_btn.count() == 0 or not audio_btn.first.is_visible():
            _log("Audio challenge button not visible.")
            return False

        _log("Clicking reCAPTCHA audio challenge button...")
        audio_btn.first.click()
        time.sleep(3)

        # 4. Trích xuất link file âm thanh
        audio_src = None
        audio_elem = bframe.locator("#audio-source, .rc-audiochallenge-tdownload-link, audio")
        if audio_elem.count() > 0:
            audio_src = audio_elem.first.get_attribute("href") or audio_elem.first.get_attribute("src")

        if not audio_src:
            _log("Could not find audio src in bframe.")
            return False

        # 5. Tải MP3, convert WAV và nhận diện giọng nói
        cache_dir = r"C:\Users\Kibe\AppData\Local\hermes\cache"
        os.makedirs(cache_dir, exist_ok=True)
        ts = int(time.time() * 1000)
        mp3_path = os.path.join(cache_dir, f"recaptcha_{ts}.mp3")
        wav_path = os.path.join(cache_dir, f"recaptcha_{ts}.wav")

        urllib.request.urlretrieve(audio_src, mp3_path)
        sound = pydub.AudioSegment.from_mp3(mp3_path)
        sound.export(wav_path, format="wav")

        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data)

        _log(f"Recognized Speech Text: '{text}'")

        # Dọn dẹp file tạm
        for p in [mp3_path, wav_path]:
            if os.path.exists(p):
                os.remove(p)

        # 6. Nhập văn bản và xác nhận
        inp = bframe.locator("#audio-response, input[name='audio-response']")
        inp.fill(text)
        time.sleep(1)

        verify_btn = bframe.locator("#recaptcha-verify-button, button:has-text('Verify'), button:has-text('Xác minh')").first
        if verify_btn.count() > 0 and verify_btn.is_visible():
            verify_btn.click()
            time.sleep(4)

        _log("reCAPTCHA audio verification submitted!")
        return True
    except Exception as e:
        _log(f"Error solving reCAPTCHA audio: {e}")
        return False
```

---

## 4. Tích hợp vào Watchdog / OAuth Loop

Trong vòng lặp chờ OAuth code (`while time.time() - start_t < timeout:`):
- Đặt bước quét reCAPTCHA song song hoặc trước các bước điền mật khẩu/TOTP:
  ```python
  for f in page.frames:
      if "anchor" in f.url and "recaptcha" in f.url:
          solve_recaptcha_audio(page)
          time.sleep(2)
          break
  ```
- Luôn chụp screenshot bằng chứng lưu vào `cache/` sau khi giải để kiểm tra audit.
