# Chuẩn hoá patch Tiktok_Reg — 2026-09-08

Áp dụng 3 fix vào `main` (lint OK, 16/17 tests pass). Dùng làm tài liệu khi revert hoặc cherry-pick.

---

## Fix 1 — `scripts/tiktok_target_eligibility.py` (~line 290)
**Hàm:** `get_registered_mailboxes_from_tracking`  
**Vấn đề:** Workbook tracking thực tế dùng sheet tên "Tài Khoản"; `_active_worksheet` fallback chọn sheet đầu tiên, có thể sai.  
**Patch:**
```python
# TRƯỚC:
worksheet = _active_worksheet(workbook, label)

# SAU:
if "Tài Khoản" in (workbook.sheetnames or []):
    worksheet = workbook["Tài Khoản"]
else:
    worksheet = _active_worksheet(workbook, label)   # fallback đúng cho test (sheet "Accounts")
```

---

## Fix 2 — `social_reg_v1.py` (~line 2904)
**Hàm:** `_try_open_account_dropdown_once`  
**Vấn đề:** Threshold `(x2 - x1) >= 220` bỏ sót display-name nodes width nhỏ hơn 220px trên các máy nhỏ/mật độ cao → dropdown không mở, reg treo.  
**Patch:**
```python
# TRƯỚC: (x2 - x1) >= 220
# SAU:   (x2 - x1) >= 120
```
**Ghi chú:** Filter `"tiểu sử" not in txt.lower()` và `y2 <= 610` giữ nguyên để tránh tap nhầm node "Thêm tiểu sử".

---

## Fix 3 — `social_reg_v1.py` (~line 3000)
**Hàm:** `tap_add_account`  
**Vấn đề:** Khi máy đã đủ 8 tài khoản TikTok, nút "Thêm tài khoản" bị ẩn → hàm raise `RuntimeError` generic, pipeline không phân biệt được "máy đầy" vs lỗi thật.  
**Patch:** Thêm ngay sau `break`, TRƯỚC `save_ui_xml(device_id, "fail_04_add_account")`:
```python
try:
    import xml.etree.ElementTree as _ET
    _xml = get_ui_xml(device_id)
    _root = _ET.fromstring(_xml)
    _acc_count = sum(
        1 for _n in _root.iter("node")
        if "n72" in _n.attrib.get("resource-id", "") or "lkp" in _n.attrib.get("resource-id", "")
    )
    if _acc_count >= 8:
        log(f"   [04_add_account] Máy đã có {_acc_count} tài khoản — đạt giới hạn tối đa 8")
        keyevent(device_id, 4, wait=D_SHORT)   # dismiss dropdown
        keyevent(device_id, 3, wait=0.5)       # go home
        raise RuntimeError("[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok")
except RuntimeError:
    raise
except Exception:
    pass
```
**Resource-ID hint:** `n72` và `lkp` là fragment trong resource-id của account-list nodes TikTok (xác nhận 2026-09-08). Nếu TikTok update app → verify lại bằng `save_ui_xml` khi máy đang ở màn dropdown, tìm node chứa display-name/avatar có `resource-id` chứa fragment mới.

---

## ⚠️ Pre-existing test failure (KHÔNG do patch)
- **Test:** `tests/test_selection_lock_filter.py::test_machine_with_six_accounts_is_skipped`
- **Triệu chứng:** Assert `[target["stt"] for target in targets] == [2]` nhưng nhận `[1, 2]`
- **Nguyên nhân:** Logic skip máy ≥ 6 acc chưa implement ở tầng `detect_targets` / `scripts/tiktok_target_eligibility.py`. File test không bị sửa bởi bất kỳ patch nào.
- **Việc cần làm:** Thêm filter ở `detect_targets` để skip máy có `machine_counts[stt] >= 6` (hoặc threshold cấu hình được).

---

## Quy trình patch chuẩn (dùng lại lần sau)
1. `grep -n '<pattern>' /d/Taadaa/Tiktok_Reg/<file>.py` để xác định offset chính xác
2. `read_file offset=N limit=25` để lấy context đủ để patch unique
3. `patch mode=replace` — dùng old_string đủ dài để unique, không dùng toàn bộ hàm
4. Verify: `python -m pytest tests/ -q --tb=short` → confirm không fail mới
5. **KHÔNG commit/push** trừ khi user yêu cầu
