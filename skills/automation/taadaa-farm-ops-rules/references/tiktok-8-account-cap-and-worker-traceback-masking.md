# TikTok 8-Account Cap, Reconcile Fast-Login & Content Duplication Safeguards

## 1. 8-Account Cap & Lịch Chạy Farm

Trần cứng **8 acc/máy** (Row 1–8):
- **Ngày lẻ (Lane B)**: Row 1, 3, 5, 7
- **Ngày chẵn (Lane A)**: Row 2, 4, 6, 8

**Mốc giờ (BLOCK_ANCHORS):**
- Ca 1: 06:00
- Ca 2: 12:00
- Ca 3: 18:00
- Ca 4: 00:00

---

## 2. Xử Lý Máy Báo Thiếu Nick / Mất Nút "Thêm Tài Khoản" (17/09/2026)

### A. Cạm Bẫy Đăng Ký Đè Khi Chưa Đối Soát
- **Nguyên nhân gốc rễ**: Khi máy chạm trần 8 nick, nếu tool tiếp tục chạy reg hoặc nạp nick mới mà không logout nick cũ, TikTok sẽ:
  1. Đẩy nick cũ ra khỏi danh sách hiển thị của Switcher.
  2. Lưu session nick cũ vào bộ nhớ đệm **"Chào mừng bạn trở lại (Fast Login / One-Tap Login)"**.
  3. Khi runner chạy ca của nick cũ, Switcher không tìm thấy ID -> runner ngỡ ngàng kích hoạt auto-login nhập lại mật khẩu.
- **HẬU QUẢ CỰC KỲ NGUY HIỂM (Magic Link & OTP Rate Limit)**:
  - Nếu runner nhảy vào nhập pass liên tục mà bỏ dở màn hình OTP 2FA hoặc không nhập OTP kịp, TikTok sẽ tự động chuyển cơ chế xác thực sang **Magic Link qua Email** hoặc kích hoạt **Rate limit 900 giây**, làm tê liệt hoàn toàn khả năng auto-login của bot!
  - Tuyệt đối không để bot tự ý trigger auto-login khi tài khoản vẫn còn cache trên thiết bị.

### B. Quy Trình Khôi Phục An Toàn (Zero Risk):
1. **Kiểm tra số lượng nick thực tế trên Switcher**:
   - Nếu còn < 8 nick (có nút "Thêm tài khoản"): Bấm vào "Thêm tài khoản" xem màn hình "Chào mừng bạn trở lại" có lưu sẵn cache nick cần tìm không.
   - Nếu có: Bấm chọn nick -> Nhập OTP tươi từ 2FA TOTP hoặc đọc trực tiếp từ app Outlook trên máy (`read_tiktok_otp_from_outlook_app`). KHÔNG bỏ dở màn hình OTP.
2. **Nếu máy chạm trần đúng 8 nick**:
   - Đối soát 8 nick trên Switcher với `taikhoan_run_safe.xlsx`:
     - Nếu có nick mồ côi (parasite - nick từ đợt chạy trước bị đè khỏi Excel nhưng còn trên máy): Sao lưu thông tin (User, Pass, Mail, Pass Mail, 2FA) trước.
     - Vào `Cài đặt và quyền riêng tư` -> Chọn `Đăng xuất` đơn lẻ **ĐÚNG nick mồ côi đó** để nhả slot.
     - TUYỆT ĐỐI CẤM logout các nick mới reg (chưa có 2FA) vì đổi fingerprint sẽ kích hoạt checkpoint làm chết nick vĩnh viễn.
   - Sau khi nhả slot, nút "Thêm tài khoản" xuất hiện trở lại -> nạp lại nick chính chủ qua Fast Login + TOTP.

### C. Vòng Lặp Vô Tận Reg Bù & Cơ Chế Auto-Reconcile Nhả Trần (18/09/2026)
- **Cơ chế lỗi lặp vô tận (Infinite Reg-Bù Loop)**:
  - Khi Excel (`taikhoan_run_safe.xlsx`) để trống slot (ví dụ Row 8 = `None`), script điều phối `ensure_row_accounts.py` quét thấy thiếu nick $\rightarrow$ tự động mua mail và kích hoạt `_run_all_targets.py` để reg bù.
  - Tuy nhiên, trên máy thật đã có đủ 8 nick trên Switcher (do chứa nick ký sinh chéo máy hoặc nick rác).
  - Code `social_reg_v1.py` mở Switcher thấy 8 nick $\rightarrow$ raise `MACHINE_FULL_8_ACCOUNTS` rồi thoát.
  - **Hệ quả**: Excel vẫn trống Row 8 $\rightarrow$ Feed ca tiếp theo skip với `config-error` $\rightarrow$ Ca sau `ensure_row_accounts.py` lại đâm đầu vào reg bù tiếp và fail tiếp.
