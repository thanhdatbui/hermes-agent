# Phân loại trạng thái Đăng Video & Báo cáo Watchdog (Feed & Upload Session)

Khi phân tích báo cáo từ `feed_session_watchdog.py` cho các ca nuôi TikTok (Kibe Máy 1-80, Admin Máy 201-280):

## 1. Cơ chế phân bổ Đăng Video
Mỗi phiên chạy ứng với một hàng tài khoản `Row N` (tương ứng file cấu hình `Tik{N}.xlsx` tại `D:\OneDrive\TaadaaData\<cluster>\Tik{N}.xlsx`).
Tiến trình `multi_machine_feed_session.py` chạy qua các Gate trước khi cho phép máy đăng video:

### Nhóm 1: "Đang dưỡng sinh (X)"
- **Nguyên nhân cốt lõi**: `reason: organic-rest-day-upload-disabled` hoặc `rest-day`.
- **Bản chất**: Cơ chế **Organic Rest (~33% farm)** được thiết kế để chống TikTok quét bot nuôi hàng loạt. Mỗi phiên sẽ bốc ngẫu nhiên khoảng 1/3 số máy để **chỉ lướt feed**, tuyệt đối **0 follow chéo, 0 đăng video**.
- **Ý nghĩa**: Đây là hoạt động an toàn bình thường, không phải lỗi kỹ thuật.

### Nhóm 2: "Khác (Y)" (Safe Skip do cấu hình/điều kiện)
- **Nguyên nhân phổ biến nhất**: `reason: missing_account_id`.
  - Trong Gate 4b: `read_machine_row_from_tik_workbook` đọc file `Tik{N}.xlsx`. Cột C (`ID`) của máy đang để trống (`None`) hoặc mang giá trị `MISSING_ID`.
  - Runner bỏ qua an toàn vì không thể upload khi chưa biết username TikTok.
- **Các nguyên nhân safe-skip khác được gom vào "Khác"**:
  - `already_uploaded`: Máy đã đăng thành công trong ca đó rồi (tránh đăng trùng lặp).
  - `cooling_period` / `account_cooling_period`: Nick mới chưa đủ ngày ngâm (cooldown 3 ngày kể từ ngày tạo hoặc mốc an toàn).
  - `sensitive-skip`: Feed kết thúc với stop_reason nhạy cảm (popup bảo mật, checkpoint...).
  - `not-final-session`: Không phải phiên cuối trong ca hoặc chưa đến giờ kích hoạt.
  - `under_10_days`, `age_gate`: Tuổi tài khoản chưa đủ điều kiện upload.
- **Cách tra cứu nhanh**:
  - Mở trực tiếp workbook `Tik{N}.xlsx` của cụm tương ứng, inspect cột C (`ID`) và `Folder Video` của các máy nằm trong danh sách "Khác".

### Nhóm 3: "Hết video/Cần cào (Z)"
- **Nguyên nhân cốt lõi**: `reason: video_not_rendered` hoặc `missing_video_folder`.
  - Gate 5 tính số thứ tự video kế tiếp: `next_video = posted_count + 1`.
  - Kiểm tra file `media_root / folder_video / f"{next_video}.mp4"`.
  - Nếu file không tồn tại hoặc `stat().st_size == 0`, runner đánh dấu `video_not_rendered`.
- **Bẫy False Alarm khi điều phối cụm chéo (Cross-Host Admin vs Kibe)**:
  - Kho video của cụm Admin nằm trên máy Admin (`D:\TIKTOK-videonuoinick-admin`).
  - Nếu runner chạy từ máy Kibe mà preflight upload kiểm tra path local `D:\TIKTOK-videonuoinick-admin` (vốn không tồn tại trên ổ D của Kibe), toàn bộ máy Admin sẽ bị báo giả `Hết video/Cần cào` dù kho trên máy Admin có sẵn hàng chục ngàn clip.
  - Khi thấy hàng loạt máy Admin báo hết video, bắt buộc verify remote qua SSH `admin-farm` kiểm tra folder đích trên máy Admin trước khi kết luận thiếu nguồn.
- **Cách khắc phục**: Nếu thiếu video thật trên đúng host chứa kho, cào video gốc và chạy pipeline render để cấp thêm video cho kênh đó.

### Nhóm 4: Máy không vào bước Upload
- Nếu một máy bị lỗi hoặc dừng ở bước Lướt Feed (máy sleep/dozing, mất kết nối ADB, kẹt popup không vượt qua được), runner sẽ không khởi chạy flow Upload cho máy đó.
- **Chẩn đoán mất kết nối hàng loạt (Hub USB rớt)**: Khi phát hiện một dải máy liên tục thất bại với lý do `device offline / device not found` (ví dụ M261-M280), kiểm tra ngay danh sách thiết bị ADB trên host tương ứng (với Admin: `ssh admin-farm "\"C:\Program Files (x86)\xiaowei\tools\adb.exe\" devices"`). Nếu thiếu 20+ máy, nguyên nhân là lỏng cáp/hub USB vật lý, không phải lỗi script hay ứng dụng.
