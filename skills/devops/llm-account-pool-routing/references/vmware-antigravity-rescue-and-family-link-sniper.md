# VMware Antigravity Rescue, Pre-Login Baseline & Family Link Sniper Architecture

## 1. Google Family / Gemini Pro Store Link Sniper & TTL Invariants

### Cạm Bẫy Thời Gian Sống Của Link (5-8 Phút TTL):
- Các gói link mời gia đình Gemini Pro giá rẻ (9.000đ - 15.000đ) từ các shop tự động (như SumiStore) có thời hạn sống cực ngắn (thường shop chỉ bảo hành trong 5 - 8 phút).
- **Hiện tượng cháy link:** Nếu ném link vào profile bị văng đăng nhập hoặc dính form bảo mật của Google (như bắt xác minh email/số điện thoại khôi phục), link sẽ bị ngâm quá hạn.
- **Bẫy tranh chấp bảo hành ("Tài khoản Pro rồi kìa"):** Khi link quá hạn được mở lại, Google One hiển thị thông báo: *"Gói thuê bao này đã được sử dụng. Đường liên kết của gói thuê bao này đã được sử dụng"*. Người bán nhìn vào dòng chữ này sẽ mặc định cho rằng link đã được kích hoạt thành công cho tài khoản và vin vào cớ *"đã lên Pro và quá 8 phút"* để từ chối bảo hành, dù thực tế tài khoản người mua vẫn là Free Tier.

### Quy Chuẩn Sniper Tức Thì (Zero-Latency Activation):
1. **Preflight Profile Target:** Trước khi nạp tiền/bắn API mua link, BẮT BUỘC kiểm tra profile đích trên GPM:
   - Đã đăng nhập sẵn Google, session sống 100% (mở sẵn tab `one.google.com/home`).
   - Tài khoản sạch, chưa tham gia nhóm gia đình nào.
   - Không bị kẹt checkpoint bảo mật hay form khôi phục.
2. **Kích hoạt tức thời O(1) qua CDP:**
   - Ngay khi API nhả mã đơn và link kích hoạt (`subscription/new/...`):
   - Script bắt link và điều hướng tab GPM đang mở sẵn qua CDP trong vòng $\le 2$ giây.
   - Bắt nút "Kích hoạt gói" tự động trên trang Google One và bấm ngay, dập tắt hoàn toàn rủi ro cháy link.

---

## 2. Quy Chuẩn Nạp Toàn Diện 3 Pool OmniRoute Cho Tài Khoản Pro

Mỗi khi có một tài khoản Google AI Pro (`g1-pro-tier`) mới được kích hoạt hoặc cứu hộ thành công, BẮT BUỘC phải nạp đồng thời vào **CẢ 3 POOL LỚN** của OmniRoute (`storage.sqlite`):

1. **Pool 1 - `ag-gemini-pool-3`:**
   - Model: `antigravity/gemini-3.8-flash-tiered`
   - Gán `connectionId` và nhãn email tương ứng.
2. **Pool 2 - `ag-sonnet`:**
   - Model: `antigravity/claude-sonnet-4-6`
   - Cho phép các tác vụ coding sử dụng Claude Sonnet thông qua quota Pro của tài khoản.
3. **Pool 3 - `ag-opus`:**
   - Model: `antigravity/claude-opus-4-6-thinking`
   - Cho phép các tác vụ suy luận sâu / kiến trúc chạy Claude Opus 4.6.
4. **Tự động thừa hưởng cho `omni-worker`:**
   - Pool điều phối `omni-worker` tham chiếu trực tiếp đến `ag-gemini-pool-3` (Tier 1) và `ag-sonnet` (Tier 4), tự động có thêm tài nguyên mà không cần cấu hình thêm.

### Cấu Hình AGY CLI Sandbox (`D:/Taadaa/agy_profiles/<name>/`):
- Mỗi sandbox mới bắt buộc phải có đủ bộ 5 file chuẩn:
  1. `google_accounts.json`: khai báo `{"active": email, "old": []}`.
  2. `oauth_creds.json`: đồng bộ bộ token OAuth tươi mới.
  3. `settings.json`: `{"security": {"auth": {"selectedType": "oauth-personal"}}}`.
  4. `projects.json`: ánh xạ workspace path.
  5. `state.json`: đếm startup warnings và tips.
