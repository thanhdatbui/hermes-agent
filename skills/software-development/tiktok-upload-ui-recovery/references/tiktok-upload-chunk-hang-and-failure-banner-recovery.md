# Xử Lý Lỗi Upload Kẹt 60% - 70% (Network Streaming Chunk Hang) & Banner Lưu Bản Nháp

## 1. Hiện tượng & Cơ chế kỹ thuật của TikTok
- Trên lưới Profile hoặc thông báo hệ thống, video bị kẹt ở mốc tiến trình `Đang tải lên (60% - 70%)` (phổ biến nhất là 67%).
- **Cơ chế tải lên 2 pha của TikTok**:
  1. **Phase 1 (0% -> ~60% - Local Transcoding & Packaging)**: Nén video, render filter, sync âm thanh offline hoàn toàn trên phần cứng điện thoại (Samsung S7). Pha này hầu như 100% vượt qua mượt mà.
  2. **Phase 2 (~60% -> 100% - Network Streaming Chunks)**: TikTok mở kết nối TCP/HTTP đẩy các gói dữ liệu chunk lên CDN ByteDance (TTNet) qua proxy gắn trên máy.
- **Nguyên nhân kẹt 67%**:
  - Proxy bị timeout, rớt gói, đổi IP (rotate) hoặc đứt socket giữa chừng khi đang stream chunk dữ liệu.
  - Automation hoặc người dùng đưa app xuống background (`KEYCODE_HOME`) hoặc switch account sớm trước khi video đạt 100%, khiến hệ điều hành Android đóng băng luồng mạng của TikTok.
  - Server TikTok ngắt kết nối do cờ kiểm duyệt âm thanh/bản quyền hoặc giới hạn tần suất đăng (Action Cooldown).
  - TikTok không nhận được ACK từ server nhưng cũng không throw exception crash, dẫn đến thanh tiến trình bị đóng băng vĩnh viễn trên UI Profile.

## 2. Di chứng bề mặt (Surface Occlusion)
- Khi app được kích hoạt lại hoặc kết nối hồi phục, TikTok hiển thị banner/popup lỗi:
  - Text tiếng Việt: *"Không thể tải video lên. Đã lưu bản nháp."*
  - Text tiếng Anh: *"Couldn't upload video. Saved to drafts."*
  - Các nút hành động: *"Không quan tâm"*, *"Chạm để thử lại"*, *"Hủy"*, *"Đóng"*.
- **Tác hại**:
  - Banner chiếm tiêu điểm bề mặt, che khuất thanh điều hướng dưới đáy và các nút trên Profile.
  - Video tải dở bị chuyển thành 1 ô "Bản nháp" (Drafts) trong thư viện Profile, làm sai lệch số đếm `pre_post_video_count` trong các thuật toán verify video increment (`_verify_profile_post_increment`).

## 3. Quy chuẩn xử lý trong Automation StateMachine

### A. Dismiss Failure Banner Tự Động (`_dismiss_upload_failure_banner`)
Tích hợp vào cả `_handle_dismiss_popups` (khi mở app/chuẩn bị chuyển account) và `_wait_for_post_submission` (khi vừa bấm Đăng):
```python
@staticmethod
def _dismiss_upload_failure_banner(adapter, xml_text: str) -> bool:
    """Dismiss TikTok upload failure banner ('Không thể tải video lên. Đã lưu bản nháp')."""
    lowered = xml_text.casefold()
    if not any(
        marker in lowered
        for marker in (
            "không thể tải video lên",
            "couldn't upload video",
            "could not upload video",
            "tải lên không thành công",
        )
    ):
        return False
    for label in ("Không quan tâm", "Hủy", "Cancel", "Đóng", "Close", "Bỏ qua", "Dismiss"):
        if adapter._tap_if_found(xml_text, text=label) or adapter._tap_if_found(xml_text, text_contains=label):
            logger.info("[POPUP] Đã đóng banner upload thất bại / lưu bản nháp (%s)", label)
            return True
    if hasattr(adapter, "back") and callable(adapter.back):
        adapter.back()
        logger.info("[POPUP] Đã nhấn Back để đóng banner upload thất bại")
        return True
    return False
```

### B. Xóa sạch bản nháp treo trước khi Post (`_delete_all_profile_drafts`)
Tại bước `ACCOUNT_READY`, sau khi xác minh đúng tài khoản đích, nếu phát hiện ô `Bản nháp` xuất hiện trên Profile grid:
1. Mở thư viện Bản nháp -> Chọn -> Chọn tất cả -> Xóa -> Xác nhận Xóa.
2. Quay về Profile root trước khi chốt `pre_post_video_count` baseline để loại trừ 100% ghost tiles.
