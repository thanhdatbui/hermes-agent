# Xử Lý Lỗi VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED, Handoff Signature Mismatch, CapCut Dismiss Navigation Fallback & SurfaceFlinger Protected Screencap (Case 87)

Tài liệu này đúc kết nguyên nhân kỹ thuật và giải pháp chuẩn cho sự cố `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]` trong quy trình Đăng Video TikTok (`Tiktok-video`) trên hệ thống farm Samsung Galaxy S7 (06/09/2026).

---

## 1. BỐI CẢNH & HIỆN TƯỢNG SỰ CỐ (MÁY 27)

- **Thiết bị:** Máy 27 | Serial: `ce031823912ae0d20c` | Nick: `hoangvy5328` | Workbook: `Tik2.xlsx`
- **Quy trình:** Đăng Video (`scripts/tiktok_workflow/run_post.py`)
- **Triệu chứng:**
  ```text
  🚨 [FARM ALERT: MÁY 27] DỪNG PHIÊN
  • Triệu chứng: [MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Picker was not verified after the bounded create-entry recovery
  • Hiện trường: GIỮ HIỆN TRƯỜNG UPLOAD
  ```
- **Log run:** `D:/CodexRuntime/tiktok-video/runs/run_ce031823912ae0d20c_20260906_043033/execution.log`

---

## 2. NGUYÊN NHÂN CỐT LÕI (ROOT CAUSE ANALYSIS)

### 2.1. Signature Mismatch Tại Ledger Handoff (`run_post.py`)
- **Cơ chế:** Khi flow video pick gặp lỗi, checkpoint lưu chữ ký:
  ```json
  "video_pick_recovery": {
    "state": "FINAL_BLOCKED",
    "signature": "VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED"
  }
  ```
- **Lỗi:** Trong `_load_video_pick_recovery_binding` của `run_post.py`, hàm kiểm tra prior checkpoint:
  ```python
  if str(prior_recovery.get("signature") or "") != "VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED":
      raise ValueError("VIDEO_PICK_RECOVERY_PRIOR_RUN_NOT_TERMINAL_PICK_FAILURE")
  ```
  Nhưng ở tầng so khớp ledger handoff (`matching` và `recapture_signature`), code lại hardcode cứng:
  ```python
  and str(item.get("candidate_signature") or "") == "VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET"
  ...
  if str(handoff.get("recapture_signature") or "").strip() != "VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET":
      raise ValueError("VIDEO_PICK_RECOVERY_RECAPTURE_SIGNATURE_MISSING")
  ```
- **Hậu quả:** Khi runner được gọi lại qua cờ `--video-pick-recovery-from`, handoff ledger từ chối kích hoạt vì chữ ký không khớp, gây crash `VIDEO_PICK_RECOVERY_SOL_HANDOFF_MISSING`.

### 2.2. CapCut Template Dismiss Navigation Fallback (`state_machine.py`)
- **Cơ chế:** Khi camera TikTok mở và xuất hiện màn hình CapCut template/hub ("Video mới", "Mẫu", "AutoCut"), hàm `_dismiss_capcut_template_surface` tap nút đóng top-left (`bq3` / `h32` tại toạ độ `(84, 150)`).
- **Lỗi:** Trên một số bản cập nhật TikTok, việc dismiss template không đưa app trở lại Camera Surface mà đẩy rơi về màn hình Profile cá nhân (`@hoangvy5328`) hoặc Home Feed.
- **Hậu quả:** Khi quay lại `_tap_visual_camera_upload_entry`, điều kiện `_is_camera_surface_xml(xml_text)` phát hiện các Profile root markers (`Ảnh hồ sơ`, `com.ss.android.ugc.trill:id/blk`, `Sửa hồ sơ`) và trả về `False`. Hàm lập tức abort với log:
  ```text
  [CAMERA] Sau khi dismiss template ở đầu hàm không còn là camera surface
  ```
  Đẩy flow sang nhánh soft reboot recovery, dẫn đến timeout proxy watcher và kết thúc bằng `MANUAL_REVIEW`.

### 2.3. Hiện Tượng SurfaceFlinger Protected Screencap Zero-Bytes
- **Hiện tượng:** Khi TikTok đang mở camera ở chế độ LIVE hoặc màn hình hiệu ứng đặc biệt, lệnh `adb exec-out screencap -p` hoặc `adb shell screencap -p /sdcard/...` tạo ra file PNG có kích thước đúng **12 bytes**:
  ```python
  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
  ```
- **Logcat hệ điều hành Android:**
  ```text
  SurfaceFlinger: FB is protected: PERMISSION_DENIED
  ```
- **Hậu quả:** Khi `PIL.Image.open(screenshot)` được gọi để tính toán độ sáng thumbnail (`non_dark_r`, `non_dark_l`), PIL raise `UnidentifiedImageError: cannot identify image file`.
- **Bản chất:** Đây là cơ chế bảo vệ phần cứng SurfaceView / DRM của Android khi SurfaceFlinger chặn chụp frame buffer của camera phần cứng. Khi đóng app TikTok hoặc đưa về Home Feed thông thường, lệnh `screencap` hoạt động bình thường trở lại (file size ~750KB).

