# Benign Popup Registry Extension Pattern & Invariants

## 1. Registry Architecture (`python_runner/flows/benign_popup_registry.py`)
Mọi popup thông báo lành tính (benign popups) xuất hiện trong lúc lướt TikTok feed hoặc chuẩn bị thiết bị cần được xử lý tập trung trong `benign_popup_registry.py`.

### Registration Contract
Mỗi popup được đăng ký qua:
```python
register_popup_handler(
    RegistryEntry(
        name="<popup_name>",
        priority=89,  # 1..100 (Higher runs first)
        detector=_detect_<popup_name>,
        dismisser=_dismiss_<popup_name>,
        enabled=True,
        source="manual",
    )
)
```

### Priority Scale
- `95-98`: Lỗi tài khoản, uiautomator overlay, văng app, activity unavailable.
- `90-94`: Camera creation overlay, permission prompts, voucher dialogs.
- `85-89`: Chính sách phần thưởng, điều khoản, tutorial swipe up, policy dialogs (ví dụ: `rewards_virtual_items_policy_dialog` priority 89, `swipe_up_tutorial_overlay` 89, `tiktok_rewards_terms_overlay` 88).
- `70-84`: Video options, shop details, search landing, live room overlay, ad feedback survey dialogs (e.g. `tiktok_ad_feedback_survey` priority 75).

## 1.1 Case Đặc Thù: Ad Feedback Survey Dialog / Overlay
- **Màn hình:** Video tài trợ (sponsored ad) hiển thị thanh/bảng hỏi: *"Bạn có quan tâm đến quảng..."* kèm 2 lựa chọn `[Không]` / `[Có]` (hoặc `[No]` / `[Yes]`).
- **Hiện tượng lỗi gốc:** Bị allowlist core từ chối vì thiếu marker hoặc resource-id lạ $\rightarrow$ `popup is not in the shared TikTok allowlist; manual review required`.
- **Cơ chế xử lý 2 lớp (`tiktok_ad_feedback_survey`):**
  1. *Detector:* Bắt các chuỗi *"bạn có quan tâm đến quảng"*, *"quan tâm đến quảng cáo"*, *"interested in this ad"*, hoặc ngữ cảnh hỏi quảng cáo kèm các nút `No`/`Không`/`Yes`/`Có`.
  2. *Dismisser:* Tìm nút `Không`/`No` hoặc nút đóng `✕`/`Close` trong UI XML để tap. Nếu không tìm thấy, thực hiện swipe-up có kiểm soát (`swipe 540 1400 540 500 300`) lướt qua video ad. Luôn truyền `before_attempt={"screen": "tiktok_ad_feedback_survey"}` vào `PopupDismissResult`.

## 2. Detector Pattern
Detector nhận `(xml_content: str = "", ocr_text: str = "") -> bool`:
```python
def _detect_<name>(xml_content: str = "", ocr_text: str = "") -> bool:
    combined = ((xml_content or "") + " " + (ocr_text or "")).lower()
    has_target = ("chính sách phần thưởng" in combined or "chính sách vật phẩm ảo" in combined)
    has_btn = ("đã hiểu" in combined or "got it" in combined)
    return has_target and has_btn
```
- Luôn kiểm tra cả biến thể có dấu và không dấu nếu cần.

## 3. Dismisser Pattern & `PopupDismissResult` Invariant
### ⚠️ BẮT BUỘC: `before_attempt` trong `PopupDismissResult`
Trong `python_runner/flows/benign_popup.py`:
`PopupDismissResult` là `@dataclass(frozen=True)` có định nghĩa:
```python
class PopupDismissResult:
    dismissed: bool
    reason: str
    before_attempt: dict[str, Any]  # <-- KHÔNG CÓ GIÁ TRỊ MẶC ĐỊNH
    after_attempt: dict[str, Any] | None = None
    selector: dict[str, Any] | None = None
    ...
    popup_closed: bool = False
```
**Bẫy lỗi:** Nếu khởi tạo `PopupDismissResult(dismissed=True, reason="...", popup_closed=True)` mà bỏ qua `before_attempt`, Python sẽ ném ngoại lệ:
`TypeError: missing 1 required positional argument: 'before_attempt'`.
BẮT BUỘC luôn truyền: `before_attempt={"action": "..."}` hoặc `before_attempt={}`.

### Cấu trúc chuẩn của Dismisser
```python
def _dismiss_<name>(ctx: Any) -> PopupDismissResult:
    from .benign_popup import PopupDismissResult
    before_state = {"action": "dismiss_<name>"}
    xml_str = _safe_capture_hierarchy(ctx)
    target_pt = None
    if xml_str:
        from automation_core.ui import parse_xml, iter_elements, parse_bounds
        try:
            xml_tree = parse_xml(xml_str)
            for el in iter_elements(xml_tree):
                t = (getattr(el, "text", "") or (el.attrib.get("text") if hasattr(el, "attrib") else "") or "").strip().lower()
                d = (getattr(el, "content_desc", "") or (el.attrib.get("content-desc") if hasattr(el, "attrib") else "") or "").strip().lower()
                if t in ("đã hiểu", "got it") or d in ("đã hiểu", "got it"):
                    bounds_val = getattr(el, "bounds", None) or (el.attrib.get("bounds") if hasattr(el, "attrib") else None)
                    if isinstance(bounds_val, (tuple, list)) and len(bounds_val) == 4:
                        target_pt = ((bounds_val[0] + bounds_val[2]) // 2, (bounds_val[1] + bounds_val[3]) // 2)
                        break
                    elif isinstance(bounds_val, str):
                        parsed_b = parse_bounds(bounds_val)
                        if parsed_b:
                            target_pt = ((parsed_b[0] + parsed_b[2]) // 2, (parsed_b[1] + parsed_b[3]) // 2)
                            break
        except Exception:
            pass

    if target_pt is not None:
        _perform_click_target(ctx, target_pt)
        time.sleep(0.8)
        return PopupDismissResult(
            dismissed=True,
            reason="clicked_da_hieu_rewards_policy",
            before_attempt=before_state,
            popup_closed=True,
        )

    return PopupDismissResult(
        dismissed=False,
        reason="<name>_target_not_found",
        before_attempt=before_state,
        popup_closed=False,
    )
```
- Dùng `_perform_click_target(ctx, target_pt)` có sẵn trong `benign_popup_registry.py` để tự động route qua `ctx.tap`, `ctx.adb.shell`, hoặc `ctx.actions.tap`.

## 4. Canary Test Verification
Sau khi sửa file, chạy cú pháp compile và Canary test:
```bash
python -m py_compile "D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/benign_popup_registry.py"
```
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <ID> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
Tuyệt đối KHÔNG tap ADB thủ công trong quá trình test; để script tự xử lý và xác nhận số swipe thành công.
