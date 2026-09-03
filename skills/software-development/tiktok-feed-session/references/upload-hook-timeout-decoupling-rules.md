# Upload Hook Timeout Decoupling & Batch Upload Safety Rules

## 1. Bản chất sự cố & Bài học kiến trúc:
- **Tách riêng Budget Timeout:**
  - Tiền xử lý lướt Feed (`feed_session_smoke`) mất trung bình 5–7 phút / máy (8–11 swipes).
  - Hook đăng video (`run_post.py` qua `Tiktok-video`) mất từ 3–5 phút / máy trên Samsung S7 do các bước render video, kiểm tra visual gate và chuyển cảnh UI.
  - Tuyệt đối KHÔNG gộp chung timeout của Feed Session với Upload Hook hoặc để Feed Session Watchdog bao ngoài (`worker_hard_timeout`) ngắt ngang Hook Upload khi đang đăng video hợp lệ.
  - Công thức tính Hard Outer Watchdog tối thiểu:
    $$\text{worker\_hard\_timeout} = \text{feed\_timeout} + \text{upload\_extra\_budget} + 300\text{s (buffer)}$$
    Trong đó `upload_extra_budget` mặc định tối thiểu 1200.0s (20 phút).
- **Chuẩn hóa giá trị Timeout:**
  - Bắt buộc dùng `math.isfinite()` và `math.ceil()` khi parse các giá trị timeout float từ config để chống crash do `NaN` / `Infinity` hoặc bị ép về `0s` gây timeout tức thì.

## 2. Quy tắc vận hành chạy bù Đăng Video (Upload Batch):
- **Cấm chạy Upload đè lên Feed Session đang chạy:**
  - Tuyệt đối không kích hoạt batch upload bù (`run_tiktok_upload_batch.ps1`) khi ca nuôi feed của phiên cuối chưa kết thúc hoàn toàn trên toàn farm.
  - Việc mở app TikTok để upload song song khi máy đang ở nhịp chạy feed vét cuối sẽ gây tranh chấp giao diện (`TikTok focus lost`, kẹt màn hình Camera/Media Picker, dẫn tới lỗi sai lệch trạng thái trên Farm Alerts).
- **Quy mô Worker Đăng Video:**
  - Giữ cố định **16 workers** cho batch đăng video (không nâng lên 40 như nuôi feed).
  - 16 workers đảm bảo an toàn cho băng thông USB Hub (`adb push` file MP4 8–15MB) và băng thông proxy/VPN ViChanger, tránh sập kết nối ADB hàng loạt.
