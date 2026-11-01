# TikTok Lite Multi-Account Sandboxing, Google SSO vs Manual Mail Reg & Anti-Reinvent (2026-11-01)

## 1. Context & Architecture
Trên các thiết bị farm Android (Samsung Galaxy S7, Android 8.0, ROM gốc không root):
- Máy đang chạy đồng thời 8 tài khoản TikTok chính trên package tiêu chuẩn `com.ss.android.ugc.trill`.
- Cần giải quyết bài toán đứt gãy dòng tiền khi bán nick: Nuôi ngâm tích lũy ngày tuổi cho nick non song song mà không chiếm slot hay ảnh hưởng 8 nick chính.
- Package TikTok Lite chính thức duy nhất hiện nay của ByteDance trên Google Play là `com.zhiliaoapp.musically.go` (v47.6.1, ~86MB). Gói cũ `com.ss.android.ugc.trill.go` đã ngừng cập nhật từ bản 3.8.1.

## 2. Experimental Ground Truth: Manual Webmail vs Google SSO

### A. Luồng Gõ Hotmail/Gmail Thủ Công (Instant-Ban Trap)
- Thao tác: Bấm "Sử dụng số điện thoại hoặc email" -> Gõ tay email (`@hotmail.com` hoặc `@gmail.com`) -> Nhập pass -> Con lăn ngày sinh (năm 2000).
- Kết quả thực nghiệm: 
  - Máy 1 (Proxy 20001) với mail `bubarraible...`: Bấm "Tiếp" ngày sinh lập tức nhận popup đỏ: **"Tài khoản của bạn đã bị cấm"** (Instant-Ban) và bị đăng xuất ngay lập tức.
  - Máy 79 (Proxy 20079) với mail sạch `pervisfqh...` (OAuth Graph API LIVE 100%): Kết quả y xì đúc, bị cấm ngay lập tức khi tạo UID.
- Bản chất kỹ thuật: Trên thiết bị phần cứng đã có hồ sơ cày farm (cắm sẵn 8 nick TikTok), luồng đăng ký bằng cách nhập tay webmail không kèm SĐT bị hệ thống Anti-Fraud của TikTok xếp vào diện hành vi bot cào tạo tài khoản rác -> Kích hoạt cơ chế chém trước hỏi sau.

### B. Luồng Google SSO / One-Tap (Thẻ Bài Miễn Tử)
- Thao tác: Trên máy đã có sẵn tài khoản Google LIVE đăng nhập trong OS Android -> Mở TikTok Lite -> Chọn tab "Tôi" -> Bấm **"Tiếp tục với Google"** -> Chọn tài khoản Google từ Google Account Chooser -> Chọn ngày sinh năm 2000 -> Bấm "Tiếp".
- Kết quả thực nghiệm:
  - Máy 78 (Proxy 20078) với `quachdat.online99228@gmail.com`: **THÀNH CÔNG 100%**, sinh username `@manhdatquach`, vào thẳng Profile 0/0/0, hoàn toàn không bị popup cấm, không captcha.
  - Máy 76 (Proxy 20076) với `kimxuanthuy018895@gmail.com`: **THÀNH CÔNG 100%**, sinh username `@xuanthuykim`, vào thẳng Profile 0/0/0.
  - Cả 2 tài khoản kiểm tra lại sau nhiều giờ (cả trên web `tiktok.com/@...` HTTP 200 lẫn mở lại app Lite) đều sống khỏe nguyên vẹn 100%.
- Bản chất kỹ thuật: Google Play Services trên hệ điều hành bảo lãnh danh tính thật cho thiết bị. TikTok nhận diện chứng chỉ OAuth từ Google Sign-In nên Trust Score đạt mức tuyệt đối an toàn, bỏ qua bộ lọc cấm thiết bị.
- **Vấn đề đổi mail sau này**:
  - Tài khoản reg qua Google SSO **hoàn toàn đổi sang Hotmail/Outlook độc lập được**.
  - Quy trình: Sau thời gian ngâm 2-3 tháng tích lũy Trust Score -> Vào Cài đặt & Quyền riêng tư -> Đặt Mật khẩu TikTok riêng -> Đổi Email sang Hotmail và gỡ liên kết Google. Không hề bị trói chết vào Google.

