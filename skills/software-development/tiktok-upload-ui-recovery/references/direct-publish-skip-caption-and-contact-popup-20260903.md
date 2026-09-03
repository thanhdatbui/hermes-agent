# Video Pick / Editor Direct Publish Skipping CAPTION_FILL & Contact Sync Modal (2026-09-03)

## Triệu chứng & Incident (Evidence Máy 74, 2026-09-03)
* **Alert:** `🚨 [MÁY 74] DỪNG PHIÊN • Script: tiktok-video • Tài khoản: Samnga2403 • Lý do: upload_subprocess_nonzero`
* **Log:**
  ```
  [INFO] scripts.tiktok_workflow.state_machine: Video pick completed: 1.mp4
  [INFO] scripts.tiktok_workflow.state_machine: >>> State: CAPTION_FILL
  [WARNING] scripts.tiktok_workflow.state_machine: Caption field not found via selectors
  [WARNING] scripts.tiktok_workflow.state_machine: Handler failed (attempt 1/3)
  ...
  [ERROR] scripts.tiktok_workflow.state_machine: Job failed sau 1 attempts. Last error: None
  ```
* **Hiện trường thực tế qua ATX capture:**
  - Video số 1 (folder 587) của tài khoản `Samnga2403` **đã được đăng thành công** lên kênh (trên Profile `@samnga2403` có tile video với `tv_play_count: 25`).
  - Màn hình thiết bị sau khi đăng rơi về Feed (tab Bạn bè) kèm popup modal đồng bộ danh bạ: *"Thêm bạn bè, dùng TikTok thêm vui. Khi đồng bộ danh bạ điện thoại, bạn có thể tìm thấy những người bạn có thể biết và được họ tìm thấy."* (2 nút: `OK` và `Không cho phép`).
  - Workbook `tik3.xlsx` dòng 75 vẫn giữ nguyên số video `0` do tiến trình thoát sớm ở `CAPTION_FILL` trước khi đến `UPDATE_WORKBOOK`.

## Nguyên nhân gốc (Root Cause)
1. **Direct Publish / Fast Story Bypass:**
   - Trên một số phiên bản TikTok (hoặc khi đăng video đầu tiên của tài khoản mới), sau khi chọn video trong Gallery Picker và bấm "Tiếp", TikTok xuất bản trực tiếp hoặc nút bấm trong Editor kích hoạt đăng ngay về Home/Feed thay vì chuyển sang màn hình soạn thảo caption truyền thống (`caption_edit_text`, `g9u`, `Suy nghĩ của bạn...`).
2. **Thiếu Popup Dismissal & Post Proof Check trong `CAPTION_FILL`:**
   - `_handle_caption_fill` chỉ kiểm tra sự tồn tại của `_find_caption_field`.
   - Khi không thấy ô caption (do app đã về Feed hoặc bị modal đè), `CAPTION_FILL` không gọi bộ giải phóng popup benign (`detect_contact_sync_dialog`) và cũng không kiểm tra xem video đã được xuất bản hay chưa (không chạy `_recheck_ambiguous_post`).
   - Dẫn đến việc script báo lỗi `upload_subprocess_nonzero` (exit code 1) dù video đã thực sự lên sóng thành công.

## Quy trình Triage & Khắc phục Chuẩn
1. **Kiểm tra hiện trường bằng ATX Primary:**
   - Không vội chạy lại làm trùng video (`DUPLICATE_MEDIA_BLOCKED`).
   - Dùng `capture_atx_session_ui` (hoặc `inspect_machine.py`) đọc XML trang Profile xem số lượng video tile / `tv_play_count` có tăng so với baseline (0 -> 1).
2. **Xử lý Popup Modal Danh bạ:**
   - Nút `Không cho phép` nằm ở node text `Không cho phép` (hoặc `deny_button` trong detector `detect_contact_sync_dialog` của `automation_core.tiktok.benign_popup`).
3. **Đồng bộ Workbook:**
   - Khi xác nhận video đã lên thành công qua Profile grid scan, cập nhật thủ công hoặc qua script reconciliation số video trong `TikN.xlsx` (tăng từ 0 lên 1) để tránh upload lặp lại.
4. **Cải tiến Script State Machine:**
   - Trong `_handle_caption_fill`: nếu sau lần quét đầu không tìm thấy caption field, thử gọi `_dismiss_core_benign_popup` và kiểm tra `_recheck_ambiguous_post()` / profile video count. Nếu video đã được đăng thành công, chuyển thẳng sang `UPDATE_WORKBOOK`.