- **Quy trình OCR Phân tích & Tự động Logout Nhả Trần (Gốc rễ)**:
  1. **OCR Switcher**: Chụp hoặc lấy ảnh `_03_dropdown_*.png`, chạy WinRT OCR bóc tách toàn bộ danh sách username trên màn hình Switcher.
  2. **So khớp Excel 7 Slots**: So sánh danh sách OCR với 7 tài khoản hợp lệ của máy đó trong Excel.
  3. **Phân loại nick chiếm trần**:
     - *Nick ký sinh (Parasite)*: Username thuộc sở hữu của máy khác trong Farm (ví dụ `@annapmfdh0a` của M44 nằm trên M28, `@anggiathinh2905` của M28 nằm trên M61).
     - *Nick rác (Rogue)*: Username không hề tồn tại trong Master Excel (`taikhoan_dat_v2_updated .xlsx`).
  4. **Tự động Logout nhả slot (`do_logout`)**:
     - **CẠM BẪY ĐIỀU HƯỚNG SWITCHER (BẮT BUỘC)**: Sau khi `open_app`, TikTok đang ở **Home Feed ("Trang chủ")**, CẤM TUYỆT ĐỐI gọi trực tiếp `open_account_dropdown`. BẮT BUỘC phải qua `go_to_profile` trước để vào tab Hồ sơ rồi mới mở Switcher dropdown. Nếu gọi mở Switcher ngay từ Home Feed sẽ fail 100%, rơi vào vòng retry và crash `RuntimeError: [03_dropdown]`.
     - **CẠM BẪY DAILY STORY PROMPT & BÀN PHÍM ("TÁM CHUYỆN NÀO")**: Khi vào tab Hồ sơ, TikTok thường bung popup Story Prompt ("Tám chuyện nào" / "Bài đăng Thường nhật...") kèm bàn phím Android che khuất màn hình. Phải gửi `keyevent 4` (KEYCODE_BACK) để hạ bàn phím, sau đó tap nút Đóng `(84, 150)` hoặc gửi thêm 1 lần Back nữa để giải phóng màn hình trước khi mở Switcher.
     - **CẠM BẪY MATCH USERNAME XML**: Trong UI XML của Switcher, text/content-desc của nick thường có tiền tố `@` (ví dụ `@annapmfdh0a`). So khớp string bắt buộc chuẩn hóa `username.lstrip("@").lower()` trên cả 2 vế (`u_clean in (d_clean, t_clean)`), tuyệt đối không dùng `username == d` nguyên bản kẻo miss node.
     - Switch sang nick lạ/ký sinh $\rightarrow$ Vào Profile $\rightarrow$ Menu 3 gạch $\rightarrow$ Cài đặt và quyền riêng tư $\rightarrow$ Cuộn đáy $\rightarrow$ Đăng xuất.
     - **CẠM BẪY VERIFY SCREENSHOT SAU LOGOUT**: Sau khi confirm logout nick ký sinh, TikTok tự động văng về Home Feed hoặc màn hình Login. CẤM gọi ngay `open_account_dropdown` để chụp ảnh kiểm chứng kẻo bị treo và crash. BẮT BUỘC phải qua `go_to_profile` trước rồi mới mở Switcher dropdown chụp ảnh.
     - Sau khi logout, số nick trên máy giảm về 7 $\rightarrow$ Nút "Thêm tài khoản" hiện lại $\rightarrow$ Quá trình reg bù Row 8 mới thành công.

  5. **Tọa độ & Công thức Logout Nick Ký sinh Chuẩn Xác (19/09/2026)**:
     - **Tọa độ cố định Samsung S7 (1080x1920)**:
       + Đánh thức máy: `input keyevent 224 && input keyevent 82`
       + Mở TikTok: `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1` (chờ 5s)
       + Vào Profile: `input tap 972 1857` (chờ 3s)
       + Mở Switcher: Vuốt nhẹ (`input swipe 540 1200 540 800 250`) rồi tap header (`input tap 540 140`) (chờ 3s)
       + Nhận diện vị trí nick: Chụp screencap Switcher, chạy `powershell -Command "D:\Taadaa\do_ocr.ps1 (Resolve-Path '<path>').Path"`.
         * **Cạm bẫy WinRT OCR Path**: `do_ocr.ps1` dùng `StorageFile::GetFileFromPathAsync`, bắt buộc đường dẫn Windows chuẩn tuyệt đối (`Resolve-Path` hoặc `os.path.abspath`). Không truyền forward slash hoặc relative path kẻo crash `NullReferenceException` / `AggregateException`.
       + Tap chọn nick ký sinh $\rightarrow$ chờ 5s chuyển tài khoản.
       + Vào lại Profile: `input tap 972 1857` (chờ 3s).
       + Mở Menu 3 gạch: `input tap 1005 150` (chờ 3s).
       + Chọn Cài đặt và quyền riêng tư: `input tap 540 1250` (đáy menu 3 gạch, chờ 4s).
       + Cuộn đáy Cài đặt: Lặp 6 lần (`input swipe 540 1600 540 300 250`, sleep 1s).
       + Tap nút Đăng xuất: `input tap 300 1640` (chờ 3s).
       + Tap xác nhận Đăng xuất trên dialog: `input tap 540 1640` (chờ 6s).
       + Chụp ảnh nghiệm thu: Vào lại Profile (`972 1857`) $\rightarrow$ Mở Switcher (`540 140`) $\rightarrow$ Chụp screencap lưu `D:/Taadaa/reports/m{id}_verified_logout.png`.
       + OCR đối soát: Xác nhận nick ký sinh ĐÃ BIẾN MẤT và Switcher ĐÃ HIỆN LẠI nút "Thêm tài khoản" (hoặc còn đúng 7 nick).
       + Teardown an toàn: `am force-stop com.ss.android.ugc.trill && input keyevent 3`.
     - **Kỷ luật ngân sách Tool Calls (Batch Runner Discipline)**:
       + Khi thực hiện trên nhiều máy (ví dụ 3-10 máy) trong giới hạn ngân sách tool call (25 turns), TUYỆT ĐỐI KHÔNG chạy tương tác ADB từng lệnh qua từng tool call đơn lẻ.
       + BẮT BUỘC đóng gói toàn bộ quy trình trên vào một Python runner script thực thi tự động (mọi lệnh `subprocess.run` BẮT BUỘC có `timeout=15`), chạy trọn gói và trả về ảnh nghiệm thu trong 1-2 tool calls.

  6. **Van chặn Hardware Ceiling Cooldown trong `ensure_row_accounts.py`**:
     - Khi một máy báo lỗi `MACHINE_FULL_8_ACCOUNTS`, script phải ghi nhận máy đó vào state cooldown blacklist (`machine_full_8_cooldown.json`).
     - Ở các ca quét tiếp theo, `ensure_row_accounts.py` tự động bỏ qua các máy này (chuyển vào danh sách Cooldown), KHÔNG được tiếp tục mua Hotmail thừa và KHÔNG dispatch reg vô ích làm nghẽn farm.
  6. **Đồng bộ JIT nếu nick hợp lệ**: Nếu nick thứ 8 trên máy là nick chính chủ đã reg từ trước nhưng bị sót chưa điền Excel, phải ghi nhận ngay vào Row 8 Excel thay vì cố reg tài khoản mới.
  7. **Nguyên lý bảo toàn Nick Chính chủ khi Logout Nick Ký sinh (18/09/2026)**:
     - *Bản chất kỹ thuật*: TikTok lưu session, refresh token và cache Switcher độc lập trên phân vùng `/data/data/com.ss.android.ugc.trill` của từng thiết bị vật lý riêng biệt.
     - *Hành vi*: Khi thực hiện `Đăng xuất (Log out)` nick ký sinh khỏi máy phụ (máy bị log nhầm), thao tác này **CHỈ xóa session cục bộ trên máy phụ đó**, hoàn toàn **KHÔNG gửi lệnh hủy session hay xóa tài khoản trên máy chính chủ** (máy đã đăng ký ra nick đó).
     - *Quy tắc đối soát trước khi logout*:
       + Tra cứu username trong `taikhoan_dat_v2_updated .xlsx` xem nick đó thuộc về máy nào (ví dụ `@annapmfdh0a` thuộc Slot 350 của Máy 44).
       + Xác nhận nick đó vẫn đang có mặt trong Switcher của máy chính chủ (Máy 44) trước khi logout khỏi máy phụ (Máy 28).
       + Nếu là nick rác không tồn tại trong Excel (`user*`, nick thử nghiệm cũ): Logout thẳng tay để giải phóng slot.

