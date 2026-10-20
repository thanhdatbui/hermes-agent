# Channel Standardization Workflow (Avatar - Hashtag - Pin Top View)

## 1. Bối cảnh & Trigger
Áp dụng khi người dùng gửi ảnh chụp màn hình trang cá nhân (Profile TikTok) kèm lệnh:
`"Chuẩn hoá kênh này"` hoặc `"Chuẩn hoá acc này"`.

Mục tiêu chuẩn hoá toàn diện 3 món:
1. **Avatar:** Đảm bảo avatar đồng bộ nhân vật chính trong kho video gốc $F_{src}$ (HD $512 \times 512$, căn chuẩn tâm ngũ quan an toàn viền tròn), không dùng avatar rác/lệch hoặc dính chữ phụ đề.
2. **Hashtag/Niche:** Khóa marker và đăng ký registry chống các script batch render đè pool hashtag sai ngách.
3. **Ghim Video (Pin Top):** Ghim video có lượt xem cao nhất lên đầu profile nếu thỏa mãn điều kiện Floor Filter $\ge 1.000$ views.

---

## 2. Quy Trình 4 Bước Chuẩn Hoá Toàn Diện

### Bước 1: Định Vị Tọa Độ Phone Farm O(1)
- Dùng WinRT OCR (`windows-native-ocr` qua `D:/Taadaa/tmp_winrt_ocr.py`) bóc tách nhanh:
  * Username / Handle (dạng `@username`).
  * Tên hiển thị (Nickname).
  * Tiểu sử (Bio).
  * View các video trên lưới.
- Quét nhanh các workbook tại `D:/OneDrive/TaadaaData/kibe/Tik*.xlsx` hoặc `D:/OneDrive/TaadaaData/admin/Tik*.xlsx` tìm dòng chứa username để xác định:
  * Số máy (`May`) & Slot TikTok (`1..8`).
  * Thư mục video gốc $F_{src}$ (cột `Folder Gốc` hoặc `F_src`).
  * Thư mục render $F_{out}$ (cột `Folder Render` hoặc `F_out`).
  * Chủ đề / Niche kênh.

### Bước 2: Soi Mắt & Tạo Preview 2 Phương Án Avatar (Gate 6 Visual Invariant)
- Kiểm tra các file `avatar.jpg` có sẵn trong:
  * Kho video gốc: `D:/video goc/<F_src>/avatar.jpg`
  * Kho video nuôi nick / render: `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`
- Nếu avatar cũ bị dính chữ phụ đề hoặc chất lượng kém, trích xuất frame mới có mặt nhân vật từ clip gốc bằng HaarCascade/Face detection, crop $512 \times 512$.
- **Tạo canvas so sánh 2 phương án trực quan:**
  * Phương án 1 (Khuyên dùng): Chân dung nhân vật chính từ video gốc $F_{src}$.
  * Phương án 2: Ảnh đại diện từ kho render $F_{out}$.
  * Vẽ vòng tròn định vị màu xanh (bán kính 250px) để mô phỏng viền cắt tròn của ứng dụng TikTok.
  * Xuất ảnh ra `D:/Taadaa/reports/m<N>_avatar_options_preview.jpg`.
  * Soi mắt OCR kiểm chứng và gửi `MEDIA:<path>` cho User lựa chọn.

### Bước 3: Khóa Kép Chống Ghi Đè (Anti-Overwrite Protection)
Sau khi xác định phương án hoặc User duyệt:
- Tạo marker vật lý `.manual_avatar_locked` và `.manual_hashtag_locked` trong các thư mục liên quan.
- Đăng ký folder ID vào registry bảo vệ SSOT:
  * `D:/Taadaa/data/manual_avatar_protected_folders.json`
  * `D:/Taadaa/data/manual_hashtag_protected_folders.json`
- Cập nhật trạng thái `PENDING` trong workbook và `avatar_replace_queue` (`tiktok_tracker.db`) nếu nạp qua watchdog ca tối, hoặc nạp trực tiếp qua long-press / edit profile nếu thao tác ngay.

### Bước 4: Kiểm Chứng & Ghim Video Top View (Pin Gate $\ge 1.000$ views)
- Soi số view của các clip trên lưới Profile từ ảnh chụp và qua UI XML:
  * **Nếu toàn bộ video < 1.000 views:** Giữ nguyên thứ tự tự nhiên của video, không ghim gượng ép.
  * **Nếu có video $\ge 1.000$ views:** Tiến hành ghim video có view cao nhất lên đầu profile.
- Sử dụng runner chuẩn hóa:
  ```bash
  python D:/Taadaa/tools/pin_top_videos.py --machine <N> --account <username> --min-views 1000 --dry-run
  ```
- **Kỷ luật an toàn thiết bị:**
  * Lệnh chạy standalone bắt buộc bọc `operator_device_lock` để không vi phạm Hard Gate #5.
  * `AdbClient` bắt buộc truyền `adb_path=ADB_BIN` để `capture_atx_session_ui` đọc đúng XML qua ATX persistent UI session (port 7912), tuyệt đối không curl trực tiếp `/dumpUI` (trả về 404) và không dùng shell uiautomator dump.
