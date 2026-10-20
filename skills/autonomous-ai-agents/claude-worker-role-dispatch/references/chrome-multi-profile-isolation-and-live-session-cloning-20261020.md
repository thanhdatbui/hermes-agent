# Chrome Multi-Profile Inventory & Live Session Cloning Protocol (2026-10-20)

## Context & User Chrome Profile Map
On this Windows host (`C:\Users\Kibe`), Google Chrome maintains distinct user profiles under `C:\Users\Kibe\AppData\Local\Google\Chrome\User Data`:

| Profile Directory | Display Name | Associated Account | Key Capabilities / Active Cookies |
| :--- | :--- | :--- | :--- |
| `Profile 1` | **a duong** | `thanhdatbui19951@gmail.com` | Google Accounts (`accounts.google.com`), Google Play |
| `Profile 3` | **đạt** | `thanhdatbui1995@gmail.com` | **`.aistudio.google.com`**, **`.gemini.google.com`**, `.antigravity.google`, `.docs.google.com` |
| `Profile 4` | **Kal** | `jinrakal@gmail.com` | Shopee VN, BoxTaiKhoan, Facebook, Personal Shopping |

*Note on GPM Login Clones vs Native Chrome:*
GPM Login profiles with similar names (e.g. `M01 - 5101 - thanhdatbui19951@gmail.com`) are farm clones created for automated batch tasks whose sessions frequently expire. The authoritative, active personal sessions live inside **Google Chrome User Data**, NOT GPM.

---

## The Concurrency Conflict: Chrome Already Running
When background Chrome processes (e.g. PID running with `--no-startup-window /prefetch:5` or minimized windows like `MikroTik Web Manager`) are active:
1. Chrome holds exclusive file locks on `User Data\Lockfile`.
2. Running a new `chrome.exe` command targeting `Profile 1` or `Profile 3` sends an IPC signal to the existing process.
3. Because the existing process was not started with `--remote-debugging-port`, no CDP port opens, rendering automation impossible.
4. **Hard Invariant:** Killing the user's running Chrome is prohibited if it contains active operator tasks (e.g. MikroTik Web Manager).

---

## The Zero-Disruption Session Cloning Pattern

Because Windows DPAPI encrypts cookie encryption keys at the Windows OS user level (`Kibe`), copying `Local State` along with a profile subdirectory allows complete, authenticated decryption on a separate isolated instance:

### Step 1: Clone Profile & Encryption Key
```python
import os, shutil

src_base = r"C:\Users\Kibe\AppData\Local\Google\Chrome\User Data"
dst_base = r"D:\Taadaa\runtime\chrome_isolated_p3"
os.makedirs(os.path.join(dst_base, "Default"), exist_ok=True)

# 1. Copy Local State (contains DPAPI-encrypted master key)
shutil.copy2(os.path.join(src_base, "Local State"), os.path.join(dst_base, "Local State"))

# 2. Copy Profile (skip Cache folders to keep size < 10MB and fast)
p_src = os.path.join(src_base, "Profile 3")  # or Profile 1
ignore = shutil.ignore_patterns("Cache*", "Code Cache*", "DawnCache*", "GPUCache*", "*.tmp")
for item in os.listdir(p_src):
    if "cache" in item.lower():
        continue
    s = os.path.join(p_src, item)
    d = os.path.join(dst_base, "Default", item)
    if os.path.isdir(s):
        shutil.copytree(s, d, ignore=ignore, dirs_exist_ok=True)
    else:
        shutil.copy2(s, d)
```

### Step 2: Launch Isolated Chrome with Custom CDP Port
```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" \
  --remote-debugging-port=9333 \
  --user-data-dir="D:\Taadaa\runtime\chrome_isolated_p3" \
  --no-first-run \
  --no-default-browser-check \
  "https://aistudio.google.com/apikey"
```

### Step 3: Connect via Playwright CDP
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9333")
    page = browser.contexts[0].pages[0]
    # Page opens with full session preserved, no login challenge or 2FA required
```

### Step 4: Teardown Hygiene
Always close the isolated instance after task completion and clean up `D:\Taadaa\runtime\chrome_isolated_*` to free disk and prevent stale cookie divergence.