---

## 3. Quy Chuẩn Tải Hạ Tầng ADB & Giới Hạn Worker Song Song (18/09/2026)
- **Ngưỡng nghẽn USB Hub & Xiaowei ADB Server**:
  - Khi chạy các script tác vụ UI/ADB diện rộng toàn Farm (như `clear-tiktok-cache`, `reconcile`, `ui dump`), **CẤM TUYỆT ĐỐI đặt `MAX_WORKERS = 40`** (bài học: đặt `MAX_WORKERS = 40` đè bẹp ADB server và nghẽn bus USB hub chia 80 máy, gây timeout đồng loạt 59/78 máy).
  - **Mức trần cân bằng User chốt (18/09/2026)**: Đặt **`MAX_WORKERS = 20`** cho tác vụ dọn dẹp cache (`cron_clear_tiktok_cache.py`) để hoàn tất nhanh mà không gây sập ADB daemon. Với các tác vụ UI dump nặng hoặc reconcile phức tạp, giữ ngưỡng an toàn 8–10 workers đồng thời. Luôn chạy cuốn chiếu từng batch để tránh tranh chấp lock và nghẽn bus I/O.

---

## 4. Ràng Buộc Độc Bản Kênh Nguồn Video (Content Duplication Safeguard)

### Hiện Tượng:
- Các tài khoản khác nhau trên các máy khác nhau lại đăng cùng video bài giảng hoặc mang cùng một avatar kênh gốc (ví dụ: kênh "Lớp Toán Thầy Hiếu Live", `@KhánhVyOFFICIAL`, `@Thamdancesports`).