---

## 3. GIẢI PHÁP CHUẨN (CASE FIX 87)

### 3.1. Đồng Bộ Hóa Signature Trong `run_post.py`
Mở rộng danh sách chữ ký hợp lệ thành tuple và dùng toán tử `in` / `not in`:

```python
valid_pick_signatures = (
    "VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET",
    "VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED",
)

# 1. Prior recovery check
if (
    str(report.get("status") or "").casefold() != "manual_review"
    or str(prior_recovery.get("state") or "") != "FINAL_BLOCKED"
    or str(prior_recovery.get("signature") or "") not in valid_pick_signatures
):
    raise ValueError("VIDEO_PICK_RECOVERY_PRIOR_RUN_NOT_TERMINAL_PICK_FAILURE")

# 2. Handoff ledger candidate matching
matching = [
    item
    for item in handoffs
    if isinstance(item, dict)
    and str(item.get("machine") or "").strip() == str(machine).strip()
    and str(item.get("target_id") or "").strip() == str(device_id).strip()
    and str(item.get("candidate_signature") or "") in valid_pick_signatures
]

# 3. Recapture signature verification
if str(handoff.get("recapture_signature") or "").strip() not in valid_pick_signatures:
    raise ValueError("VIDEO_PICK_RECOVERY_RECAPTURE_SIGNATURE_MISSING")
```

### 3.2. Điều Hướng Fallback Tạo Lại Camera Trong `state_machine.py`
Sau khi gọi `_dismiss_capcut_template_surface`, nếu màn hình không còn là camera surface, kiểm tra xem nút Tạo (+) ở thanh điều hướng đáy (`_find_bounded_create_button`) có xuất hiện hay không. Nếu có, tap lại nút Tạo (+) để mở lại Camera / Media Picker thay vì thoát thất bại:

```python
if self._dismiss_capcut_template_surface(adapter, xml_text):
    time.sleep(1)
    try:
        xml_text = adapter.dump_ui()
    except Exception:
        xml_text = ""
    if not self._is_camera_surface_xml(xml_text):
        create_btn = self._find_bounded_create_button(xml_text)
        if create_btn and create_btn.get("center"):
            logger.info(
                "[CAMERA] Sau khi dismiss template rơi về feed/profile; tap lại create button để vào lại camera"
            )
            adapter.tap(*create_btn["center"])
            time.sleep(2)
            try:
                xml_text = adapter.dump_ui()
            except Exception:
                xml_text = ""
    if not self._is_camera_surface_xml(xml_text):
        logger.warning("[CAMERA] Sau khi dismiss template màn hình không còn là camera surface")
        return False
```

*(Áp dụng đồng bộ ở cả 2 vị trí: đầu hàm `_tap_visual_camera_upload_entry` và bên trong vòng lặp retry).*

### 3.3. Tối Ưu Thứ Tự Thumbnail Candidates (Left-First Priority)
Trên các máy Samsung, thumbnail thư viện nằm ở bên trái hoặc dưới cùng bên trái. Sắp xếp danh sách candidates theo thứ tự ưu tiên:
```python
left_targets = []
if non_dark_l >= 0.20:
    left_targets.append(("L", (int(width * 0.145), int(height * 0.82)), non_dark_l))
if non_dark_bl >= 0.20:
    left_targets.append(("BL", (int(width * 0.11), int(height * 0.95)), non_dark_bl))
left_targets.sort(key=lambda item: item[2], reverse=True)

right_targets = []
if non_dark_r >= 0.20:
    right_targets.append(("R", (int(width * 0.875), int(height * 0.83)), non_dark_r))

ordered_candidates = left_targets + right_targets
```

---

## 4. QUY TRÌNH KIỂM CHỨNG & CANARY AN TOÀN

1. **Syntax Check:** `python -m py_compile scripts/tiktok_workflow/run_post.py scripts/tiktok_workflow/state_machine.py`
2. **Focused Tests:**
   ```bash
   pytest tests/test_tiktok_workflow.py -k "test_tap_visual_camera_upload_entry or video_pick_recovery or recovery_binding or LIVE"
   ```
3. **Live Canary Command (Máy Target):**
   ```bash
   cd /d D:/Taadaa/Tiktok-video && env -u PYTHONPATH python -m scripts.tiktok_workflow --config "D:\Taadaa\Tiktok-video\config.example.yaml" --workflow-workbook "D:\OneDrive\TaadaaData\kibe\Tik2.xlsx" --single-device <SERIAL> --video-number <N> --no-dry-run
   ```
4. **Fail-Safe Cleanup:** Luôn bảo đảm đưa app về Home (`am force-stop` + `input keyevent 3`) sau khi hoàn thành hoặc khi xảy ra ngoại lệ, nhả device lock sạch sẽ.
