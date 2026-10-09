# TikTok Draft Cleanup: Non-Fatal Pattern & Multi-Variant Select-All

## 1. Bối cảnh & Hiện tượng (Context & Symptom)
- **Repo:** `D:/Taadaa/Tiktok-video`
- **File:** `scripts/tiktok_workflow/state_machine.py`
- **Hàm:** `_handle_account_ready` và `_delete_all_profile_drafts`
- **Hiện tượng:** Khi tài khoản có bản nháp tồn đọng, state machine vào nhánh dọn dẹp nháp (`_delete_all_profile_drafts`). Nếu TikTok thay đổi UI hoặc ngôn ngữ (ví dụ nút đổi thành "Tất cả", "Select all", hoặc selector nằm ở `content_desc`), hàm không tìm thấy nút "Chọn tất cả".
- **Hậu quả cũ:** State machine coi đây là fatal failure:
  ```python
  self.context.is_ui_unavailable = True
  self.context.error = "[DRAFT_CLEANUP_FAILED] Không xoá được toàn bộ bản nháp"
  return False
  ```
  Hệ quả là toàn bộ ca upload video bị huỷ bỏ (state machine chuyển sang `FAILED`), tài khoản bị đánh dấu lỗi UI dù khả năng đăng video mới vẫn hoàn toàn bình thường.

---

## 2. Nguyên nhân kỹ thuật (Root Cause)
1. **Selector cứng nhắc (Rigid Selectors):** Chỉ tìm duy nhất `adapter._tap_if_found(select_xml, text="Chọn tất cả")`. TikTok trên các phiên bản khác nhau hoặc tài khoản tiếng Anh/giao diện mới dùng các nhãn khác nhau:
   - `text="Chọn tất cả"` / `text_contains="Chọn tất cả"`
   - `text="Tất cả"` / `text_contains="Tất cả"`
   - `text_contains="Select all"`
   - `content_desc="Chọn tất cả"` / `content_desc="Select all"`
2. **Kẹt màn hình khi fail (Unclean Exit):** Khi không tìm thấy nút "Chọn tất cả", script chỉ log warning rồi `return False` mà không gửi phím `KEYCODE_BACK`, khiến giao diện điện thoại kẹt ở màn hình chọn nháp.
3. **Phân cấp lỗi sai (Fatal vs Non-Fatal):** Việc dọn dẹp nháp là bước bảo dưỡng phụ trợ (housekeeping), không phải điều kiện tiên quyết bắt buộc để đăng video mới. Việc abort toàn bộ tiến trình upload vì không xoá được nháp là over-fatal.

---

## 3. Giải pháp 2 lớp (Two-Layer Fix)

### Lớp 1: Multi-variant Selector & Safe Exit trong `_delete_all_profile_drafts`
Mở rộng tập selector và luôn đảm bảo thoát an toàn về màn hình trước bằng `KEYCODE_BACK`:
```python
select_xml = adapter.dump_ui()
tapped_all = (
    adapter._tap_if_found(select_xml, text="Chọn tất cả")
    or adapter._tap_if_found(select_xml, text_contains="Chọn tất cả")
    or adapter._tap_if_found(select_xml, text="Tất cả")
    or adapter._tap_if_found(select_xml, text_contains="Tất cả")
    or adapter._tap_if_found(select_xml, text_contains="Select all")
    or adapter._tap_if_found(select_xml, content_desc="Chọn tất cả")
    or adapter._tap_if_found(select_xml, content_desc="Select all")
)
if not tapped_all:
    logger.warning("[DRAFT_CLEANUP] Không tìm thấy nút Chọn tất cả; nhấn Back để thoát màn hình nháp")
    adapter.keyevent("KEYCODE_BACK")
    time.sleep(1)
    return False
```

### Lớp 2: Chuyển sang Non-Fatal trong `_handle_account_ready`
Khi dọn dẹp nháp thất bại, log warning, bấm Back về hồ sơ, cập nhật lại `profile_xml` và tiếp tục luồng upload bình thường:
```python
if self.context.config.get("profile_smoke") is not True:
    if not self._delete_all_profile_drafts(profile_xml):
        logger.warning("[DRAFT_CLEANUP] Không xoá được toàn bộ bản nháp; bấm Back về hồ sơ và tiếp tục upload")
        adapter.keyevent("KEYCODE_BACK")
        time.sleep(1)
    profile_xml = self.context.adapter.dump_ui()
```

---

## 4. Kiểm chứng (Verification)
1. **Kiểm tra cú pháp:**
   `python -m py_compile D:/Taadaa/Tiktok-video/scripts/tiktok_workflow/state_machine.py`
2. **Focused Test:**
   `pytest D:/Taadaa/Tiktok-video/tests/test_tiktok_workflow.py -k "draft"`
3. **Bài học Lean Execution:**
   - Với file monolith lớn (>12.000 dòng như `state_machine.py`), tránh dùng công cụ tìm kiếm diện rộng có thể dính lỗi path/timeout.
   - Dùng script Python trực tiếp mở file, kiểm tra `content.count(old_string) == 1` (Uniqueness check), thay thế và ghi đĩa để hoàn tất trong 1 turn duy nhất.
