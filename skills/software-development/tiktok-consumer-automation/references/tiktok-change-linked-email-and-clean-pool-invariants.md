# TikTok Change Linked Email Flow & Clean Mail Pool Invariants

> **Context**: Áp dụng khi đổi email liên kết của nick TikTok hiện có trên farm Android (SM-G930 / S7) hoặc khi thay thế Hotmail hỏng pass / thiếu pass cho profile GPM / TikTok.

---

## 1. Cạm Bẫy "Bốc Mail Cũ Đã Reg" & Kỷ Luật Thẩm Định Mail Sạch

### 1.1 Nguyên nhân lỗi (User Correction)
- **Lỗi nhận thức**: Kiểm tra một email chỉ trên tệp `taikhoan_dat_v2_updated .xlsx` rồi kết luận email đó "chưa dùng" là SAI LẦM.
- **Thực tế hệ thống**:
  - Các file đệm (`hotmail_input.txt`, `latest_bought_70.txt`, `hotmail_all_60_bought.txt`) chứa nhiều email đã từng được nạp vào các đợt reg TikTok trước đó, hoặc đã đăng ký TikTok nhưng bị fail ở bước sau, hoặc đã được cấp cho máy khác trong `gmail_clean_v2.xlsx`.
  - Khi bốc các mail này nhập vào TikTok flow `Thay đổi email`, TikTok lập tức chặn với thông báo lỗi đỏ:
    > **`com.ss.android.ugc.trill:id/icn | text="Email này đã được sử dụng"`**
  - Người dùng chất vấn: *"Ủa sao lúc change hotmail lại đi bốc các hotmail đã reg r. Chưa hiểu"*.

### 1.2 Kỷ luật chọn Hotmail thay thế
1. **Ưu tiên mua mới 100% qua tool canonical**:
   - Sử dụng lệnh: `python D:/Taadaa/tools/buy_hotmail.py --buy 1 --target-file <path>`
   - Tool tự động điều phối BoxTaiKhoan (nếu còn stock/balance) hoặc CloneFBIG fallback (stock hàng ngàn acc, balance sẵn có).
2. **Kiểm tra hộp thư Graph API trước khi gán**:
   - Gọi Microsoft Graph API: `https://graph.microsoft.com/v1.0/me/messages?$top=5&$select=subject,receivedDateTime`
   - Đảm bảo trong inbox **KHÔNG CÓ** bất kỳ email nào từ TikTok (`là mã gồm 6 chữ số của bạn` hoặc `là mã TikTok của bạn`).
3. **Kiểm tra va chạm chéo máy (Cross-machine collision)**:
   - Tra cứu trong `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx`: Đảm bảo mail không thuộc về slot của máy khác (tránh trường hợp rút ruột mail của máy này đắp cho máy kia).

---

## 2. Quy Trình UI Đổi Email Liên Kết TikTok Trên Android (ADB / ATX)

### Bước 1: Xác định tài khoản mục tiêu
- Mở TikTok: `adb shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1`
- Vào tab **Hồ sơ** (`bounds=[864,1794][1080,1920]`).
- Kiểm tra `@username` đang hiển thị. Nếu chưa đúng nick mục tiêu, bấm dropdown Switcher ở đỉnh (`bounds=[36,280][325,364]`), cuộn và chọn đúng nick (ví dụ: `yobi1965`).

### Bước 2: Điều hướng đến mục Email
1. Bấm Menu 3 gạch góc trên phải (`bounds=[954,96][1056,204]`).
2. Ở bottom-sheet hiện lên, bấm **Cài đặt và quyền riêng tư** (thường ở `[330,1243][860,1303]` hoặc `[360,1091][942,1151]`).
3. Tại danh sách Cài đặt, bấm **Tài khoản** (`bounds=[24,1704][1056,1878]`).
4. Tại màn hình Tài khoản, bấm **Thông tin tài khoản** (`bounds=[24,246][1056,402]`).
5. Bấm vào dòng **Email** (`bounds=[24,402][1056,558]`).

### Bước 3: Thao tác Thay đổi email & Nhập mail mới
1. Popup hiện email hiện tại dạng che (`Email của bạn: y***f@hotmail.com`).
2. Bấm nút **Thay đổi email** (`bounds=[120,1262][960,1405]`).
3. Dialog xác nhận *"Thay đổi email? Email mới của bạn cũng sẽ được sử dụng cho xác minh 2 bước"*: Bấm nút **Tiếp tục** (`bounds=[541,1212][960,1355]`).
4. Màn hình nhập email:
   - Gõ tiền tố email qua ADB: `adb shell input text <prefix>` (ví dụ: `thresajf21011996`).
   - Bấm vào pill gợi ý đuôi `@hotmail.com` (`bounds=[748,927][1069,1011]`) để điền nhanh đuôi mail chuẩn xác, tránh lỗi gõ phím ảo.
   - Bấm nút đỏ **Tiếp tục** (`bounds=[96,735][984,891]`).

### Bước 4: Lấy OTP qua Graph API & Xác nhận
1. TikTok chuyển sang màn hình *"Xác minh email - Sử dụng liên kết này hoặc nhập mã được gửi đến..."*.
2. Script Python gọi Microsoft Graph API đọc token:
   ```python
   # Lấy access token từ refresh_token
   # Query https://graph.microsoft.com/v1.0/me/messages?$top=5&$select=subject,bodyPreview,receivedDateTime
   # Regex tìm mã 6 số: \b(\d{6})\b trong subject hoặc preview
   ```
3. Nhập mã OTP 6 số qua ADB: `adb shell input text <OTP>`.
4. Nếu TikTok hiện thông báo hỏi bản tin/quảng cáo (*"Bạn muốn nhận nội dung thịnh hành..."*): Bấm **Không, cảm ơn** (`bounds=[38,1713][1043,1857]`).

### Bước 5: Bằng chứng xác minh (Visual Evidence Invariant)
- Màn hình quay trở lại **Thông tin tài khoản** với dòng email đã cập nhật (ví dụ: `t***6@hotmail.com`).
- Chụp ảnh màn hình lưu vào thư mục Taadaa và gửi bằng chứng cho User qua cú pháp:
  `MEDIA:D:\Taadaa\m34_final_verified_fresh_thresajf.png`

---

## 3. Đồng Bộ Trạng Thái Hệ Thống (Triệt Để 3 Nơi)

1. **Master Excel (`taikhoan_dat_v2_updated .xlsx`)**:
   - Luôn tạo bản sao lưu trước khi ghi (`taikhoan_dat_v2_updated_before_fresh_*.xlsx`).
   - Cập nhật đúng dòng máy/slot: cột F (`email`) và cột G (`pass_mail`).
2. **GPM Supervisor State (`batch_gpm_5profiles_supervisor_state.json`)**:
   - Xóa key profile cũ (ví dụ: `M34:yobifqtx...`).
   - Tạo key profile mới: `M34:<new_email>`, gán `mail_password`, đặt `stage: HOTMAIL_LOGIN`, `status: PENDING`.
3. **Kho Token Kế Thừa (`D:/Taadaa/Hotmail/hotmail_input.txt`)**:
   - Nối dòng định dạng `mail|pass|refresh_token|client_id` vào cuối file để các module kiểm tra token sau này có đầy đủ context.
