# Zero-Token Autonomous Farm Watchdog Architecture & Repo Applicability

**Date:** 2026-10-16  
**Context:** Taadaa Phone Farm 160 machines (80 Kibe + 80 Admin). User inquired about LLM quota usage and whether unattended background jobs require LLM vision inspection before sending media:
- *"Gửi mấy cái này tốn quota k nhỉ, mỗi lần đổi tên xong phải ép llm đọc ảnh trc khi gửi hả"*
- *"Có ưu tiên áp dụng khi viết script chưa! Còn repo nào khả thi chưa áp dụng k"*
- *"Ưu tiên repo tiktok follow trc. Repo tiktok luot nuoi acc có làm k"*

---

## 1. Dual-Tier Inspection Architecture: Interactive vs Autonomous

| Tier | Role / Trigger | Vision / Inspection Engine | Quota / Token Cost | Delivery Mechanism |
|---|---|---|---|---|
| **Tier 1: Interactive Coordinator** | User chatting directly in Telegram session; investigating bug or anomaly | `browser_vision` (multimodal LLM) + WinRT OCR cross-check | Consumes LLM input/output tokens | Assistant emits `MEDIA:<posix_path>` after verified inspection |
| **Tier 2: Autonomous Cron Watchdog** | Scheduled fleet runner (`no_agent: True`, e.g. `*/5 * * * *`, `*/15 * * * *`) | WinRT OCR Native (`Windows.Media.Ocr` via PowerShell) offline on Windows host CPU | **0 Tokens, 0 Quota, 0 API Calls** (~0.2s - 0.5s per image) | Script prints `MEDIA:<posix_path>` to stdout; Telegram Gateway uploads native photo |

**Key Takeaway:** Unattended background cronjobs must NEVER spawn LLM agents (`no_agent: False`) merely to read tool stdout or inspect screenshots. All mechanical verification must run via WinRT OCR offline scripts, and visual proof is delivered via `MEDIA:<posix_path>` directly to Telegram.

---

## 2. Repo Applicability & Prioritization Matrix

When modernizing Android farm automation workflows from XML hierarchy dumps (`atx-agent` / `uiautomator dump`) to WinRT OCR, prioritize by bottleneck severity:

### Priority 1: High Bottleneck (Mandatory OCR Fast-Path)
1. **`D:/Taadaa/tiktok-follow` (Follow / Nurture Target):**
   - *Problem:* `verify_follow.py` and `mode1_search_follow.py` must check profile action buttons ("Follow", "Follow lại", "Nhắn tin", "Đã follow"). TikTok 46.x frequently renames resource IDs (`id/fds`, `id/ff8`, `id/fij`, `id/fi6`, `id/flo`) or flattens clickable regions into parents. When `atx-agent` dumps hang, retry ladders waste 30-45s per target.
   - *OCR Solution:* Screencap O(1) -> WinRT OCR text boxes in header band (`y < 1200`) -> Direct semantic match ("Nhắn tin" -> `followed`, "Follow" -> `not_followed`). Tapping computes center `(cx, cy)` from the OCR bounding box directly without guessing coordinates.

2. **`D:/Taadaa/Tiktok_Reg` (Account Registration):**
   - *Problem:* Multi-step sequential funnel (birth date, email input, waiting for Outlook OTP, password, username, contact suggestion dismiss). An XML freeze at any intermediate step halts the entire registration pipeline.
   - *OCR Solution:* Fast-path button detection for "Use phone or email", "Email", "Skip", and reading 6-digit OTP codes directly off the screen framebuffer.

3. **`D:/Taadaa/airdrop-automation` (Web3 / Mobile App Tasks):**
   - *Problem:* Security-hardened Web3 apps (Privy, crypto wallets) activate `FLAG_SECURE` or disable accessibility node inspection, resulting in `null root node` or empty XML hierarchies.
   - *OCR Solution:* WinRT OCR reads pixels directly from `adb exec-out screencap -p`, completely bypassing accessibility-tree blocking.

### Low Urgency / Do Not Touch:
4. **`D:/Taadaa/tiktok-luot nuoi acc` (Feed Nurture Session):**
   - *Rationale:* 95% of feed session runtime is hardware input swipes (`input swipe X Y`), natural video dwell times (5-30s), and stochastic like/comment actions.
   - *Policy:* Feed sessions do NOT dump XML on every video swipe. XML is only queried during rare benign popups or initial startup. The feed engine is already lightweight and stable; modifying its core feed loop adds risk without meaningful performance gain.

---

## 3. Implementation Pattern for Consumer Repos

### Step 1: Core OCR Module (`core/ocr.py`)
```python
import subprocess, unicodedata, re
from pathlib import Path
from typing import List, Tuple, Optional

OCR_PS1 = Path(r"D:\Taadaa\tools\ocr_boxes.ps1")

def norm_text(s: str) -> str:
    if not s: return ""
    s = s.replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()

def parse_ocr_boxes_output(raw_stdout: str) -> List[Tuple[str, Tuple[int, int, int, int]]]:
    out = []
    for line in raw_stdout.splitlines():
        line = line.strip()
        if not line or "\t" not in line: continue
        box_str, _, text = line.partition("\t")
        if not text.strip(): continue
        try:
            parts = [int(v.strip()) for v in box_str.split(",")]
            if len(parts) == 4:
                out.append((text.strip(), tuple(parts)))
        except Exception: continue
    out.sort(key=lambda it: ((it[1][1] + it[1][3]) // 40, it[1][0]))
    return out

def ocr_screen_boxes(image_path: str | Path, timeout: float = 30.0) -> List[Tuple[str, Tuple[int, int, int, int]]]:
    if not OCR_PS1.exists(): return []
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(OCR_PS1.resolve()), str(Path(image_path).resolve())],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
        )
        return parse_ocr_boxes_output(r.stdout)
    except Exception: return []
```

### Step 2: Fallback Seam in Verification Flow
Keep the existing XML logic first for backward compatibility and test stability. Only when XML returns `"unknown"` or raises `FollowAdapterError`, invoke the WinRT OCR fast-path to rescue the verification:
```python
cls = classifier(_dump())
if cls == "unknown" or not current_dump:
    ocr_cls = _classify_button_ocr(engine)
    if ocr_cls in ("followed", "not_followed"):
        cls = ocr_cls
```