### C. Luồng Canonical TikTok Reg Chuẩn Farm (Login First, Sign-Up Later)
- Khi dùng Hotmail/Outlook, **BẮT BUỘC** phải tuân theo luồng "dương đông kích tây" của `social_reg_v1.py` & `tiktok_reg_live_email_v1.py`:
  1. Mở TikTok lên -> Màn hình Đăng ký xuất hiện -> **BẤM NÚT "ĐĂNG NHẬP" (LOG IN) Ở CHÂN TRANG TRƯỚC** (`choose_email_login` dòng 3620).
  2. Điền email vào ô Đăng nhập -> Bấm Tiếp tục.
  3. TikTok kiểm tra thấy email chưa có trên hệ thống -> Bật thông báo: *"Tài khoản không tồn tại / Bạn chưa có tài khoản? Đăng ký ngay"*.
  4. Lúc này bot mới bấm *"Tạo tài khoản mới / Đăng ký"*.
  5. Giả lập hành vi người dùng thật tưởng mình đã có tài khoản -> Vượt qua bộ lọc bot của ByteDance. **CẤM TUYỆT ĐỐI đi thẳng vào form Sign-Up!**

## 3. Preflight Live Verification Guard Bắt Buộc Trước Khi SSO
- Cạm bẫy phát hiện trên Máy 205: Tài khoản `khong.khai.chien...` reg tối hôm trước bị Google kích hoạt challenge (Verify it's you / Robot check). Khi bấm SSO TikTok Lite, Google Play Services bị kẹt phiên, bung màn hình bắt nhập lại mật khẩu / xác minh danh tính.
- **Quy tắc sống còn:** Mọi tài khoản Google trước khi dùng reg TikTok Lite BẮT BUỘC phải qua kiểm tra Live (qua Google Sign-In lookup hoặc browser CDP probe).
  - Trạng thái `LIVE`: Hiện chữ "Welcome" / "Nhập mật khẩu" -> Đủ điều kiện SSO 1 chạm.
  - Trạng thái `CHALLENGE / DIE`: Bị khóa treo xác minh robot -> Tuyệt đối loại bỏ, không lấy làm SSO.
  - Thời điểm vàng: Nên thực hiện SSO TikTok Lite ngay sau khi reg Gmail thành công trên máy (khi Google session token còn tươi).

## 4. Kỷ Luật Hành Vi Điều Phối: Chống Bại Liệt Khóc Lóc (Anti-Whining Trap) & Cấm Chế Bánh Xe
1. **Cấm viết script ADB bấm tay lẻ tẻ**:
   - Khi có task Auth/Reg/Login TikTok, BẮT BUỘC chạy `python D:/Taadaa/tools/find_existing_logic.py <từ_khóa>` để lấy script canonical có sẵn (`social_reg_v1.py`, `tiktok_reg_live_email_v1.py`, `do_logout_account.py`).
   - Cấm viết các script tạm như `tiktok_lite_enter_email.py`, `tap_email_reg.py` làm bẩn farm và bỏ sót các logic xử lý bẫy của ByteDance.
2. **Kỷ luật chống khóc lóc thoái thác (Anti-Whining Discipline)**:
   - Khi Worker bị Guard chặn (ví dụ: lệnh pytest bị chặn vì metacharacters):
     - **CẤM TUYỆT ĐỐI**: Chuyển sang viết văn xin lỗi, phân trần nhận lỗi dông dài ("Em nhận lỗi sâu sắc trước...", "Em chủ quan..."). Hành vi này bị coi là thoái thác trách nhiệm và bị Receipt Guard đóng dấu vi phạm.
     - **BẮT BUỘC**: Cung cấp nguyên nhân kỹ thuật O(1) cụ thể (Allowlist bị lệch, regex shell quá rộng) và hành động kỹ thuật tiếp theo để mở khóa.
3. **Quy tắc Guard Actionable Guide**:
   - Mọi Guard chặn lệnh kiểm thử (`is_command_safe`) phải trả về cú pháp mẫu chuẩn (`python -m pytest <path> -q`, `py.test <path> -q`) để Worker tự sửa và chạy qua ngay, không được chặn thụ động đẩy Worker vào ngõ cụt.
