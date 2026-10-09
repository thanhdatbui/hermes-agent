# GPM Profile CRX Extension Injection & Playwright/CDP Control

## 1. Khi nào sử dụng

- Khi profile GPM cần extension bổ trợ (như VPN extension để fake IP khi thiếu proxy, captcha solver, cookie editor, user-agent spoofer) nhưng:
  - Chrome Web Store UI popup native ("Thêm tiện ích") không bấm được qua CDP / Playwright headless.
  - Cần tự động hoá cài đặt extension mà không cần thao tác tay trên GUI.
  - Cần điều khiển popup/background page của extension qua Playwright CDP.

---

## 2. Quy trình tải và giải nén CRX chuẩn không cần cài tool ngoài

Extension Chrome (`.crx`) thực chất là một file ZIP có thêm header định dạng `Cr24`. Có thể tải trực tiếp từ Google update server qua extension ID và giải nén bằng Python stdlib:

```python
import urllib.request
import zipfile
import struct
import os

def download_and_unpack_crx(ext_id: str, dest_dir: str):
    os.makedirs(dest_dir, exist_ok=True)
    crx_url = (
        f"https://clients2.google.com/service/update2/crx"
        f"?response=redirect&prodversion=120.0&acceptformat=crx2,crx3&x=id%3D{ext_id}%26uc"
    )
    temp_crx = os.path.join(dest_dir, "temp.crx")
    urllib.request.urlretrieve(crx_url, temp_crx)

    with open(temp_crx, "rb") as f:
        data = f.read()

    # Bỏ qua CRX header để lấy dữ liệu ZIP
    if data[:4] == b"Cr24":
        version = struct.unpack("<I", data[4:8])[0]
        if version == 3:
            header_size = struct.unpack("<I", data[8:12])[0]
            zip_data = data[12 + header_size:]
        elif version == 2:
            pk_len = struct.unpack("<I", data[8:12])[0]
            sig_len = struct.unpack("<I", data[12:16])[0]
            zip_data = data[16 + pk_len + sig_len:]
        else:
            raise ValueError(f"Unsupported CRX version: {version}")
    else:
        zip_data = data

    temp_zip = os.path.join(dest_dir, "temp.zip")
    with open(temp_zip, "wb") as f:
        f.write(zip_data)

    with zipfile.ZipFile(temp_zip, "r") as zf:
        zf.extractall(dest_dir)

    os.remove(temp_crx)
    os.remove(temp_zip)
    print(f"Extracted extension {ext_id} to {dest_dir}")
```

---

## 3. Khởi chạy GPM Chrome kèm unpacked extension

Truyền cờ `--load-extension` khi chạy binary Chrome của GPM:

```python
import subprocess

CHROME_EXE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe"
PROFILE_DIR = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\<profile_id>"
EXT_DIR = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\extensions\<ext_name>"

cmd = [
    CHROME_EXE,
    f"--user-data-dir={PROFILE_DIR}",
    f"--load-extension={EXT_DIR}",
    "--remote-debugging-port=49698",
    "--no-first-run",
    "--no-default-browser-check",
]
proc = subprocess.Popen(cmd)
```

---

## 4. Điều khiển Extension UI qua Playwright CDP

Mỗi extension có một panel/popup URL dạng `chrome-extension://<extension_id>/<path_in_manifest>`:

1. Đọc `manifest.json` trong thư mục extension vừa giải nén để tìm file HTML panel (ví dụ: `panel/panel.html` hoặc `popup.html`).
2. Mở page trực tiếp tới URL đó bằng Playwright:
   ```python
   from playwright.sync_api import sync_playwright

   with sync_playwright() as p:
       browser = p.chromium.connect_over_cdp("http://127.0.0.1:49698")
       context = browser.contexts[0]
       ext_page = context.new_page()
       ext_page.goto(f"chrome-extension://{ext_id}/panel/panel.html")
       # Thao tác click/chọn server/connect tự động
       ext_page.click("#connect-button")
   ```

---

## 5. Pitfalls & Lưu ý thực tế

- **VPN Datacenter vs Residential Block:** Một số nền tảng (Meta AI / Muse.ai, TikTok, OpenAI) tích hợp hệ thống phát hiện VPN/Proxy IP Datacenter. Khi dùng VPN extension miễn phí (TouchVPN, SetupVPN...), IP thuộc ASN Datacenter hoặc dính WebRTC leak sẽ bị đưa vào danh sách chờ (Waitlist) hoặc chặn hiển thị ô Redeem Invite Code. Cần ưu tiên Proxy Residential sạch hoặc Cloud Browser native khi gặp tình huống này.
- **Port Conflict:** Khi start Chrome thủ công với remote debugging port, kiểm tra xem port có đang bị chiếm không trước khi bind.
