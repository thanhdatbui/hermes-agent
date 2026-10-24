# Triage: TikTok Milestone "Tổng Lượt Thích" Popup, LIVE Camera Trap, and Source Channel Integrity (2026-10-17)

## 1. User Invariant: "Nguồn Cũ" vs "Niche Cũ"
- **Định nghĩa bất biến:** "Nguồn cũ" là **ĐÚNG kênh / creator gốc** (cùng channel URL, cùng gương mặt, cùng phong cách).
- **CẤM:** Tuyệt đối không nhầm lẫn giữa "cùng niche" và "nguồn cũ". Không được nhồi clip của creator khác vào thư mục nguồn cũ dù cùng thể loại/niche.
- **Quy tắc 1 folder = 1 creator:** Nếu kênh cũ đã hết clip, phải dùng `swap_single_folder_pipeline.py` để thay thế trọn bộ >= 45 clip của một creator mới và đổi avatar đồng bộ, cấm chắp vá đa nguồn.

## 2. Workbook Header Drift: Parenthesized Column Aliases
- **Triệu chứng:** Runner crash với lỗi `Missing required fields: Folder Video` dù file Excel có dữ liệu.
- **Căn nguyên:** Các file Excel trên farm (`Tik1.xlsx` -> `Tik8.xlsx`) thường có header mở rộng có chú thích trong ngoặc đơn:
  - `Folder Video (Render Dich)`
  - `Video Goc (Nguon Cao)`
- **Xử lý:** `CANONICAL_HEADERS` trong `scripts/tiktok_workflow/account_source.py` bắt buộc phải chứa các alias chuẩn hóa có ngoặc đơn này (`folder video (render dich)`, `video goc (nguon cao)`).

## 3. Admin Downloader Proxy Loopback (502 Bad Gateway)
- **Triệu chứng:** Downloader trên host Admin (201-280) văng lỗi `ProxyError: 502 Bad Gateway` liên tục khi cào video từ YouTube/TikTok.
- **Căn nguyên:** Host Admin (`192.168.110.119`) cùng mạng LAN với router MikroTik (`192.168.110.2`). Khi cấu hình `proxy_pool_69.txt` dùng domain ngoài `mirotik1.taadaa.click:100xx`, request loopback ra ngoài WAN bị router từ chối.
- **Xử lý:** Ép thẳng IP LAN nội bộ `192.168.110.2:10001..10035` trong file proxy pool trên Admin. Khi sửa file, phải restart tiến trình downloader vì danh sách proxy được nạp vào RAM lúc khởi động.

## 4. Popup Milestone "Tổng Lượt Thích" Chặn Switcher
- **Triệu chứng:** Runner kẹt ở `ACCOUNT_SWITCHER` -> `SWITCHER_NOT_CONFIRMED`, dẫn đến soft reboot không cần thiết.
- **Hiện trường:** TikTok hiển thị popup chúc mừng thành tích:
  - Tiêu đề: *"Tổng lượt thích"*
  - Nội dung: *"twohavqyd8g đã nhận tổng cộng 359 lượt thích cho tất cả video"*
  - Nút bấm: `[OK]` ở giữa màn hình (tọa độ ~`[506, 1389, 575, 1425]` trên 1080x1920).
- **Xử lý:**
  - Trong `adapter.py` (`prepare_switcher_anchor`), khi phát hiện chuỗi `"tổng lượt thích"`, tự động bấm `[OK]` (cả text lẫn `content_desc`) hoặc fallback tap `(540, 1400)` trước khi dò profile header.
  - Sắp xếp candidates theo tọa độ $y$ tăng dần để lấy đúng tên tài khoản ở header.
  - Trong `state_machine.py` (`_dismiss_simple_close_popup`), bổ sung kiểm tra `content_desc` và fallback tap `(540, 1400)`.

## 5. Bẫy Màn Hình LIVE Camera Sau Khi Đăng Video
- **Triệu chứng:** Video đã đăng lên server thành công (`post-published-surface.png` tồn tại), nhưng ở bước `VERIFY_POST`, script văng lỗi `[POST_VERIFY_LIVE_SURFACE_BLOCKED]` và chuyển `MANUAL_REVIEW`.
- **Hiện trường:** TikTok tự động điều hướng sang giao diện Camera phát trực tiếp (`CAMERA / TẠO / LIVE`).
- **Điểm kẹt:** Phím `BACK` vật lý của Android bị app TikTok khóa/chặn ở màn hình này.
- **Xử lý:** Trong `_dismiss_live_surface`, bắt buộc tap vào nút `[X]` đóng camera ở góc trên bên trái `(60, 140)` trước khi gửi `BACK` để thoát về Feed/Profile.

## 6. Phụ Thuộc GanProxyWatcherTray Khi Soft Reboot
- **Triệu chứng:** Soft reboot recovery thất bại với `proxy watcher readiness was not published after reboot`.
- **Căn nguyên:** Scheduled task `GanProxyWatcherTray` bị `Disabled` trên host Kibe, khiến sau khi điện thoại boot xong không có tiến trình nào kích hoạt lại ViChanger để cấp card mạng `tun0`.
- **Xử lý:** Luôn đảm bảo task `GanProxyWatcherTray` ở trạng thái `Ready` và có tiến trình `gan_proxy_fleet.py watch` chạy nền trước khi thực hiện các đợt upload có recovery.
