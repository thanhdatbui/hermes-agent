# Pitfalls: Cross-Device Multi-Account Leak & Cron False Promises

## 1. Hiện Tượng Nick Đăng Nhập Trùng Nhiều Máy (Cross-Device Duplicate Login)
- **Triệu chứng:**
  - File Excel `taikhoan_run_safe.xlsx` hoặc `taikhoan_dat_v2_updated .xlsx` hiển thị máy thiếu nick ở Slot 7 hoặc Slot 8 (`None`).
  - Runner gọi reg bù hoặc login thì crash với lỗi `[04_add_account] Không tìm thấy nút 'Thêm tài khoản'`.
  - Kiểm tra UI XML của Account Switcher (`fail_04_add_account_*.xml`) thì thấy trên thiết bị **đã đủ 8 tài khoản**.
- **Nguyên nhân cốt lõi:**
  1. **Nạp trùng email giữa các máy trong quá khứ:** Một Hotmail/Gmail bị nạp cho 2 máy khác nhau trước khi có cơ chế kiểm tra chặn trùng mail. Khi máy thứ hai reg/login, nó đăng nhập vào chính nick TikTok của máy thứ nhất.
  2. **Copy đè dữ liệu trùng lặp trong Excel:** Có tình trạng nick ở Slot 6 bị copy đè xuống Slot 8, trong khi Slot 7 để trống. Bộ lọc an toàn loại bỏ ID trùng khiến hệ thống tưởng máy thiếu nick.
- **Quy trình xử lý dứt điểm:**
  1. **CẤM TUYỆT ĐỐI chỉ đối soát nội bộ trên file Excel**: Soi trùng lặp giữa các dòng Excel là hoàn toàn vô hiệu vì nick ký sinh chỉ tồn tại trên UI của máy thật, không hề có dòng nào trên Excel của máy bị ký sinh (đây là bài học xương máu khiến agent báo sót nick ký sinh).
  2. **Bắt buộc đối soát qua UI XML máy thật**: Dùng atx-agent hoặc screencap trích xuất danh sách username TikTok thực tế trong Account Switcher (các button bounds `[0, y][1080, y]`), sau đó so từng nick ngược lại toàn bộ workbook `taikhoan_dat_v2_updated .xlsx` để bóc trần nick ký sinh.
  3. Xác định nick chính chủ (máy gốc) và nick ký sinh (máy bị log nhầm).
  4. Thực hiện **Logout** nick ký sinh ra khỏi thiết bị bằng watchdog event-driven `watchdog_idle_parasite_reconcile.py` khi máy rảnh (0 locks, Idle) để app TikTok trở về 7 nick, nút "Thêm tài khoản" sẽ xuất hiện lại.
  5. Làm sạch ô bị copy trùng trong file Excel để tránh bộ lọc hiểu nhầm là thiếu slot.

## 2. Kỷ Luật Tuyệt Đối Về Canh Giờ & Lập Lịch Cron (Anti-False-Promise)
- **CẤM TUYỆT ĐỐI "HỨA MỒM" CANH GIỜ:**
  - Khi user chỉ đạo "canh hết phiên X rồi làm", CẤM NÓI "vâng em đang canh" mà không tạo cron job hay tiến trình thực tế.
  - Phải lập tức kiểm tra `date` thực tế của hệ thống để biết chính xác đang ở khung giờ nào, tránh việc đọc log quá khứ rồi nhầm tưởng thời gian hiện tại.
- **QUY TẮC NÉ KHUNG GIỜ CRON TRỌNG YẾU:**
  - **Khung 14:00 - 18:00:** Chạy chuỗi chiều `post-noon-chain` (Reg Gmail + Add 2FA TikTok). CẤM can thiệp thiết bị farm trong khung giờ này vì sẽ phá vỡ tiến trình lấy OTP và nhận 2FA.
  - **Khung 21:00 - 23:45:** Chạy chuỗi tối (Avatar upload + GPM Login).
  - **Khung giờ vàng an toàn sau Ca tối:** **20:45 - 21:15** (Sau khi Phiên 2 Ca tối kết thúc, toàn bộ 80 máy về Home và trước khi Avatar watchdog kích hoạt).
- **MẪU TẠO WATCHDOG TỰ ĐỘNG CHUẨN:**
  - Luôn tạo script watchdog kiểm tra lock `.codex/device-locks`: chỉ khi số lượng active lock = 0 mới kích hoạt tác vụ.
  - Nạp cron job với schedule thăm dò `*/5` trong khung giờ vàng và dùng state file ghi nhận `last_run_date` để chỉ chạy đúng 1 lần/ngày.