### Nguyên Nhân:
- Tool cào tự động (`download_by_niche.py`) tìm video theo từ khóa của Niche.
- Khi nhiều folder cùng ngách (hoặc khác slot) cào từ YouTube/TikTok, database không có ràng buộc độc bản `source_channel` cho từng folder, dẫn đến việc cùng một kênh nguồn bị tải dồn cho 2-4 folder khác nhau, kéo theo cả file `avatar.jpg` của kênh đó bị nhân bản hàng loạt.

### Ràng Buộc Kỷ Luật:
1. **Cơ sở dữ liệu `state.db`**: Mỗi `source_channel` CHỈ ĐƯỢC PHÉP gán cho duy nhất 1 `folder_num` (`UNIQUE(source_channel)`).
2. **Khi phân bổ video**: Kiểm tra trước trong `folders` và `videos`: nếu kênh đã có mặt ở Folder A thì bắt buộc bỏ qua, tìm kênh khác cho Folder B để đảm bảo mỗi nick trên Farm sở hữu một nguồn content và bộ nhận diện độc bản 100%.

---

## 5. Kỷ Luật Báo Cáo Không Spam (Zero-Chatter & Single End-to-End Report)
- **Chỉ đạo thực tế từ User (18/09/2026)**: *"Báo cáo sau khi chạy xong thôi đừng spam thế"*.
- **Quy tắc bất biến cho Coordinator & Worker**:
  1. **CẤM Chat Tiến Độ Trung Gian**: Khi nhận lệnh thực thi tác vụ nhiều bước (batch run, login GPM, cứu nick, sửa code, dispatch worker), TUYỆT ĐỐI KHÔNG gửi tin nhắn tường thuật trung gian ("Em đang làm bước 1...", "Tôi đã nhận lệnh...", "Đang điều phối worker...", "Chờ tí em đang...").
  2. **Cơ chế [SILENT]**: Trong các lượt trung gian cần gọi công cụ hoặc chờ worker chạy ngầm, Coordinator BẮT BUỘC giữ im lặng tuyệt đối (chỉ dùng `[SILENT]` nếu runtime bắt buộc text).
  3. **DUY NHẤT 1 Báo Cáo Cuối Cùng**: CHỈ gửi 1 tin nhắn tổng kết duy nhất khi TOÀN BỘ luồng tác vụ đã hoàn thành e2e và có kết quả/nghiệm thu thực tế (Mục đích $\rightarrow$ Kết quả $\rightarrow$ Blocker).
  4. **Watchdog & Cron Alerts**: Tránh gửi spam báo cáo lặp lại nếu không có thay đổi trạng thái hoặc không có lỗi mới cần can thiệp.
