# TikTok Profile Draft Resume & Recovery Workflow

## 1. Bối cảnh & Vấn đề
Khi upload TikTok gặp lỗi mạng, crash hoặc bị ngắt quãng giữa chừng sau khi đã render/tải video vào editor, TikTok thường tự động lưu trạng thái vào **Bản nháp (Draft)** trên tab Hồ sơ (Profile).
Trước đây, script `state_machine.py` trong `ACCOUNT_READY` có bước dọn dẹp `_delete_all_profile_drafts()` xóa sạch bản nháp để tránh lẫn lộn. Tuy nhiên, với flow upload batch, việc xoá bản nháp dẫn đến:
- Mất công upload/chuẩn bị video trước đó.
- Không tận dụng được bản nháp đã có sẵn để upload tiếp.
- Có thể bị lặp lỗi và không hoàn tất lượt đăng.

## 2. Quy tắc xử lý Draft Resume (Patch Contract)
1. **StateContext Tracking:**
   - Thêm cờ `has_profile_draft: bool = False` vào `StateContext`.
2. **ACCOUNT_READY State:**
   - Khi kiểm tra XML profile, nếu phát hiện `bản nháp` hoặc `draft`, đặt `self.context.has_profile_draft = True`.
   - Giữ nguyên bản nháp (không xoá) để chuẩn bị resume ở state `VIDEO_PICK`.
3. **VIDEO_PICK Flow:**
   - Ưu tiên kiểm tra: Nếu `self.context.has_profile_draft` là `True`, chuyển hướng sang `_resume_draft_from_profile(adapter, xml_text)` thay vì bấm nút "+" tạo mới từ Feed/Gallery.
4. **Quy trình `_resume_draft_from_profile` (4 bước):**
   - **Bước 1:** Đảm bảo ở màn hình Hồ sơ, tap vào tile `Bản nháp` (`text_contains="Bản nháp"` hoặc `"Draft"`).
   - **Bước 2:** Mở video nháp đầu tiên trong danh sách (`resource_id="cover"`, `bounds` parse fallback, hoặc tọa độ mặc định ô đầu).
   - **Bước 3:** Trên màn hình Editor xem trước video nháp, tap `Tiếp` / `Next` để tiến vào Composer.
   - **Bước 4:** Xác nhận màn hình Đăng / Composer (`_is_final_composer_surface` hoặc chứa `text="Đăng"` / `text="Post"`).
5. **Video Tile Counting Baseline:**
   - Trong `_profile_video_tile_records`, phải loại trừ các tile bản nháp (`"bản nháp"` / `"draft"`) để không tính nhầm ô nháp vào số lượng video đã publish công khai (baseline post count).

## 3. Lệnh test kiểm chứng
Chạy bộ test focused:
```bash
PYTHONPATH="D:/Taadaa/automation-core/src;D:/Taadaa/Tiktok-video/scripts" "D:/Taadaa/python-envs/automation/Scripts/python.exe" -m pytest "D:/Taadaa/Tiktok-video/tests/test_upload_failure_recovery.py"
```
