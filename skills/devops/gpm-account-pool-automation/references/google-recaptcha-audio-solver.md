# Google reCAPTCHA Enterprise Audio Solver Automation

## 1. Nguyên lý
Khi đăng nhập tài khoản Gmail mới trên profile trình duyệt chưa có cookie/history, Google thường kích hoạt reCAPTCHA Enterprise với popup *"Xác minh danh tính của bạn — Xác nhận bạn không phải là rô-bốt"*.

Thay vì giải captcha hình ảnh phức tạp hoặc bắt người dùng thao tác thủ công, ta có thể tự động giải 100% bằng cách khai thác **Audio Challenge (Âm thanh)** kết hợp với mô hình nhận dạng giọng nói **Google Speech-to-Text API** (qua thư viện `speech_recognition` + `pydub` + `ffmpeg`).

---

## 2. Các thư viện phụ thuộc
```bash
pip install SpeechRecognition pydub
```
Đảm bảo đường dẫn `ffmpeg.exe` có sẵn trong `os.environ["PATH"]` (trên Windows thường nằm tại `C:\Users\Kibe\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin`).

---

## 3. Code mẫu giải Captcha Audio tự động chuẩn:

```python
import os
import time
import urllib.request
import pydub
import speech_recognition as sr
from playwright.sync_api import Page

# Đảm bảo ffmpeg trong PATH
FFMPEG_BIN = r"C:\Users\Kibe\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin"
if FFMPEG_BIN not in os.environ["PATH"]:
    os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ["PATH"]


def solve_recaptcha_audio(page: Page) -> bool:
    """Tự động phát hiện và giải reCAPTCHA Enterprise Audio Challenge trên trang Google."""
    anchor_frame = None
    bframe = None

    # 1. Tìm iframe anchor
    for _ in range(5):
        for f in page.frames:
            if "enterprise/anchor" in f.url or "api2/anchor" in f.url:
                anchor_frame = f
            if "enterprise/bframe" in f.url or "api2/bframe" in f.url:
                bframe = f
        if anchor_frame:
            break
        time.sleep(1)

    if not anchor_frame:
        return False

    # 2. Click checkbox
    anchor_frame.locator("#recaptcha-anchor").click()
    time.sleep(3)

    # Nếu click xong tự động pass luôn (Green check)
    if anchor_frame.locator("#recaptcha-anchor").get_attribute("aria-checked") == "true":
        return True

    # 3. Tìm iframe bframe (chứa puzzle/audio)
    for f in page.frames:
        if "enterprise/bframe" in f.url or "api2/bframe" in f.url:
            bframe = f
            break

    if not bframe:
        return False

    # 4. Click nút Chuyển sang Audio Challenge
    audio_btn = bframe.locator("#recaptcha-audio-button")
    if audio_btn.count() == 0:
        return False

    audio_btn.click()
    time.sleep(3)

    # 5. Lấy link tải file âm thanh .mp3
    audio_link = bframe.locator("#audio-source, .rc-audiochallenge-tdownload-link").first.get_attribute("href") or bframe.locator("#audio-source").get_attribute("src")
    if not audio_link:
        return False

    cache_dir = r"C:\Users\Kibe\AppData\Local\hermes\cache"
    os.makedirs(cache_dir, exist_ok=True)
    mp3_path = os.path.join(cache_dir, "recaptcha_temp.mp3")
    wav_path = os.path.join(cache_dir, "recaptcha_temp.wav")

    urllib.request.urlretrieve(audio_link, mp3_path)

    # 6. Convert MP3 -> WAV bằng pydub
    sound = pydub.AudioSegment.from_mp3(mp3_path)
    sound.export(wav_path, format="wav")

    # 7. Nhận diện văn bản giọng nói (Speech Recognition)
    r = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = r.record(source)
        transcribed_text = r.recognize_google(audio_data)

    # 8. Điền kết quả và bấm Xác minh
    inp = bframe.locator("#audio-response")
    inp.fill(transcribed_text)
    time.sleep(1)

    bframe.locator("#recaptcha-verify-button").click()
    time.sleep(4)

    # Dọn dẹp file tạm
    for p in [mp3_path, wav_path]:
        if os.path.exists(p):
            os.remove(p)

    return True
```
