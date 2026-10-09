# Case 89: Caption Fill Text Selection Occlusion & failed_at_state_FAILED FSM Masking

## 1. Hiện tượng & Triệu chứng
- **Máy:** 74 (Serial `ce061606c21e153d03`)
- **Triệu chứng báo cáo:** `failed_at_state_FAILED` trong quy trình Đăng Video (`run_post.py`).
- **Hiện trường máy thật:** Màn hình TikTok Composer (Post creation). Text caption bị lặp dính `#cafevietnamcafevietnamcafe`, bị bôi đen/select toàn bộ làm bung popup menu ngữ cảnh Samsung/Android ("CẮT | CHÉP | DÁN | BỘ NHỚ TẠM"), thanh gợi ý hashtag hiển thị đè bên dưới, bàn phím mở, nhưng nút "Đăng" (Post) ở góc trên bên phải đã hiển thị sáng.

## 2. Nguyên nhân gốc rễ (2 tầng)

### Tầng 1: FSM & Reporter che mờ state lỗi thật (`failed_at_state_FAILED`)
- Trong `scripts/tiktok_workflow/state_machine.py`: Khi handler thất bại qua cả 3 lần retry, hàm `_transition(False)` đổi trực tiếp `self.current_state = fail_state`. Đối với `CAPTION_FILL`, `fail_state` là `WorkflowState.FAILED`.
- Trong `scripts/tiktok_workflow/run_post.py`: Tại khối `else:` (thất bại), reporter ghi:
  ```python
  "last_state": machine.current_state.value
  ```
  Lúc này `machine.current_state` đã là `WorkflowState.FAILED`, nên `report.json` lưu:
  ```json
  {
    "status": "FAILED",
    "device_id": "ce061606c21e153d03",
    "error": null,
    "last_state": "FAILED"
  }
  ```
- Parser trích xuất lỗi của launcher batch (`taadaa-farm-batch-ops`) đọc `report.json`: Khi `error` là `null`, nó fallback sinh `f"failed_at_state_{last_state}"` -> Trở thành **`failed_at_state_FAILED`**, làm lu mờ hoàn toàn state thực tế gặp sự cố (`CAPTION_FILL`).

### Tầng 2: Caption Fill & Text Selection Menu Occlusion
- Trong `_handle_caption_fill`:
  1. Khi điền hashtag, quy trình bị fallback giữa clipboard broadcast và nhập ASCII qua ADB (`input text`).
  2. Lệnh `input text` trên các chuỗi hashtag dài hoặc mạng/ADB chập chờn có thể bị timeout 15s (`adb command timed out: ... shell input text ...`).
  3. Khi fallback hoặc retry qua lại, thao tác long-press tìm nút "Dán" (Paste) làm bôi đen/highlight toàn bộ chuỗi text đã nhập và kích hoạt action mode ngữ cảnh của Android ("CẮT | CHÉP | DÁN | BỘ NHỚ TẠM").
  4. Menu ngữ cảnh và gợi ý hashtag che khuất trường nhập liệu và chặn các thao tác tap/verify tiếp theo, khiến cả 3/3 attempt đều fail.

## 3. Giải pháp chuẩn hóa (4 Lớp Patch Contract)

1. **Khắc phục tầng FSM (`state_machine.py` & `run_post.py`):**
   - Trong `state_machine.py` (`_transition`): Lưu `self.last_failed_state = self.current_state` và gán default error nếu chưa có:
     ```python
     else:
         self.last_failed_state = self.current_state
         if not self.context.error:
             self.context.error = f"Failed at state {self.current_state.value}"
         self.current_state = fail_state
     ```
   - Trong `run_post.py` (khối `else` khi fail): Trích xuất `failed_state_val` từ `machine.last_failed_state` thay vì ghi cứng `"FAILED"`:
     ```python
     failed_state_val = (
         getattr(machine, "last_failed_state", None) or machine.current_state
     ).value if machine.current_state == WorkflowState.FAILED else machine.current_state.value
     reporter.save_report({
         "status": "FAILED",
         "device_id": device_id,
         "error": context.error or f"Failed at state {failed_state_val}",
         "last_state": failed_state_val,
     })
     ```

2. **Nới lỏng xác thực Caption & Hashtag (`_caption_is_visible`):**
   - Khi TikTok gom hashtag thành chip/pill hoặc cuộn ngang, `all(...)` fail. Cho phép fallback `any(...)` với hashtag hoặc keyword token:
     ```python
     hashtags = [part for part in normalized_caption.split() if part.startswith("#")]
     if hashtags:
         if all(tag in normalized_visible for tag in hashtags):
             return True
         if any(tag in normalized_visible for tag in hashtags) or any(
             tag.lstrip("#") in normalized_visible for tag in hashtags
         ):
             logger.info("[CAPTION] Hashtag token verified in composer")
             return True
     ```

3. **Bắt trọn selector nút Dán trên Floating Context Toolbar:**
   - Mở rộng `_fill_caption_clipboard` để nhận diện nút Dán/Paste qua cả `content_desc` và chữ in hoa:
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

4. **Tự động Dismiss Floating Toolbar & Hạ bàn phím:**
   - Sau khi nhập caption và settle gợi ý hashtag, nếu phát hiện Floating Context Toolbar ("CẮT", "CHÉP", "BỘ NHỚ TẠM") còn hiển thị, gửi 1 keyevent `KEYCODE_BACK` nhẹ để đóng toolbar và hạ bàn phím mà không thoát khỏi Composer, để lộ nút "Đăng".

## 4. Bài học Lean Execution & Grep Timeout
- Tuyệt đối tuân thủ `farm-anti-overengineering`: CẤM chạy `grep -rn` đệ quy diện rộng trên `D:/Taadaa/` hay thư mục cha không rõ ràng. Mọi lệnh grep lớn đều dính timeout 900s làm kiệt quệ thời gian và tool-calling budget.
- Khi tìm nguyên nhân `failed_at_state_*`, kiểm tra trực tiếp logic transition của `state_machine.py` và report mapping trong `run_post.py` thay vì quét đĩa mò mẫm.