- Khai báo proxy di động 1:1 trong `profiles_config.json`.

---

## 3. Kiến Trúc Cứu Hộ VMware: Pre-Login Baseline vs Cold Launch Trap

### Sai Lầm Thiết Kế Hồi Chiều (Cold Launch Trap):
- Khi đưa tài khoản vào máy ảo VMware (`D:\VM\ag-onboard\ag-onboard.vmx`) để cứu hộ:
- Nếu để Antigravity GUI khởi động trước rồi bấm nút `Sign in with Google` $\rightarrow$ Antigravity sẽ mở một cửa sổ Chrome trắng tinh chưa có bất kỳ phiên đăng nhập nào.
- Google nhận diện môi trường máy ảo mới toanh đang cố kết nối OAuth ứng dụng ngoài, lập tức kích hoạt tầng phòng thủ cao nhất: bắt giải reCAPTCHA âm thanh/hình ảnh, soi vân tay và chặn luồng xác thực.

### Thiết Kế Chuẩn: Pre-Login Baseline (Tái Sử Dụng Từ GPM Repo):
Tái sử dụng logic tự động hóa đăng nhập Gmail từ repo GPM (`relogin_chuanh_gpm.py`), đóng gói thành script cứu hộ `vm_prelogin_gmail.py` trong `D:/Taadaa/GPM auto/scripts/antigravity_rescue/`:

1. **Bước 1 (Đọc Thông Tin SoT):**
   - Đọc trực tiếp Password và 2FA Secret từ file quản lý `master_gmail_manager.xlsx` (Sheet `Master_All`).
   - Tự động sinh mã TOTP 6 số theo chuẩn RFC 6238 thời gian thực (Zero Manual OTP).
2. **Bước 2 (Chrome CDP trong Guest):**
   - Khởi chạy Chrome trong máy ảo với cổng `--remote-debugging-port=9222`, mở thẳng `https://accounts.google.com/signin`.
   - Điều khiển tự động: Điền Email $\rightarrow$ Enter $\rightarrow$ Điền Password $\rightarrow$ Enter $\rightarrow$ Điền TOTP 2FA $\rightarrow$ Enter.
   - Chờ Chrome chuyển hướng hoàn tất vào dashboard Google (`myaccount.google.com`).
   - Chụp ảnh màn hình `C:\login_complete.png` trong guest xác nhận đăng nhập thành công.
3. **Bước 3 (Khởi Động Antigravity):**
   - Chỉ khi Chrome đã có sẵn Cookie & Trusted Session sạch, script mới khởi động Antigravity GUI (`lib.launch_antigravity()`).
   - Khi bấm **"Sign in with Google"**, Chrome chỉ hiện bảng **Account Chooser (chọn nick 1 chạm)** và tự động nhảy vào app trong **2 giây**, triệt tiêu vĩnh viễn nguy cơ bị Google chặn reCAPTCHA hay challenge bot!

---

## 4. Xử Lý Lỗi Google 403 `VALIDATION_REQUIRED` (Bypass Challenge)

Khi tài khoản Google One Pro mới kết nối Antigravity lần đầu hoặc đổi refresh token, Google có thể trả về lỗi:
```json
403 PERMISSION_DENIED: "Verify your account to continue." (reason: "VALIDATION_REQUIRED")
```
- **Hiện tượng:** Token cũ chưa mang hạn mức Pro mới, khi gọi `agy cli` báo `RESOURCE_EXHAUSTED 429 - Individual quota reached`.
- **Giải pháp:**
  - Chạy kịch bản Re-authenticate OAuth (`reauth_quyphuoc_gpm.py`):
  - Điều hướng tới endpoint `/api/oauth/antigravity/authorize`, chọn tài khoản trên Account Chooser, bypass màn hình Security Warning ("Đăng nhập").
  - Quá trình này bắt Authorization Code mới và đổi xong bộ token Pro chính thức trong OmniRoute, triệt tiêu mã lỗi `VALIDATION_REQUIRED` mà không cần quét mã QR.
