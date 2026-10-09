# Kẹt Video Upload 67% & Xử Lý Banner "Không thể tải video lên. Đã lưu bản nháp"

## 1. Bản chất hiện tượng kẹt video 67%
- **0% đến ~60% (Local Transcoding & Nén)**: TikTok render hiệu ứng, chèn nhạc và nén video offline trực tiếp trên phần cứng máy. Giai đoạn này không phụ thuộc vào kết nối mạng nên hầu như luôn chạy bình thường.
- **~60% đến 100% (Network Chunk Streaming)**: Bắt đầu từ mốc ~65% - 67%, TikTok mở kết nối TCP/HTTP để stream các chunk dữ liệu video lên CDN máy chủ ByteDance qua proxy của thiết bị.
- **Kẹt đúng 67%**: Quá trình render offline đã xong nhưng vừa bắt đầu đẩy dữ liệu lên mạng thì bị ngắt kết nối:
  - Proxy bị timeout, rớt gói, hoặc xoay IP đột ngột.
  - App TikTok bị chuyển xuống nền (HOME) hoặc bị switch account quá sớm trước khi upload hoàn tất 100%.
  - Server TikTok tạm chặn hoặc từ chối gói tải lên (do vi phạm âm thanh / action block).

## 2. Hệ quả trên UI: Banner treo cản trở Workflow
Khi upload bị rớt kết nối, TikTok lưu video vào Bản nháp và bật banner trên giao diện:
> *"Không thể tải video lên. Đã lưu bản nháp."* kèm nút *"Không quan tâm"* / *"Chạm để thử lại"*.

Banner này chiếm quyền tiêu điểm (focus) màn hình, làm tê liệt các bước tiếp theo của workflow:
- Chặn không vào được Profile hoặc Account Switcher.
- Làm kẹt bước dọn dẹp bản nháp tự động (`_delete_all_profile_drafts`).

## 3. Quy chuẩn xử lý trong `state_machine.py` (`D:\Taadaa\Tiktok-video`)

### 3.1. Phương thức giải phóng banner:
`_dismiss_upload_failure_banner(adapter, xml_text, checkpoint=None) -> bool`
- **Nhận diện marker lỗi**: `"không thể tải video lên"`, `"couldn't upload video"`, `"could not upload video"`, `"tải lên không thành công"`.
- **Negative guard**: Không dismiss nếu màn hình chứa `"đăng nhập vào tài khoản"`, `"log in to tiktok"`, `"cài đặt mạng"` để tránh false-positive.
- **Hành động tap**: Tìm và tap các nút `"Không quan tâm"`, `"Hủy"`, `"Cancel"`, `"Đóng"`, `"Close"`, `"Bỏ qua"`, `"Dismiss"`. Nếu không có nút, gửi phím `adapter.back()`.
- **Telemetry & Checkpoint**: Ghi nhận `[TELEMETRY_POPUP_DISMISSED] type=UPLOAD_FAILURE_BANNER` và tăng `dismiss_count` trong checkpoint để tránh lặp vô hạn.

### 3.2. Vị trí gắn hook bắt buộc:
1. `_handle_dismiss_popups()`: Đóng ngay banner khi mở app hoặc trước khi bung account switcher.
2. `_wait_for_post_submission()`: Đóng ngay banner nếu vừa bấm Đăng mà mạng rớt giữa chừng trong vòng lặp 15 giây chờ submission.
