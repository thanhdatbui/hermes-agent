# Case 97 (2026-09-13): Triage Lỗi [AVATAR_EDIT_UNAVAILABLE] trên Clone/Secondary Profile TikTok

## 1. Hiện tượng & Triệu chứng thực tế (Farm Alert)
- Khi watchdog hoặc launcher batch upload avatar (`run_tiktok_upload_avatar.ps1` / `post_evening_avatar_watchdog.py`) chạy cho các Row mới (ví dụ Row 5 trên `Tik5.xlsx`), hàng loạt máy (14/39 máy) báo lỗi:
  ```text
  [AVATAR_EDIT_UNAVAILABLE] ENSURE_AVATAR: TikTok báo hoạt động sửa avatar không có sẵn
  ```
- Toàn bộ batch bị đánh rớt thành `FAILED` / `LỖI`.

## 2. Nguyên nhân gốc rễ trong Codebase
- Trên các phiên bản TikTok mới và tài khoản clone/phụ (secondary profile được switch qua account switcher), khi tap vào Sửa hồ sơ hoặc Ảnh đại diện, TikTok hiển thị popup cảnh báo dạng:
  *"hoạt động không có sẵn đối với tài khoản ban đầu"*
- Trong `D:\Taadaa\Tiktok-video\scripts\tiktok_workflow\state_machine.py`:
  Hàm `_wait_for_avatar_edit_screen` nhận diện popup này và trả về `edit_state = "unavailable"`.
  Tuy nhiên, tại bước fallback cuối (dòng ~6003):
  ```python
  if edit_state == "unavailable":
      if not adapter._tap_if_found(current_xml, text="OK"):
          adapter.back()
      raise WorkflowError(
          WorkflowState.ENSURE_AVATAR,
          "TikTok báo hoạt động sửa avatar không có sẵn",
          "AVATAR_EDIT_UNAVAILABLE",
      )
  ```
  Việc `raise WorkflowError` làm ngắt ngay lập tức quy trình upload và đánh dấu máy thất bại, thay vì bỏ qua an toàn (safe-skip).

## 3. Giải pháp & Quy chuẩn xử lý chuẩn (Safe-Skip Pattern - Case 97)
1. **Không raise WorkflowError khi gặp popup cấm sửa avatar tài khoản phụ**:
   - Khi phát hiện `edit_state == "unavailable"`:
     1. Tap "OK" hoặc bấm Back để đóng popup cảnh báo.
     2. Ghi nhận `self.context.avatar_status = "SKIPPED_AVATAR_EDIT_UNAVAILABLE"` (hoặc `"SKIPPED_EXISTING_AVATAR"`).
     3. Log thông báo:
        ```python
        logger.warning("[ENSURE_AVATAR] TikTok báo hoạt động sửa avatar không có sẵn trên profile phụ; safe-skip để tiếp tục flow")
        ```
     4. Trả về `True` để workflow tiếp tục các bước tiếp theo (hoặc kết thúc avatar_smoke với trạng thái thành công).
2. **Cập nhật tập trạng thái hợp lệ (`accepted`)**:
   - Trong `_handle_ensure_avatar`, bổ sung `"SKIPPED_AVATAR_EDIT_UNAVAILABLE"` vào tập `accepted` bên cạnh `"SKIPPED_EXISTING_AVATAR"`, `"UPLOADED_VERIFIED"`, `"FORCED_REPLACED_VERIFIED"`.
3. **Unit Test Verification**:
   - Viết test case `test_avatar_edit_unavailable_safe_skip` trong `tests/test_tiktok_workflow.py` mock `_wait_for_avatar_edit_screen` trả về `("unavailable", xml)` kèm đầy đủ stub `MockAdapter` (`_find_ui_element`, `tap`, `bring_to_foreground`).
   - Chạy `pytest tests/test_tiktok_workflow.py -k "test_avatar_edit_unavailable_safe_skip"` xác nhận PASS 100%.
4. **Quy tắc điều phối Coordinator**:
   - Khi nhận Farm Alert có `AVATAR_EDIT_UNAVAILABLE` diện rộng:
     - Kiểm tra O(1) qua `summary.csv` trong `D:\CodexRuntime\tiktok-video\batch-runs\<batch_id>\`.
     - Phân loại rõ: nhóm máy dính `AVATAR_EDIT_UNAVAILABLE` (lỗi logic state machine), nhóm `ACCOUNT_SWITCHER_FAILED` (kẹt popup/mất focus), nhóm `DEVICE_OFFLINE` (lỗi vật lý).
     - Soạn Patch Contract đóng (c=1) và dispatch Worker Subagent xử lý trong repo `Tiktok-video`.
