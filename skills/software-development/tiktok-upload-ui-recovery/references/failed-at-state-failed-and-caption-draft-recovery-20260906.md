# FSM State Obfuscation (failed_at_state_FAILED), Floating Context Toolbar & Non-Fatal Draft Cleanup (2026-09-06)

## 1. Hiện Tượng & Triệu Chứng Lỗi (Máy 74 - ce061606c21e153d03)
- **Alert Farm:** `[FARM ALERT: MÁY 74] DỪNG PHIÊN - Quy trình: Đăng Video (Tiktok-video) - Triệu chứng: failed_at_state_FAILED`.
- **Màn hình hiện trường:** Đang ở màn hình soạn thảo TikTok (Composer / Caption area). Ô nhập caption hiển thị `#cafevietnamcafevietnamcafe` bị bôi đen toàn bộ (select all). Menu ngữ cảnh nổi Samsung (`CẮT | CHÉP | DÁN | BỘ NHỚ TẠM`) đè lên màn hình, thanh gợi ý hashtag và bàn phím ảo mở, nút "Đăng" ở góc trên bên phải đã hiển thị.
- **Log `report.json`:**
  ```json
  {
    "status": "FAILED",
    "device_id": "ce061606c21e153d03",
    "error": null,
    "last_state": "FAILED"
  }
  ```

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Causes)

### 2.1. Lỗi Che Lấp State FSM (`failed_at_state_FAILED`)
- **Trong `state_machine.py` (`_transition`):** Khi một handler (ví dụ `CAPTION_FILL`) thất bại qua cả 3 lần retry, hàm `_transition(False)` gán trực tiếp `self.current_state = fail_state` (`WorkflowState.FAILED`).
- **Trong `run_post.py`:** Khi workflow fail, reporter lấy trực tiếp `machine.current_state.value` ghi vào `last_state` của `report.json`.
- **Hệ quả:** Do `current_state` đã bị biến thành `FAILED` và `context.error` là `None`, tầng watchdog/giám sát bên ngoài fallback sinh chuỗi `f"failed_at_state_{last_state}"` $\rightarrow$ sinh ra mã lỗi **`failed_at_state_FAILED`**, làm lu mờ hoàn toàn state thực tế bị hỏng (`CAPTION_FILL`).

### 2.2. Kẹt Menu Ngữ Cảnh Floating Toolbar ("CẮT | CHÉP | DÁN") & Hashtag Verification
- Khi gõ hashtag bằng `input text` trên Android Samsung S7, lệnh ADB input text có thể bị timeout hoặc dính text lặp (`#cafevietnamcafevietnamcafe`).
- Khi fallback sang long-press ô caption để paste, trên Android Samsung nếu ô nhập ĐÃ CÓ CHỮ, long-press sẽ kích hoạt tính năng Select All của hệ thống, làm bật Floating Action Mode toolbar: `CẮT | CHÉP | DÁN | BỘ NHỚ TẠM`.
- Các nút trên Floating Toolbar thường mang nhãn trong thuộc tính `content-desc` (hoặc viết HOA toàn bộ: `DÁN`), nên selector chỉ tìm theo `text` sẽ không bắt được nút "Dán".
- Thao tác verify caption yêu cầu `all(tag in normalized_visible for tag in hashtags)`: Trên TikTok, các hashtag có thể tự co lại thành chip/pill hoặc bị cuộn ngang, khiến điều kiện `all(...)` trả về `False` dù caption đã có mặt.

### 2.3. Bẫy Draft Cleanup Fatal (`[DRAFT_CLEANUP_FAILED]`)
- Khi vào state `ACCOUNT_READY`, nếu profile có bản nháp cũ, script gọi `_delete_all_profile_drafts`.
- Khi màn hình danh sách bản nháp không tìm thấy nút "Chọn tất cả" với text exact, hàm return `False` mà **không bấm Back về Profile root**.
- Đồng thời, `ACCOUNT_READY` coi đây là lỗi nghiêm trọng (`self.context.is_ui_unavailable = True; return False`), làm sập toàn bộ workflow đăng video mới và kích hoạt soft reboot không cần thiết.

