# Benign Popup Registry: AI Info Bottom Sheet & Dual-Path Dispatch Patterns

## Architecture & Integration
In `tiktok-luot nuoi acc/python_runner`:
- `flows/benign_popup_registry.py` maintains `BENIGN_POPUP_REGISTRY` with `RegistryEntry(name, priority, detector, dismisser, enabled, source)`.
- `flows/benign_popup.py` executes registry-first dispatch via `find_matching_handler(xml_content, ocr_text)` inside `dismiss_any_popup` and `dismiss_shared_benign_popup`.
- Registry dispatch invokes `matching_entry.dismisser(ctx)`.

### Handler Signature Pattern
To support both registry dispatch and direct function invocation:
```python
def _detect_popup_name(xml_content: str = "", ocr_text: str = "") -> bool:
    ...

def _dismiss_popup_name(ctx: Any, xml_content: str = "", ocr_text: str = "") -> PopupDismissResult:
    ...
```
Defaulting `xml_content` and `ocr_text` ensures `dismisser(ctx)` works seamlessly without `TypeError`.

## Pitfall: `PopupDismissResult` Dataclass Instantiation
In `flows/benign_popup.py`, `PopupDismissResult` is defined as a `@dataclass(frozen=True)`:
```python
@dataclass(frozen=True)
class PopupDismissResult:
    dismissed: bool
    reason: str
    before_attempt: dict[str, Any]  # Note: missing default factory
    after_attempt: dict[str, Any] | None = None
    ...
    popup_closed: bool = False
```
- **Pitfall**: Instantiating with `PopupDismissResult(dismissed=True, reason="...", popup_closed=True)` without `before_attempt` raises:
  `TypeError: PopupDismissResult.__init__() missing 1 required positional argument: 'before_attempt'`.
- **Fix**: Update `before_attempt: dict[str, Any] = field(default_factory=dict)` or explicitly pass `before_attempt={}` or `before_attempt={"action": "..."}`.

## TikTok AI Info Bottom Sheet ("Thông tin về AI")
Appears when users view videos tagged with AI disclosures.

### Detection Keywords (case-insensitive)
- Vietnamese: `"thông tin về ai"`, `"bài đăng được nhà sáng tạo gắn nhãn"`, `"chỉnh sửa bằng ai"`, `"nội dung này được tạo hoặc chỉnh sửa bằng ai"`
- English fallbacks: `"ai-generated"`, `"ai info"`, `"creator labeled"`

### Dismiss Strategy
1. XML node inspection: look for close icon (`✕`), content-desc / text matching `Đóng`, `Close`, `Quay lại`, `Back`.
2. If found: tap center coordinates via `_perform_click_target(ctx, (cx, cy))`.
3. If node not found: fallback to clicking outside bottom sheet (upper half of screen) or sending `KEYCODE_BACK` (`input keyevent 4`) with `time.sleep(0.8)`.
4. Registry registration: Priority `68` (below `rewards_virtual_items_policy_dialog` at 69).

## Windows Cross-Drive & MSYS Path Pitfalls
1. **MSYS vs Native Windows Python Paths**:
   When invoking native Windows Python (`python -m py_compile ...` or `python script.py`) from Git Bash, passing MSYS POSIX paths like `"/d/Taadaa/..."` fails with:
   ```
   [Errno 2] No such file or directory: '/d/Taadaa/...'
   ```
   Always use Windows drive syntax (e.g. `"D:/Taadaa/..."` or `D:\Taadaa\...`) or `cd` to the directory first.

2. **Cross-Drive Unit Test Execution**:
   When running Python `unittest` on Windows from `C:` drive pointing to a test file on `D:` drive:
   ```bash
   python -m unittest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_foo.py"
   ```
   Python raises:
   ```
   ValueError: path is on mount 'D:', start on mount 'C:'
   ```
   **Correct Pattern**: Always change working directory to the target repo drive/path first:
   ```bash
   cd "/d/Taadaa/tiktok-luot nuoi acc/python_runner" && python -m unittest tests/test_foo.py
   ```
