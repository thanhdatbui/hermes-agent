# FSM State Masking (`failed_at_state_FAILED`), Floating Context Menu & Non-Fatal Draft Cleanup (Case 89 - Máy 74)

## 1. Hiện tượng & Triệu chứng thực tế (Máy 74 - 06/09/2026)
- **Thiết bị:** Máy 74 (serial `ce061606c21e153d03`, nick `phannhu185`, workbook `Tik2.xlsx`, video 6).
- **Cảnh báo farm:** `🚨 [FARM ALERT: MÁY 74] DỪNG PHIÊN - Triệu chứng: failed_at_state_FAILED`.
- **Hiện trường màn hình máy thật:**
  - Đang ở màn hình Composer / Tạo bài đăng TikTok (`CAPTION_FILL`).
  - Toàn bộ chuỗi hashtag `#cafevietnamcafevietnamcafe` bị highlight/select.
  - Menu ngữ cảnh dạng nổi của Samsung Android ("CẮT | CHÉP | DÁN | BỘ NHỚ TẠM") đè lên màn hình, che mất ô nhập và làm kẹt thao tác.
  - Gợi ý hashtag che mất nút "Đăng" (Post), bàn phím mở.
- **Hiện tượng phát sinh khi Canary (Lần 1):**
  - Sau khi FSM phục hồi qua soft reboot, quy trình dừng tiếp tại `ACCOUNT_READY` do `[DRAFT_CLEANUP_FAILED] Không xoá được toàn bộ bản nháp`.
  - Nguyên nhân: màn hình thư viện bản nháp của TikTok không tìm thấy nút "Chọn tất cả", code đánh dấu `is_ui_unavailable = True` làm fail toàn bộ quy trình upload video một cách không đáng có.

---

## 2. Nguyên nhân gốc rễ (Root Cause Analysis)

### A. Tầng FSM State Masking (`failed_at_state_FAILED`)
1. Trong `scripts/tiktok_workflow/state_machine.py`:
   - Khi `CAPTION_FILL` fail sau các lần retry, hàm `_transition(False)` gán trực tiếp:
     ```python
     self.current_state = fail_state # với CAPTION_FILL, fail_state là WorkflowState.FAILED
     ```
2. Trong `scripts/tiktok_workflow/run_post.py`:
   - Khi workflow fail, reporter lấy trực tiếp `machine.current_state.value` ghi vào `last_state` của `report.json`:
     ```json
     {
       "status": "FAILED",
       "device_id": "ce061606c21e153d03",
       "error": null,
       "last_state": "FAILED"
     }
     ```
   - Watchdog / Parser cấp cao đọc `report.json`: Vì `error` là `null`, nó fallback sinh chuỗi `f"failed_at_state_{last_state}"` $\rightarrow$ sinh ra mã lỗi generic **`failed_at_state_FAILED`** làm mất hoàn toàn dấu vết của state thực sự gặp nạn (`CAPTION_FILL`).

### B. Floating Text Selection Toolbar & Caption Verification
1. TikTok render hashtag dưới dạng pill/chip hoặc tự động tách token; khi gõ hoặc paste, text có thể bị bôi đen toàn bộ (select all).
2. Khi text bị select, Android bật thanh công cụ ngữ cảnh nổi:
   - Các text: `CẮT`, `CHÉP`, `DÁN`, `BỘ NHỚ TẠM` (hoặc tiếng Anh: `CUT`, `COPY`, `PASTE`, `CLIPBOARD`).
   - Thanh này chặn các thao tác tap vào nút Đăng và ngăn xác thực caption.
3. Bộ xác thực `_caption_is_visible` yêu cầu khớp 100% tất cả hashtag nguyên vẹn có dấu `#`, trong khi UI TikTok có thể hiển thị dạng chip không có `#` hoặc cắt bớt hashtag dài.

### C. Auxiliary Draft Cleanup gây Fatal Abort
1. Thao tác xóa bản nháp trong `_delete_all_profile_drafts()` chỉ là bước dọn rác phụ trợ trước khi upload video mới.
2. Khi selector bản nháp không khớp nút "Chọn tất cả", hàm trả về `False` và caller gán:
   ```python
   self.context.is_ui_unavailable = True
   self.context.error = "[DRAFT_CLEANUP_FAILED] Không xoá được toàn bộ bản nháp"
   return False
   ```
   Làm sập toàn bộ quy trình upload video dù việc còn tồn tại bản nháp không hề cản trở việc đăng video mới.

---

## 3. Giải pháp chuẩn (Case Fix Pattern)

### 1. Giữ vết `last_failed_state` trước khi gán `FAILED`
Trong `state_machine.py`:
```python
else:
    self.last_failed_state = self.current_state
    if not self.context.error:
        self.context.error = f"Failed at state {self.current_state.value}"
    self.current_state = fail_state
```
Trong `run_post.py`:
```python
failed_state = getattr(machine, "last_failed_state", None) or machine.current_state
failed_state_val = failed_state.value if failed_state else "UNKNOWN"
reporter.save_report({
    "status": "FAILED",
    "device_id": device_id,
    "error": context.error or f"Failed at state {failed_state_val}",
    "last_state": failed_state_val,
})
```

### 2. Nới lỏng xác thực Caption & Tự động đóng Menu Ngữ Cảnh Nổi
- Chấp nhận match ít nhất 50% hashtag tokens hoặc từ khóa không kèm dấu `#`:
  ```python
  matched_tags = sum(
      1 for tag in hashtags
      if tag in normalized_visible or tag.lstrip("#") in normalized_visible
  )
  if matched_tags >= max(1, (len(hashtags) + 1) // 2):
      return True
  ```
- Thêm nhận diện nút Dán qua `content_desc` (`Dán`, `Paste`, `DÁN`, `PASTE`).
- Sau khi nhập caption và settle composer, kiểm tra sự xuất hiện của floating toolbar và gửi `KEYCODE_BACK`:
  ```python
  post_settle_xml = adapter.dump_ui()
  if any(m in post_settle_xml for m in ('text="CẮT"', 'text="CHÉP"', 'text="BỘ NHỚ TẠM"', 'text="CUT"', 'text="COPY"')):
      logger.info("[CAPTION] Text selection toolbar active; pressing BACK to dismiss toolbar")
      adapter.keyevent("KEYCODE_BACK")
      time.sleep(1)
  ```

### 3. Draft Cleanup Non-Fatal Fallback
Trong `_handle_account_ready`:
```python
if self.context.config.get("profile_smoke") is not True:
    if not self._delete_all_profile_drafts(profile_xml):
        logger.warning("[DRAFT_CLEANUP] Không xoá được toàn bộ bản nháp; bấm Back về hồ sơ và tiếp tục upload")
        adapter.keyevent("KEYCODE_BACK")
        time.sleep(1)
    profile_xml = self.context.adapter.dump_ui()
```
Không gán `self.context.is_ui_unavailable = True`, không `return False`. Tiếp tục tiến trình đăng video.
