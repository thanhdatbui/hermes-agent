# Xử lý Popup Bản Nháp Dở Chừng & Banner Upload Thất Bại (TikTok Upload Automation)

## Hiện tượng & Ngữ cảnh
Khi batch upload video TikTok chạy trên farm, có 2 trường hợp liên quan đến "Bản nháp" (Draft) xuất hiện ngắt quãng luồng upload:

1. **Popup "Tiếp tục chỉnh sửa bài đăng này?" ("Continue editing this post?")**:
   - Xuất hiện khi TikTok bị tắt/kill trong lúc đang ở màn hình composer hoặc upload dở chừng lần trước.
   - Khi mở lại TikTok hoặc vào upload, app hiện popup hỏi tiếp tục chỉnh sửa.
   - **Chỉ thị của User**: Bấm vào bản nháp rồi bấm đăng tiếp thay vì hủy bỏ hay xóa bỏ.
   - Cần phân biệt với luồng dọn dẹp profile nháp: Nếu đang trong flow upload video mới và gặp bản nháp dở chừng, ưu tiên tap "Tiếp tục chỉnh sửa" / "Edit" / "Bản nháp" để khôi phục composer và đăng tiếp.

2. **Banner "Không thể tải video lên. Đã lưu bản nháp"**:
   - Khi mạng yếu hoặc TikTok timeout upload, banner thông báo màu đen hoặc popup xuất hiện ở đỉnh hoặc chân màn hình.
   - Nếu dismiss banner này bằng các nút "Không quan tâm", "Hủy", "Cancel", "Bỏ qua", app sẽ giữ video trong mục Bản nháp trên trang Profile (`_delete_all_profile_drafts`).

## Điểm Neo & Anchor trong State Machine (`scripts/tiktok_workflow/state_machine.py`)

- **Xử lý popup khôi phục bản nháp**:
  - `_dismiss_resume_draft_popup(adapter, xml_text)`: Trong `DISMISS_POPUPS` và `VIDEO_PICK`.
  - Cần hỗ trợ 2 chế độ:
    - Chế độ default: Nếu user yêu cầu tiếp tục đăng bản nháp (`resume_draft=True` hoặc phát hiện video đang dở), tap vào "Chỉnh sửa" / "Tiếp tục chỉnh sửa" / "Edit", sau đó chuyển sang `CAPTION_FILL` hoặc `POST`.
    - Chế độ dismiss an toàn (khi cần upload video mới tinh): Lưu bản nháp hoặc xóa bản nháp khỏi profile root.
- **Xử lý banner upload thất bại**:
  - `_dismiss_upload_failure_banner(adapter, xml_text)`: Tự động tap "Không quan tâm" / "Hủy" hoặc nhấn `Back` để giải phóng màn hình mà không bị kẹt chu kỳ FSM.
