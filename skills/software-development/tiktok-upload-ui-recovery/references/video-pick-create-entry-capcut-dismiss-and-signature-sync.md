# Bounded Create-Entry Recovery: CapCut Template Dismiss Navigation & Signature Sync

## 1. Hiện Tượng & Mã Lỗi
- **Mã lỗi:** `[MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Picker was not verified after the bounded create-entry recovery`
- **Quy trình:** Đăng video (`Tiktok-video` / `scripts/tiktok_workflow/run_post.py` & `state_machine.py`).
- **Triệu chứng hiện trường:**
  1. Khi bấm nút Tạo (+) để vào Camera, giao diện mẫu CapCut (template/hub) xuất hiện thay vì Media Picker.
  2. Hàm `_dismiss_capcut_template_surface` bấm nút thoát/back (tọa độ `84, 150` / id `bq3`), đưa app về màn hình **Hồ sơ cá nhân (Profile)** hoặc **Trang chủ (Feed)** thay vì giữ lại camera surface.
  3. `_is_camera_surface_xml` kiểm tra thấy không còn là Camera, khiến `_tap_visual_camera_upload_entry` trả về `False` để luồng ngoài xử lý.
  4. Quá trình bounded create-entry recovery cố gắng recapture nhưng thất bại, kích hoạt `_maybe_soft_reboot_recovery()`.
  5. Quá trình soft reboot timeout proxy readiness (`proxy readiness timed out for <serial>`) dẫn đến lỗi kết thúc phiên `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`.

---

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)

### A. Lệch điều hướng khi thoát CapCut Template (`state_machine.py`)
- Khi dismiss template surface ở đầu hàm hoặc trong vòng lặp visual thumbnail, app rơi về màn hình Profile hoặc Feed root.
- Màn hình này không còn là Camera (`_is_camera_surface_xml` trả về `False`), nhưng có hiển thị thanh điều hướng đáy (Bottom Navigation Bar) chứa nút Tạo (+) ở giữa (`[432,1794][648,1920]`, `content-desc="Quay"` hoặc `"Tạo"` / `id="oea"`).
- Nếu không phát hiện và bấm lại nút Tạo (+) này để mở lại Camera / Media Picker, flow sẽ lập tức `return False` và chuyển sang soft reboot không cần thiết.

### B. Lệch chữ ký Recovery giữa Checkpoint và Handoff Ledger (`run_post.py`)
- Trong `run_post.py`, hàm `_load_video_pick_recovery_binding`:
  - Tại dòng ~788: kiểm tra checkpoint chỉ chấp nhận signature `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` (hoặc `VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET`).
  - Tại dòng ~872–886: tầng Handoff Ledger lại kiểm tra cứng:
    ```python
    and str(item.get("candidate_signature") or "") == "VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET"
    ...
    if str(handoff.get("recapture_signature") or "").strip() != "VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET":
    ```
  - Khi luồng recovery chạy với chữ ký `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`, ledger reject với lỗi `VIDEO_PICK_RECOVERY_SOL_HANDOFF_MISSING` hoặc `VIDEO_PICK_RECOVERY_RECAPTURE_SIGNATURE_MISSING`.

---

## 3. Giải Pháp Khắc Phục (Canonical Fix)

### 1. Phục hồi điều hướng sau khi dismiss CapCut (`state_machine.py`)
Ngay sau khi `_dismiss_capcut_template_surface` trả về `True`, nếu màn hình hiện tại không còn là Camera (`not self._is_camera_surface_xml(xml_text)`):
```python
if not self._is_camera_surface_xml(xml_text):
    create_btn = self._find_bounded_create_button(xml_text)
    if create_btn and create_btn.get("center"):
        logger.info(
            "[CAMERA] Sau khi dismiss template ở đầu hàm rơi về feed/profile; tap lại create button để vào lại camera"
        )
        adapter.tap(*create_btn["center"])
        time.sleep(2)
        try:
            xml_text = adapter.dump_ui()
        except Exception:
            xml_text = ""
```

### 2. Đồng bộ chữ ký Recovery trong Handoff Ledger (`run_post.py`)
Khai báo tập chữ ký hợp lệ dùng chung cho cả kiểm tra checkpoint và handoff ledger:
```python
valid_pick_signatures = (
    "VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET",
    "VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED",
)

# Tại dòng ~784-790:
if (
    str(report.get("status") or "").casefold() != "manual_review"
    or str(prior_recovery.get("state") or "") != "FINAL_BLOCKED"
    or str(prior_recovery.get("signature") or "") not in valid_pick_signatures
):
    raise ValueError("VIDEO_PICK_RECOVERY_PRIOR_RUN_NOT_TERMINAL_PICK_FAILURE")

# Tại dòng ~866-887:
matching = [
    item
    for item in handoffs
    if isinstance(item, dict)
    and str(item.get("machine") or "").strip() == str(machine).strip()
    and str(item.get("target_id") or "").strip() == str(device_id).strip()
    and str(item.get("candidate_signature") or "") in valid_pick_signatures
]
...
if str(handoff.get("recapture_signature") or "").strip() not in valid_pick_signatures:
    raise ValueError("VIDEO_PICK_RECOVERY_RECAPTURE_SIGNATURE_MISSING")
```

---

## 4. Quy Trình Kiểm Chứng (Canary Verification)
1. Kiểm tra cú pháp:
   ```bash
   python -m py_compile scripts/tiktok_workflow/run_post.py scripts/tiktok_workflow/state_machine.py
   ```
2. Chạy focused pytest:
   ```bash
   pytest tests/test_tiktok_workflow.py -k "video_pick_recovery or recovery_binding"
   ```
3. Chạy Canary trên máy thật:
   ```bash
   cd /d D:/Taadaa/Tiktok-video && env -u PYTHONPATH python -m scripts.tiktok_workflow --config "D:\Taadaa\Tiktok-video\config.example.yaml" --workflow-workbook "D:\OneDrive\TaadaaData\kibe\Tik2.xlsx" --single-device <SERIAL> --video-number <N> --no-dry-run
   ```