---

## 3. Giải Pháp Khắc Phục Chuẩn (Canonical Fixes)

### 3.1. Lưu Vết State Gốc Khi FSM Thất Bại
Trong `scripts/tiktok_workflow/state_machine.py`:
```python
        else:
            if (self.context.is_captcha or
                self.context.is_login_required or
                self.context.is_muted or
                self.context.is_ui_unavailable):
                self.current_state = manual_review_state
            else:
                self.last_failed_state = self.current_state
                if not self.context.error:
                    self.context.error = f"Failed at state {self.current_state.value}"
                self.current_state = fail_state
```
Trong `scripts/tiktok_workflow/run_post.py`:
```python
        else:
            logger.error(f"Workflow failed: {context.error}")
            failed_state_val = (
                getattr(machine, "last_failed_state", None) or machine.current_state
            ).value if machine.current_state == WorkflowState.FAILED else machine.current_state.value
            reporter.save_report({
                "status": "FAILED",
                "device_id": device_id,
                "error": context.error or f"Failed at state {failed_state_val}",
                "last_state": failed_state_val,
                ...
            })
```

### 3.2. Bổ Sung Selector `content_desc` & Tự Động Dismiss Floating Toolbar
Trong `_fill_caption_clipboard`:
- Tìm nút dán qua cả `text_contains` lẫn `content_desc`:
  ```python
  pasted = (
      adapter._tap_if_found(xml_text, text_contains="Dán")
      or adapter._tap_if_found(xml_text, text_contains="Paste")
      or adapter._tap_if_found(xml_text, content_desc="Dán")
      or adapter._tap_if_found(xml_text, content_desc="Paste")
      or adapter._tap_if_found(xml_text, content_desc="DÁN")
      or adapter._tap_if_found(xml_text, content_desc="PASTE")
  )
  ```
- Sau khi settle hashtag panel, nếu phát hiện Floating Toolbar đang mở (`CẮT`, `CHÉP`, `BỘ NHỚ TẠM`), gửi 1 phím `KEYCODE_BACK` để đóng toolbar và ẩn bàn phím:
  ```python
  post_settle_xml = adapter.dump_ui()
  if any(m in post_settle_xml for m in ('text="CẮT"', 'text="CHÉP"', 'text="BỘ NHỚ TẠM"', 'text="CUT"', 'text="COPY"')):
      logger.info("[CAPTION] Text selection toolbar active; pressing BACK to dismiss toolbar")
      adapter.keyevent("KEYCODE_BACK")
      time.sleep(1)
  ```
- Mở rộng kiểm chứng hashtag: Chấp nhận nếu có ít nhất 1 hashtag hoặc keyword token hiển thị trong composer:
  ```python
  if hashtags:
      if all(tag in normalized_visible for tag in hashtags):
          return True
      if any(tag in normalized_visible for tag in hashtags) or any(
          tag.lstrip("#") in normalized_visible for tag in hashtags
      ):
          return True
  ```

### 3.3. Draft Cleanup Là Non-Fatal & Đảm Bảo Thoát Về Profile Root
Trong `_delete_all_profile_drafts`:
- Hỗ trợ các biến thể của nút chọn: `"Chọn tất cả"`, `"Tất cả"`, `"Select all"` qua `text`, `text_contains` và `content_desc`.
- Nếu không tìm thấy, bấm `adapter.keyevent("KEYCODE_BACK")` để đảm bảo màn hình thoát khỏi danh sách bản nháp và quay lại trang Profile.
Trong `_handle_account_ready`:
- Không bao giờ set `self.context.is_ui_unavailable = True` khi dọn bản nháp thất bại. Bản nháp cũ không ngăn cản việc tải lên video mới; chỉ log warning và tiếp tục quy trình upload.
