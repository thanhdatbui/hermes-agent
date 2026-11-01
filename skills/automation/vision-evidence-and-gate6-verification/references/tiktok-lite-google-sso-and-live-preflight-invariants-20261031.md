# TikTok Lite Farm Coexistence, Google SSO Invariant & Live Mail Preflight

## 1. Bản Chất Kỹ Thuật (TikTok Main vs TikTok Lite)
- **Coexistence An Toàn:** TikTok Lite (`com.zhiliaoapp.musically.go`) và TikTok Chính (`com.ss.android.ugc.trill`) là 2 package độc lập, có sandbox dữ liệu riêng biệt trên Android. Cài Lite lên thiết bị đang chạy 8 nick TikTok chính không gây mất phiên hay suy suyển dữ liệu TikTok chính.
- **Mục Đích Farm:** Cài TikTok Lite để reg ngâm 1 nick phụ tích lũy ngày tuổi (3 tháng) song song với ca nuôi của 8 nick chính, giải quyết đứt gãy dòng tiền khi xuất bán nick.

## 2. Sự Khác Biệt Sống Còn: Gõ Hotmail Thủ Công vs Google SSO
- **Luồng Gõ Hotmail Thủ Công = Instant-Ban 100%:**
  - Trên thiết bị farm đã cắm 8 nick chính, gõ tay Hotmail mua sỉ bị thuật toán ByteDance Anti-Fraud xếp vào diện bot tạo rác.
  - Vừa chọn xong ngày sinh ➔ Bị cấm ngay lập tức: `"Tài khoản của bạn đã bị cấm"` (Thử trên cả máy nick già M1 và máy nick non M79 đều dính án phạt như nhau).
- **Luồng Google One-Tap SSO = Success 100% (Thẻ Bài Miễn Tử):**
  - Mở TikTok Lite ➔ Chọn "Tiếp tục với Google" ➔ Chọn tài khoản Google có sẵn trên máy.
  - Google Play Services đứng ra bảo lãnh danh tính thật ➔ Vượt qua bộ lọc thiết bị cày farm, bỏ qua bước nhập mật khẩu, vào thẳng profile sống nguyên vẹn (Đã nghiệm thu trên M78 `@manhdatquach` và M76 `@xuanthuykim`).

## 3. Preflight Live Check Bắt Buộc Trước Khi SSO
- **Cạm Bẫy Session Ngầm Của Google:**
  - Không được bốc bừa Gmail trên máy để bấm SSO.
  - Nếu Gmail mới tạo quá 24h hoặc đang bị Google treo Challenge/Verify robot (như M205 `khong.khai.chien...`), Google Play Services sẽ bung màn hình đòi xác minh danh tính/nhập lại mật khẩu, làm nghẽn automation.
- **Quy Tắc Vận Hành:**
  1. Chỉ dùng Gmail vừa reg xong trong ca (Google session còn tươi 100%) hoặc Gmail đã qua preflight live check qua Google Sign-In (trả về `Welcome` + ô Password).
  2. Tuyệt đối không chọn Gmail dính `Verify it's you / Robot Challenge`.

## 4. Tránh Bại Liệt Khi Bị Guard Chặn (Actionable Gate Invariant)
- **Không Khóc Lóc/Phân Trần:** Khi lệnh sửa code hoặc kiểm thử bị Guard từ chối, CẤM mở mồm phân trần, xin lỗi hoặc hứa hẹn mà không có tool call thực tế (sẽ bị `Receipt Guard` đóng dấu `CHƯA CÓ WORKER NÀO CHẠY THẬT`).
- **Sửa Guard Thay Vì Sửa Worker:** Khi Worker bị chặn lệnh test `pytest` do nghi ngờ metacharacters, không tăng turns hay ép prompt, mà mở rộng allowlist hẹp (cho phép `py.test`, `python -m pytest <path> -q`) và bổ sung `Actionable Guide` (trả về lệnh mẫu hợp lệ) để Worker tự động phục hồi trong 1 turn duy nhất.
