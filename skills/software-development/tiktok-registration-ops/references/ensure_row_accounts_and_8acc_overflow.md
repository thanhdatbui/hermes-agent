# Quy Trình Tự Động Reg Bù (`ensure_row_accounts.py`) & Xử Lý Kịch Trần 8 Nick

## 1. Cơ Chế Preflight Reg Bù Tự Động Trước Khi Nuôi Acc
- Khi `tiktok_runner.py` chạy theo Ca và xác định `Row` (1..8), hàm `_preflight_ensure_accounts(row, window_key)` được kích hoạt trước khi spawn feed runner.
- Lệnh thực thi: `python D:/Taadaa/tools/ensure_row_accounts.py <row>`
  1. Quét file `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`: Phát hiện các máy có giá trị `None` hoặc rỗng ở hàng `row`.
  2. Đối chiếu với kho mail `gmail_clean_v2.xlsx`: Tìm mail sạch chưa từng được sử dụng (loại trừ toàn bộ `used_emails` trong `taikhoan_dat_v2_updated .xlsx`).
  3. Nếu thiếu mail -> tự động gọi `buy_hotmail.py` mua Hotmail OAuth2 và nạp vào máy.
  4. Khởi chạy `_run_all_targets.py` với biến môi trường `TIKTOK_REG_TARGET_STTS=<danh_sách_máy_thiếu>` để reg bù đúng các máy này.
  5. Đọc `tracking_result_*.json`, cập nhật tài khoản mới vào `taikhoan_dat_v2_updated .xlsx` và đồng bộ tự động sang `taikhoan_run_safe.xlsx`.

## 2. Sự Cố Kịch Trần 8 Nick & Nick Lạc Khác Máy (Ẩn Nút "Thêm tài khoản")
- **Hiện tượng lỗi:**
  - Script dừng ở bước 4 `tap_add_account` với thông báo:
    `RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account', 'Thêm tài khoản khác', 'Add another account', 'add_account')`
  - Mặc dù bảng theo dõi báo máy đang thiếu slot (ví dụ Row 6 là `None`).
- **Nguyên nhân cốt lõi:**
  - Ứng dụng TikTok trên Android giới hạn tối đa **8 tài khoản** đăng nhập cùng lúc. Khi đã đủ 8 tài khoản, nút "Thêm tài khoản" bị ẩn hoàn toàn khỏi danh sách dropdown.
  - Sự cố nick lạc: Do lịch sử nạp trùng cùng 1 địa chỉ email vào 2 máy khác nhau (ví dụ email của Máy 40 bị nạp nhầm vào Máy 19). Khi Máy 19 chạy đăng ký với email này, TikTok nhận diện email đã có nick nên chuyển sang luồng Đăng nhập (OTP Graph API), vô tình kéo nick của Máy 40 vào Máy 19.
- **Quy trình gỡ rối chuẩn hóa:**
  1. Dump XML giao diện dropdown chuyển tài khoản (`social_reg_v1.py` -> `get_ui_xml`).
  2. Đọc danh sách các nick đang đăng nhập trên máy từ các node `resource-id="com.ss.android.ugc.trill:id/lpw"`.
  3. Đối chiếu danh sách này với 8 tài khoản chính thức của máy trong `taikhoan_dat_v2_updated .xlsx` để xác định nick thừa/lạc không thuộc máy.
  4. Chuyển sang nick thừa đó trong app TikTok.
  5. Điều hướng: Tab *Hồ sơ* -> *Menu ba gạch* (góc phải trên) -> *Cài đặt và quyền riêng tư* -> Cuộn xuống đáy màn hình chọn *Đăng xuất* -> Xác nhận *Đăng xuất*.
  6. Sau khi đăng xuất nick thừa, ứng dụng còn 7 nick -> Nút "Thêm tài khoản" lập tức xuất hiện trở lại.
  7. Chạy lại `python D:/Taadaa/tools/ensure_row_accounts.py <row>` để hoàn tất đăng ký nick mới vào đúng hàng.

## 3. Cấu Hình Báo Cáo Telegram & Pitfall Format Folder Máy Đơn (2026-09-18)
- **Kênh Telegram chuẩn (Farm Alert):**
  - Mọi báo cáo summary `[PREFLIGHT REG BÙ ROW X]` BẮT BUỘC gửi về nhóm **Farm Alert** (`-5373649734`).
  - Tuyệt đối KHÔNG gán nhầm sang nhóm Gmail Reg (`-5139245637`).
- **Pitfall Format Folder `stt_{m:02d}` vs `stt_{m}`:**
  - Thư mục artifact trên đĩa được lưu với format 2 chữ số (`stt_02`, `stt_03`).
  - Khi trích xuất lỗi trong `_extract_reg_error`, nếu chỉ tìm `f"stt_{m}"`, các máy < 10 sẽ không khớp thư mục và fallback hiển thị chữ `FAILED` cộc lốc.
  - Bắt buộc kiểm tra `b_dir / f"stt_{int(m):02d}"` trước, sau đó mới fallback `b_dir / f"stt_{m}"`.
- **Bài học phân loại lỗi khi Reg bù diện rộng (Ví dụ ca 34 máy):**
  - `MACHINE_FULL_8_ACCOUNTS`: Máy thật đã đủ 8 nick trên Switcher mặc dù Excel còn slot trống -> Cần chạy JIT Reconcile hoặc logout nick rác nhả slot trước khi kích hoạt reg.
  - `BLOCKED_GMAIL_OTP_TIMEOUT`: Gmail cũ dễ dính timeout nhận OTP -> Ưu tiên cấp Hotmail OAuth2 qua `buy_hotmail.py` (tỷ lệ thành công 100%).
  - `UI_XML_TIMEOUT` / ADB timeout: atx-agent hoặc kết nối ADB chập chờn > 20s -> Cần phục hồi ADB/atx-agent.

