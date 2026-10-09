# Khắc Phục Bắt Nhầm GALAXYESSENTIALS Trên Samsung Launcher & Dọn DPAPI Journal

## 1. Hiện Tượng & Nguyên Nhân Gốc (Audit 2026-09-07)
- **Chuỗi ký tự Base32 giả:** Trên các thiết bị Samsung (S7/S8) chạy Samsung Launcher (`com.sec.android.app.launcher`), màn hình chính có widget "Galaxy Essentials".
- Chuỗi `"GALAXYESSENTIALS"` dài đúng 16 ký tự, chỉ gồm ký tự `A-Z`, thỏa mãn chuẩn Base32 (RFC 4648) và sinh được mã TOTP hợp lệ.
- **Kịch bản nhiễm bẩn hàng loạt:** Khi TikTok bị crash hoặc máy rơi về Home Screen, hàm `_base32_candidates()` trong `ui_interact.py` quét toàn bộ XML không lọc `package`, bắt nhầm `"GALAXYESSENTIALS"` làm Secret Key 2FA và lưu vào Journal DPAPI dưới trạng thái `CAPTURED`.
- **Hệ quả kẹt vĩnh viễn:** Khi chạy lại, runner thấy Journal ở state `CAPTURED` nên bỏ qua toàn bộ bước điều hướng TikTok và nhảy cóc thẳng vào `advance_to_otp()`. Tại đây máy đang ở Launcher nên không tìm thấy nút "Tiếp tục" / "Next", văng lỗi `OTP_ADVANCE_BUTTON_NOT_REACHED`. Mọi lần retry đều bị kẹt lặp lại.
- **Kết quả Audit thực tế:** 100% (24/24 máy) file `.dpapi` trong `C:\Users\Kibe\AppData\Local\codex_gmail_debug-tiktok-add-bao-mat-f2a\journals` đều bị nhiễm `secret=GALAXYESSENTIALS`.

---

## 2. Script Python Audit & Purge Journal Lỗi

### Quét kiểm tra trạng thái các file journal:
```python
import sys
from pathlib import Path
sys.path.insert(0, r'D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner')
from core.journal import JournalStore

jdir = Path(r'C:\Users\Kibe\AppData\Local\codex_gmail_debug-tiktok-add-bao-mat-f2a\journals')
store = JournalStore(jdir)
for p in jdir.glob('*.dpapi'):
    try:
        rec = store.load(p.stem)
        print(f'{p.name}: machine={rec.machine} user={rec.username_normalized} row={rec.source_row} state={rec.state} secret={rec.secret}')
    except Exception as e:
        print(f'{p.name}: error {e}')
```

### Xóa triệt để các journal chứa GALAXYESSENTIALS:
```python
import sys
from pathlib import Path
sys.path.insert(0, r'D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner')
from core.journal import JournalStore

jdir = Path(r'C:\Users\Kibe\AppData\Local\codex_gmail_debug-tiktok-add-bao-mat-f2a\journals')
store = JournalStore(jdir)
purged_count = 0
for p in jdir.glob('*.dpapi'):
    try:
        rec = store.load(p.stem)
        if rec.secret == "GALAXYESSENTIALS":
            p.unlink()
            purged_count += 1
            print(f'Purged: {p.name} (Machine {rec.machine}, {rec.username_normalized})')
    except Exception as e:
        print(f'Error reading {p.name}: {e}')
print(f'Total purged: {purged_count}')
```

---

## 3. Khắc Phục Triệt Để Trong Codebase (Hardening)

### A. Trong `python_runner/core/ui_interact.py`:
1. **Lọc nghiêm ngặt package TikTok trong `_base32_candidates()`:**
```python
def _base32_candidates(elements: Iterable[UIElement]) -> list[str]:
    candidates: list[str] = []
    for element in elements:
        pkg = element.attrib.get("package") or getattr(element, "package", None)
        if not pkg and element.resource_id.startswith("com.ss.android.ugc.trill:"):
            pkg = "com.ss.android.ugc.trill"
        if pkg != "com.ss.android.ugc.trill":
            continue
        for value in (element.text, element.content_desc):
            compact = "".join(value.upper().split()).replace("-", "")
            if compact == "GALAXYESSENTIALS":
                continue
            if not re.fullmatch(r"[A-Z2-7]{16,64}", compact):
                continue
            try:
                generate_totp(compact, timestamp=0)
            except ValueError:
                continue
            candidates.append(compact)
    return list(dict.fromkeys(candidates))
```

2. **Chặn fail-closed trong `read_secret_node()`:**
```python
def read_secret_node(xml_text: str) -> str:
    if "com.ss.android.ugc.trill" not in xml_text:
        raise UIInteractError("current UI is not TikTok")
    elements = list(iter_elements(parse_xml(xml_text)))
    evidence_nodes = [
        element for element in elements
        if element.resource_id == F2ASelector.SECRET_VALUE.value
    ]
    candidates = _base32_candidates(evidence_nodes)
    if not candidates and not evidence_nodes:
        candidates = _base32_candidates(elements)
    if len(candidates) != 1:
        raise UIInteractError(f"expected one Base32 secret, found {len(candidates)}")
    return candidates[0]
```

### B. Trong `python_runner/core/live_phase_b_adapter.py`:
1. **Kiểm tra màn hình Launcher & phục hồi TikTok trong `navigate_and_verify_account()`:**
```python
    is_launcher = (
        "com.sec.android.app.launcher" in current
        or "com.google.android.apps.nexuslauncher" in current
        or "launcher" in current.lower()
    )
    if is_launcher or "com.ss.android.ugc.trill" not in current:
        if not fresh_prepared:
            self._prepare_fresh_tiktok()
            fresh_prepared = True
        try:
            self._back_to_profile()
        except LiveAdapterError:
            self._open_profile_tab()
        current = self._dump_preflight()

    # Chỉ thử đọc secret node khi chắc chắn UI thuộc TikTok
    if "com.ss.android.ugc.trill" in current:
        try:
            read_secret_node(current)
        except UIInteractError:
            pass
        else:
            self._resume_key_screen = True
            return
```

### C. Lưu ý Unit Test:
- Khi `read_secret_node()` bắt buộc `"com.ss.android.ugc.trill" in xml_text`, các fixture XML trong `test_ui_interact.py` và `test_live_phase_b_adapter.py` cần có `package="com.ss.android.ugc.trill"` hoặc `resource-id="com.ss.android.ugc.trill:id/..."` để vượt qua bộ lọc fail-closed.
