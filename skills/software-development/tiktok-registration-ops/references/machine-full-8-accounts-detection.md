# Machine-Full 8-Account Detection in Tiktok_Reg

**Context:** `social_reg_v1.py` — Step 4 (`tap_add_account`). When a machine already holds 8 TikTok accounts the dropdown opens but shows NO "Thêm tài khoản" button, causing a misleading `[04_add_account]` RuntimeError.

---

## 1. XML Evidence (from `fail_04_add_account_012059.xml`)

When a machine is full the account-switcher XML contains exactly 8 nodes with:
```
resource-id="com.ss.android.ugc.trill:id/n72"
```
Each node's `text` is a TikTok username (e.g. `anderyepax4`, `ninhy05100`, …). The "Thêm tài khoản" text node is **absent**.

Sample layout bounds (portrait 1080×1920):
```
bounds="[252,354][559,414]"   → row-1
bounds="[252,570][535,630]"   → row-2
bounds="[252,786][652,846]"   → row-3
...
bounds="[252,1866][561,1920]" → row-8  (bottom; sometimes clipped)
```

---

## 2. Detection Snippet

Insert **before** the final `raise RuntimeError` in `tap_add_account()`:

```python
import xml.etree.ElementTree as _ET
_xml = get_ui_xml(device_id)
try:
    _root = _ET.fromstring(_xml)
    _acc_count = sum(
        1 for _n in _root.iter("node")
        if "n72" in _n.attrib.get("resource-id", "")
    )
    if _acc_count >= 8:
        log(f"   [04_add_account] Máy đã có {_acc_count} tài khoản — đạt giới hạn tối đa 8")
        keyevent(device_id, 4, wait=D_SHORT)  # dismiss dropdown
        keyevent(device_id, 3, wait=0.5)      # KEYCODE_HOME
        raise RuntimeError(
            "[04_add_account] MACHINE_FULL_8_ACCOUNTS: "
            "Thiết bị đã đạt giới hạn 8 tài khoản TikTok"
        )
except RuntimeError:
    raise
except Exception:
    pass  # fail-open: let the original error surface below
```

The caller (`_run_all_targets.py` or equivalent) should catch `MACHINE_FULL_8_ACCOUNTS` and **skip** that device for the rest of the batch — it is not a retryable failure.

---

## 3. Upstream eligibility guard (`tiktok_target_eligibility.py`)

`load_registered_mailboxes()` already counts `machine_counts[m]` and `select_pending_targets()` skips any machine where `counts.get(stt, 0) >= 8`.

**Bug:** `_active_worksheet()` uses the workbook's last-saved active sheet. If the tracking workbook has multiple sheets and the active one is a summary/pivot, the count is wrong.

**Fix:**
```python
# In load_registered_mailboxes(), after opening the workbook:
PREFERRED_SHEET = "Tài Khoản"
if PREFERRED_SHEET in (workbook.sheetnames or []):
    worksheet = workbook[PREFERRED_SHEET]
else:
    worksheet = _active_worksheet(workbook, label)
```

---

## 4. Display-name width threshold bug (`social_reg_v1.py` Pass 4)

Line ~2904:
```python
if txt and not txt.startswith("@") and (x2 - x1) >= 220 and y2 <= 610 …
```
Short display names like `"Hà"`, `"An"`, `"Mai"` render with width ≈ 100–180 px and are silently skipped, causing dropdown-open to fall through all passes and retry unnecessarily.

**Fix:** lower threshold to `>= 120` (still wide enough to exclude narrow icon-buttons):
```python
if txt and not txt.startswith("@") and (x2 - x1) >= 120 and y2 <= 610 …
```

---

## 5. `rid='n72'` as account-row sentinel

Confirmed stable across two firmware builds (2026-09 runs). If TikTok updates and `n72` disappears, fall back to counting nodes whose `bounds` y1 >= 300 and y2 <= 1900 and `text` is a non-empty, non-@ string inside the open dropdown sheet.
