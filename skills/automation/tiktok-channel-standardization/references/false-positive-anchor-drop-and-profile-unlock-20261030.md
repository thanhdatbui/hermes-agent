# False-Positive Follow Drop (Anchor Check Race) & New Profile Edit Unlock

## 1. Cơ Chế Nhả Follow Thật (Optimistic UI Drop vs Path B Verify)
### Hiện tượng
Trong các ca chạy nuôi TikTok (Mode 2: Follow Followers), watchdog hoặc runner báo cáo:
`FOLLOW_FAILED: anchor @<uid> bị nhả sau vuốt — dừng session` hoặc `FOLLOW_FAILED: TikTok không nhận follow (profile vẫn chưa follow)`.

### Bản Chất Kỹ Thuật (Truth from Code & Backend)
1. **Optimistic UI của TikTok:** Khi bot tap nút "Follow" trên danh sách / feed, app client TikTok ngay lập tức đổi màu nút thành "Đang follow" để tạo cảm giác mượt mà trước khi server phản hồi.
2. **Cơ chế Path B Verify (`_path_b_verify` trong `mode2_follow_followers.py`):**
   - Code farm **100% bắt buộc verify Path B** để chống Optimistic UI ảo: Sau khi tap nút Follow trên danh sách, bot tap tiếp vào avatar để mở trang Profile cá nhân của nick vừa follow.
   - Nếu trên Profile cá nhân đó nút vẫn là `Follow` / `Follow lại` thay vì `Đang follow`, điều đó chứng minh **Server TikTok đã âm thầm từ chối (REJECT) lệnh follow từ backend**.
   - Đây là **NHẢ THẬT bởi thuật toán TikTok**, KHÔNG PHẢI lỗi delay mạng! CẤM Coordinator suy đoán vô căn cứ là "do mạng lag", "do nick ít video" hay "chưa đủ ấm" khi chưa đọc file log.
3. **Session Velocity & Anchor Dwell Time:**
   - TikTok áp dụng bộ lọc rate-limit động theo phiên. Các máy xem video mồi (Anchor Dwell Time) dài (> 14s - 18s) như M17 thì server chấp nhận follow liên tục (ăn trọn 14 lượt). Các máy có dwell time ngắn hoặc bị gắn cờ bot tại thời điểm đó thì server drop ngay từ lượt đầu tiên.

### Kỷ luật Triage & Điều Tra
- **CẤM ĐOÁN MÒ LẢI NHẢI:** CẤM suy diễn lý thuyết suông. BẮT BUỘC dùng lệnh trích xuất O(1) kiểm tra trực tiếp:
  - `machines/machine_<N>/<run_id>/follow_result.json` (đọc exact `status`, `reason`, `followed_count`).
  - Sổ cái master `taikhoan_run_safe.xlsx` để so sánh ngày reg và số video thật giữa các máy cùng đợt.

---

## 2. Samsung S7 / New TikTok Profile: Nút Sửa Hồ Sơ & Mở Khóa Đổi Username
### Hiện tượng
Giao diện Profile TikTok mới trên Samsung S7 (1080x1920) khi tài khoản chưa có Bio:
- Không hiển thị nút chữ `Sửa hồ sơ`.
- Nút `+ Thêm tiểu sử` chiếm vị trí trung tâm `[36, 684][887, 768]`.
- Bấm vào tên nickname `Lý Thị Hoàn1` mở Account Switcher (chuyển đổi tài khoản) thay vì sửa tên.
- Bấm vào ID `@user...` bị chuyển hướng vào form nhập Tiểu sử.

### Cách vào màn hình "Sửa hồ sơ" chuẩn để đổi Username:
1. **Bước 1 (Mở khóa Bio):**
   - Tap vào `+ Thêm tiểu sử` (tọa độ `y ~ 720..740`).
   - Nhập một câu Bio bất kỳ qua ADB / AdbKeyboard (ví dụ: `Am nhac moi ngay`) ➔ Bấm **Lưu** (`[953, 133][1029, 168]` ở góc trên bên phải).
2. **Bước 2 (Vào Sửa hồ sơ):**
   - Sau khi có Bio, dòng chữ Bio xuất hiện trên Profile (`y ~ 680..720`).
   - **Tap thẳng vào dòng chữ Bio vừa tạo** (ví dụ `(211, 706)`).
   - TikTok sẽ mở ra trang **`Sửa hồ sơ`** đầy đủ (gồm: Thay đổi ảnh, Tên, Tên người dùng `@`, Tiểu sử).
3. **Bước 3 (Đổi Username `@`):**
   - Tap vào dòng `Tên người dùng` (`[445, 874][762, 915]`).
   - Xóa chuỗi cũ, nhập username mới (ví dụ `lyhoan.music`).
   - Bấm **Lưu** góc trên bên phải ➔ Bấm **Xác nhận** popup *"Cập nhật tên người dùng (30 ngày đổi 1 lần)"* tại `[644, 1222][853, 1259]`.
4. **Bước 4 (Atomic Sync):** Đồng bộ nguyên tử ngay lập tức vào Excel phân ca (`Tik<N>.xlsx`), master excel (`taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`) và SQLite `tiktok_tracker.db` (`account_mapping`, `farm_account_info`).
