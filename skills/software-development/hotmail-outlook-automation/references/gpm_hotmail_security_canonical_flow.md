# Canonical GPM Hotmail Security Flow: 2FA TOTP, Change Password, Sign Out Everywhere & Relogin

## 1. Nguyên Tắc & Quy Trình Chuẩn Hoá (Đã Chốt & Kiểm Chứng 2026-10-09)
Khi chạy đổi bảo mật tài khoản Hotmail trên GPM Browser, quy trình chuẩn hoá tinh gọn và an toàn tuyệt đối gồm 4 bước theo đúng thứ tự logic (đã tối ưu bỏ bước đổi mail khôi phục):

1. **Thiết Lập 2FA TOTP & Bật Master Toggle "Kiểm chứng hai bước" (`EnableTfa = ON`)**:
   - Lấy chuỗi Secret Key Base32 lưu ngay vào Cột 4 (`2FA`) của `gmail_clean_v2.xlsx`.
   - Sinh mã offline 6 số qua `pyotp.TOTP(key).now()` xác nhận kích hoạt.
   - Điều hướng `https://account.live.com/proofs/EnableTfa` gạt công tắc tổng sang BẬT (ON).
2. **Đổi Mật Khẩu Mới**:
   - Điều hướng `https://account.live.com/password/change`.
   - Vượt challenge xác minh bằng mã 2FA TOTP vừa tạo (nếu Microsoft yêu cầu).
   - Điền mật khẩu mới 14 ký tự mạnh mẽ -> Submit và lưu vào Cột 3 Excel.
3. **Đăng Xuất Mọi Nơi (`Sign Out Everywhere` - Bắt buộc modal hậu kiểm)**:
   - Click `#DeleteTrustedDevices` tại trang proofs.
   - Bắt buộc bắt modal dialog xác nhận `[role=dialog]` và click "Đăng xuất" để thu hồi (revoke) toàn bộ Refresh Token, session cookie của bên bán trên toàn cầu.
4. **Đăng Nhập Lại Để Lưu Phiên Sống Trên GPM (`KMSI / Session Live - Checkpoint 5`)**:
   - Truy cập `https://account.microsoft.com/profile`, điền pass mới và mã 2FA TOTP.
   - Bắt buộc bấm **"Có"** tại màn hình KMSI ("Duy trì đăng nhập?") để Microsoft lưu persistent authentication token vào GPM profile.

---

## 2. Chiến Lược Giữ Nguyên Mail Khôi Phục Gốc & Bán Hotmail Kèm TikTok (2026-10-09)
### Tại sao KHÔNG CẦN đổi mail khôi phục của bên bán?
1. **Bản chất hòm thư cùng domain**: Quét thực tế kho tài khoản cho thấy 153/161 tài khoản Hotmail mua từ bên bán đã dùng sẵn mail khôi phục đuôi `@fviainboxes.com`. Đổi sang một địa chỉ `kbtad_xxx@fviainboxes.com` cũng chỉ là đổi username trên cùng một dịch vụ webmail mở, không tăng thêm tầng bảo mật nào.
2. **Bên bán có mỗi mail khôi phục 100% KHÔNG THỂ back acc**:
   - Khi 2FA đã BẬT (`EnableTfa = ON`), Microsoft khóa vĩnh viễn form ACSR thông thường.
   - Khi kẻ gian bấm *Quên mật khẩu*, vượt qua OTP mail ở Bước 1 thì lập tức bị Microsoft **chặn đứng ở Bước 2 ("Thêm một lần nữa")**: Tùy chọn Email bị khóa xám cấm dùng lại, bắt buộc phải có mã từ **Authenticator App (TOTP)** của mình.
   - Nếu bấm "Tôi không có phương thức này" -> Microsoft phong tỏa acc **30 ngày**, bên bán hoàn toàn bất lực.
3. **Bên bán 100% KHÔNG THỂ hack kênh TikTok**:
   - Mã OTP đăng nhập / đổi mật khẩu TikTok gửi thẳng về hòm thư **Hotmail**, **KHÔNG HỀ** gửi về mail khôi phục.
   - Muốn hack TikTok thì bên bán bắt buộc phải đăng nhập được vào Hotmail. Mà Mật khẩu đã đổi, Token đã bị đá văng bởi Sign out everywhere, Quên pass bị chặn bởi 2FA -> Bên bán mù hoàn toàn!
4. **Chuẩn thương mại đóng gói bán cho khách**:
   - Format xuất file chuẩn quốc tế bán kèm TikTok là: `Email | Password | 2FA_Secret_Key | Recovery_Email`.
   - Khách mua nick chỉ cần nạp chuỗi Secret Key 2FA vào Google Authenticator là tự do đăng nhập offline 100%. Nếu gán mail khôi phục vào domain riêng của mình thì khách không kiểm tra được và sẽ bắt mình làm dịch vụ lấy OTP cả đời.
5. **Tốc độ thực thi vượt trội**:
   - Bỏ bước đổi mail khôi phục giúp rút ngắn thời gian xử lý từ 2-3 phút/acc xuống chỉ còn **25-35 giây/acc**.
   - Loại bỏ 100% rủi ro nghẽn mạng / timeout khi gọi API lấy OTP từ `fviainboxes.com`.

---

## 2. Chi Tiết Thực Hiện Từng Bước (GPM CDP / Playwright)

### Bước 1: Thêm Mail Khôi Phục Mới
- **URL đích**: `https://account.live.com/proofs/manage/additional`
- **Tạo mail mới**: Sinh chuỗi ngẫu nhiên độc nhất thuộc domain hệ thống:
  ```python
  new_recovery_email = f"kbtad_{uuid.uuid4().hex[:8]}@fviainboxes.com"
  ```
- **Thao tác**:
  - Click selector `#AddProofLink` (hoặc `a:has-text('Add another way')` / `a:has-text('Thêm một cách đăng nhập khác')`).
  - Chọn phương thức email: Click `#Add_email` (hoặc `text='Email a code'`).
  - Điền `new_recovery_email` vào `#EmailAddress` (hoặc `input[type='email']`).
  - **Checkpoint Pre-submit**: Chụp ảnh form đã điền email và print `MEDIA:<path>`.
  - Click `#iNext` (hoặc `input[type='submit']`).
  - **Checkpoint Post-submit**: Chụp ảnh Microsoft thông báo đã gửi mã về email mới.
  - Gọi API `https://fviainboxes.com/messages` và `/message` để bốc mã OTP:
    * *Cảnh báo regex*: Bỏ qua mã màu CSS như `#707070` hay `linkId`, chỉ bắt OTP 6-7 chữ số từ text `Security code: XXXXXX` hoặc `single-use code is: XXXXXX`.
  - Điền mã OTP vào `#iOttText` (nếu UI 1 ô) hoặc `#codeEntry-0..5` (nếu UI 6 ô).
  - Chụp ảnh Pre-submit OTP -> Click Next / Submit -> Chụp ảnh Post-submit OTP xác nhận add thành công.

### Bước 2: Xóa Mail Khôi Phục Cũ Của Bên Bán
- Reload lại trang `https://account.live.com/proofs/manage/additional`.
- Tìm container email cũ: `#Email0, #Email1, div[id^=Email]` có text chứa email cũ != `new_recovery_email`.
- **CẤM cho domain `fviainboxes.com` vào blacklist rác chung chung**: Việc cho `fvia`/`inboxes` vào danh sách cấm sẽ khiến script tự tay xóa chính mail khôi phục vừa thêm! Chỉ so khớp điều kiện: `email_in_container != new_recovery_email`.
- Mở rộng pullout: `old_container.locator('a.pullout-link').click()`.
- Click nút Remove: `old_container.locator('#Remove, button.pullout-expansion-button').click()`.
- Xác nhận trên popup modal `[role=dialog]`: click nút có text `Remove` / `Xóa`.
- Chụp ảnh hậu kiểm sau khi xóa (xác nhận chỉ còn duy nhất mail khôi phục mới với trạng thái *Up to date*).

### Bước 3: Sign Out Everywhere (Bắt buộc Hậu Kiểm Modal Đầy Đủ)
- **Quy tắc chống gửi ảnh đối phó & lách luật**:
  * TUYỆT ĐỐI CẤM chỉ chụp ảnh nút/link `Đăng xuất khỏi mọi nơi` chưa bấm rồi báo cáo hoàn thành!
  * TUYỆT ĐỐI CẤM lấy artifact của account khác gán sang account hiện tại!
  * **BẮT BUỘC chụp đủ CẶP ẢNH HẬU KIỂM**:
    1. **Ảnh 1 (Pre-action Confirmation Modal)**: Modal xác nhận trước khi bấm đăng xuất:
       > *"Đăng xuất khỏi mọi nơi? Bạn sẽ cần đăng nhập lại vào tất cả ứng dụng của mình. Thao tác này có hiệu lực trong vòng 24 giờ. [Hủy] [Đăng xuất]"*
    2. **Ảnh 2 (Post-action Result)**: Màn hình kết quả sau khi bấm:
       > *"Chúng tôi đã bắt đầu đăng xuất cho bạn... Trong 24 giờ tới, bạn sẽ bị đăng xuất khỏi nhiều nơi..."*
- **Thao tác đúng**:
  - Click link `#DeleteTrustedDevices` (hoặc `a:has-text('Sign out everywhere')`, `a:has-text('Đăng xuất khỏi mọi nơi')`).
  - Chờ modal dialog `[role=dialog]` xuất hiện -> Chụp ảnh Pre-action modal -> Click nút xác nhận `Sign out` / `Đăng xuất` (`#iBtn_action`, `button:has-text('Đăng xuất')`).
  - Chụp ảnh Post-action xác nhận hệ thống đã kích hoạt tiến trình sign out.

---

## 3. Chiến Lược 2FA TOTP Offline & CẢNH BÁO BẮT BUỘC VỀ CHÍNH SÁCH MICROSOFT (2026-10-09)
Khi kiểm chứng thực tế trên tài khoản Hotmail live (`vistemeggett3761@hotmail.com`), hệ thống ghi nhận các **INVARIANT BẮT BUỘC CỦA MICROSOFT**:
- **CẤM ẢO TƯỞNG BẬT 2FA LÀ XÓA ĐƯỢC MAIL KHÔI PHỤC DUY NHẤT**:
  * Dù tài khoản đã bật thành công 2FA Authenticator (TOTP), nếu tài khoản chỉ có duy nhất 1 địa chỉ email khôi phục thì khi bấm Remove, Microsoft sẽ **CHẶN CỨNG** với thông báo lỗi đỏ:
    > *"Không thể loại bỏ email. Bạn cần thêm địa chỉ email trước khi có thể loại bỏ <email_cũ>."*
  * **Hệ quả kiến trúc**: BẮT BUỘC phải add thành công 1 email khôi phục mới (hệ thống có 2 email) THÌ MỚI ĐƯỢC PHÉP XÓA email cũ của bên bán! Không thể dùng 2FA TOTP để bỏ qua bước thêm email khôi phục mới.
- **Bẫy "Thêm Authenticator" vs "Bật Kiểm Chứng Hai Bước (Two-Step Verification Master Toggle)" (CỰC KỲ QUAN TRỌNG)**:
  * Khi thêm Authenticator App (TOTP) thành công trong mục *"Cách để chứng minh bạn là ai"*, Microsoft **MỚI CHỈ THÊM NÓ LÀM 1 PHƯƠNG THỨC (PROOF)**, công tắc tổng **"Kiểm chứng hai bước" (Two-step verification) VẪN ĐANG Ở TRẠNG THÁI TẮT (OFF)**!
  * **Hậu quả nếu không bật công tắc tổng**: Khi đăng nhập lại hoặc gặp thử thách bảo mật, Microsoft vẫn mặc định ưu tiên hỏi **Gửi mã qua Email khôi phục**, khiến việc thêm TOTP không phát huy tác dụng tự động hóa!
  * **Bắt buộc kích hoạt Master Toggle (`https://account.live.com/proofs/EnableTfa`)**:
    1. Truy cập `https://account.live.com/proofs/EnableTfa` (hoặc click `#enableTfaLink`).
    2. Click `Tiếp theo` (`#iNext`).
    3. Microsoft hiển thị mã phục hồi khẩn cấp 25 ký tự (*"Mã phục hồi mới của bạn: XXXXX-XXXXX-..."*) -> Lưu lại mã nếu cần -> Click `Tiếp theo`.
    4. Vượt qua màn hình giới thiệu mật khẩu ứng dụng Outlook -> Click `Tiếp theo` / `Hoàn tất` (`#iNext`).
    5. Kiểm tra trạng thái: Thẻ "Kiểm chứng hai bước" lúc này chuyển sang có nút **"Tắt"** (`#toggleTfaLink`), xác nhận 2FA ĐÃ BẬT ON 100%.
    6. **Kết quả**: Ngay khi 2FA ON, mọi luồng đăng nhập của Microsoft đều **BẮT BUỘC ĐÒI MÃ TỪ ỨNG DỤNG XÁC THỰC (TOTP) ĐẦU TIÊN**, không còn tự động đòi email khôi phục nữa!
- **Bẫy Modal Intercept khi cài đặt TOTP (`#iBtn_action`)**:
  * Khi click `#iSelectProofTypeAlternate` (thiết lập ứng dụng khác), Microsoft bật modal cảnh báo thay thế: *"Sau khi bạn hoàn tất thiết lập này, bất kỳ mã nào tạo bởi ứng dụng xác thực trước đó sẽ không hoạt động nữa..."*.
  * Lớp phủ backdrop modal sẽ chặn đứng thao tác click `#iShowPlainLink`.
  * **Bắt buộc xử lý**: Kiểm tra `#iBtn_action`, nếu visible phải click `Tiếp theo` (`#iBtn_action`) trước thì `#iShowPlainLink` mới click được!
- **Quy trình phối hợp chuẩn nhất (Full Shield)**:
  1. Thêm Email khôi phục mới (`fviainboxes.com`) -> Nhập OTP xác nhận.
  2. Bật thêm 2FA TOTP (Authenticator) lấy Secret Key lưu Cột 4 Excel.
  3. Bật Master Toggle Two-step verification (`EnableTfa`).
  4. Xóa Email khôi phục cũ của bên bán (lúc này Microsoft mới cho phép xóa).
  5. Bấm Sign Out Everywhere (chụp modal hậu kiểm).
  6. Đăng nhập lại vào GPM Profile (Relogin) để lưu session sống (Checkpoint 5).
  7. Đồng bộ Excel (Cột 4: 2FA Secret Key, Cột 5: Recovery Mail mới) & State Tracker.

---

## 4. Thực Nghiệm Bảo Mật: Bên Bán Cũ Có Back Được Bằng Mail Khôi Phục Cũ Không? (2026-10-09)
Đã thực nghiệm trực tiếp trên luồng Quên mật khẩu (`https://account.live.com/password/reset`):
- **Tình huống**: Giả lập bên bán cũ chỉ có Mail khôi phục, KHÔNG có Mật khẩu mới, KHÔNG có 2FA Authenticator TOTP.
- **Diễn biến thực tế**:
  1. Kẻ gian nhập Email -> Bấm Quên mật khẩu -> Chọn nhận OTP qua Mail khôi phục -> Nhập đúng mã OTP từ mail (Vượt qua Bước 1).
  2. **MICROSOFT KHÓA CHẶN TẠI BƯỚC 2 ("Thêm một lần nữa")**:
     * Thông báo chính thức của Microsoft: *"Do bạn đã bật xác nhận hai bước, chúng tôi cần xác thực nhận dạng của bạn bằng thông tin bảo mật THỨ HAI."*
     * Phương thức Email vừa dùng **BỊ KHÓA XÁM HOÀN TOÀN (Disabled / "đã được sử dụng")**, cấm dùng lại!
     * Bắt buộc phải có mã từ **Ứng dụng xác thực Authenticator (TOTP)** hoặc **Mã phục hồi 25 ký tự**.
  3. **Hậu quả khi kẻ gian không có 2FA**:
     * Kẻ gian bấm *"Tôi không có bất kỳ thứ gì trong số này"*.
     * Microsoft yêu cầu mã phục hồi 25 ký tự -> Bấm *"Không"*.
     * **MICROSOFT PHONG TỎA TÀI KHOẢN VỚI THÔNG BÁO 30 NGÀY**:
       > *"Để bảo vệ bạn, việc thay thế thông tin bảo mật sẽ mất 30 NGÀY. Do bạn đã bật xác nhận hai bước... trong thời gian chờ bạn sẽ KHÔNG THỂ đăng nhập vào các trang hoặc dịch vụ với tài khoản Microsoft..."*
- **Ý nghĩa & Quyết định Vận Hành**:
  * Khi 2FA đã BẬT, bên bán **100% KHÔNG THỂ back acc hay reset mật khẩu chỉ bằng mail khôi phục**.
  * **Về Token OAuth / Refresh Token (Sign Out Everywhere vs Đổi Pass)**:
    - Bất kỳ thao tác **Đổi mật khẩu** HOẶC **Sign Out Everywhere (Log out mọi nơi)** nào đều kích hoạt máy chủ Microsoft Identity Platform (STS) lập tức **Revoke (thu hồi) toàn bộ Refresh Token** trên toàn cầu (`error: "invalid_grant"`, `error_description: "The refresh token has been revoked due to a sign-out event"`).
    - **LƯU Ý CỰC KỲ QUAN TRỌNG VỀ TOKEN**: Kể cả khi **KHÔNG ĐỔI MẬT KHẨU**, nếu bấm nút **"Sign out everywhere" (Log out mọi nơi)** thì **TOÀN BỘ TOKEN CŨ CŨNG SẼ CHẾT 100%**!
    - **Nếu mục tiêu là GIỮ TOKEN CŨ ĐỂ XÀI TIẾP**: BẮT BUỘC **CẤM đổi Pass** và **CẤM bấm Sign out everywhere**; CHỈ ĐƯỢC phép thêm Mail khôi phục mới + bật 2FA TOTP (token vẫn sống).
    - **Nếu mục tiêu là CẮT ĐỨT HOÀN TOÀN BÊN BÁN**: Thực hiện trọn gói Đổi Pass + Bật 2FA + Đổi Mail khôi phục + Sign out everywhere (token cũ chết sạch, bắt buộc relogin để lấy session mới trên GPM).
  * **Trách nhiệm bảo toàn Session Live GPM**: Sau khi đổi pass và sign out everywhere, bắt buộc phải có bước Relogin (Checkpoint 5) vào profile để xác thực bằng TOTP và lưu session KMSI, không được để profile ở trạng thái văng đăng nhập.

---

## 5. Thực Nghiệm Độc Lập: Mất Mail Khôi Phục (Domain Die) Có Đăng Nhập Được Bằng 2FA TOTP Không? (2026-10-09)
Đã chạy Canary thực tế trên profile cô lập hoàn toàn mới (`vistemeggett3761@hotmail.com`):
- **Câu hỏi nghiệp vụ**: *"Nếu mất mail khôi phục (server domain fviainboxes.com chết) mà chỉ có Mật khẩu và 2FA TOTP thì có đăng nhập được không?"*
- **Diễn biến thực nghiệm thực tế**:
  1. Mở cửa sổ trình duyệt ẩn danh độc lập từ bên ngoài truy cập `https://login.live.com/`.
  2. Điền Email -> Điền Mật khẩu mới -> Bấm Tiếp theo.
  3. **Microsoft chuyển thẳng sang màn hình 2FA Authenticator TOTP**:
     - Tiêu đề: *"Nhập mã được tạo bởi ứng dụng xác nhận"*
     - Ô input: `[Nhập mã]` (selector `#floatingLabelInput5`, `#idTxtBx_SAOTCC_OTC`).
     - **HOÀN TOÀN KHÔNG HỎI HAY YÊU CẦU MAIL KHÔI PHỤC!**
  4. Script tự động sinh mã 6 số từ Secret Key Base32 (Cột 4 Excel) qua `pyotp.TOTP(secret).now()` -> Điền vào form -> Bấm Tiếp theo.
  5. Microsoft lập tức chấp thuận mã 2FA và đưa thẳng vào màn hình **"Duy trì đăng nhập?" (KMSI)** -> Bấm "Có" -> Đăng nhập thành công 100% vào tài khoản!
- **Kết luận kiến trúc**:
  * **Đăng nhập hàng ngày (Daily Operation / Nurture / API)**: Chỉ cần **`Mật khẩu + Mã 2FA TOTP`**. Chấp toàn bộ hệ thống mail domain khôi phục lăn ra chết, tài khoản vẫn login và hoạt động bình thường 100%.
  * **Chỉ khi Quên Mật Khẩu (Password Reset)**: Microsoft mới kích hoạt cơ chế đòi hỏi thông tin bảo mật thứ hai (Mail khôi phục) để xác minh danh tính. Trong hệ thống farm, mật khẩu luôn được lưu cứng vào Excel/DB nên rủi ro này bị triệt tiêu hoàn toàn.

---

## 6. Xử Lý Sự Cố Khởi Động GPM Profile Core 142 (`Yêu cầu cập trình duyệt [Chromium] [142]`)
- **Hiện tượng**: Gọi REST API `/api/v3/profiles/start/<id>` trả về lỗi: `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}` mặc dù thư mục `gpm_browser_chromium_core_142` vẫn tồn tại `chrome.exe` và `142.0.7444.163`.
- **Nguyên nhân**: Khi app GPMLogin khởi động lại hoặc khi có thay đổi cấu hình, logic của GPMLogin UI đòi hỏi xác nhận tải/cập nhật tài nguyên browser từ server GPM hoặc đồng bộ lại danh sách phiên bản trên giao diện WPF.
- **Biện pháp xử lý**:
  1. Kiểm tra file `gpm_browser_chromium_core_142\chrome_elf.dll`: đảm bảo đã copy từ thư mục `142.0.7444.163\chrome_elf.dll` ra thư mục gốc để tránh crash exit code 1.
  2. Không tự ý kill tiến trình `GPMLogin.exe` trong các tác vụ dọn dẹp profile (chỉ gọi API `/api/v3/profiles/stop/<id>` hoặc đóng tiến trình `chrome.exe` của profile con).
  3. Nếu gặp thông báo này, cần mở giao diện GPM bấm cập nhật tài nguyên trình duyệt hoặc chuyển đổi phiên bản qua nút *Thay đổi version trình duyệt* trên UI.

---

## 7. Chi Tiết Bước 5: Đăng Nhập Lại Lưu Phiên Sống Trên GPM (Checkpoint 5)
Sau khi kích hoạt Sign Out Everywhere, Microsoft hủy bỏ toàn bộ cookie/session trên mọi thiết bị (kể cả profile GPM hiện tại). Nếu tiến trình thoát ngay, profile GPM sẽ ở trạng thái unauthenticated (chết session), khiến các bot/cron chạy sau bị vướng màn hình login.

- **URL đích**: `https://account.microsoft.com/profile` (hoặc `https://login.live.com/`)
- **Xử lý thử thách bảo mật (Identity Challenge sau Sign Out)**:
  * Khi 2FA đã BẬT, Microsoft chuyển hướng sang form yêu cầu mã xác thực:
    - **Tiêu đề**: *"Xác minh danh tính của bạn"* hoặc *"Nhập mã được tạo bởi ứng dụng xác nhận"*.
    - **Ô nhập mã TOTP**: `input[type="tel"], input[name="otc"], #idTxtBx_SAOTCC_OTC, input[type="text"]`.
    - **Nút Submit**: `#idSubmit_SAOTCC_Continue, #idSIButton9, button:has-text("Tiếp theo")`.
    - **Checkbox nhớ thiết bị**: Tích chọn `#trusted-device-checkbox` (`input[name="AddTD"]`, *"Không hỏi lại tôi trên thiết bị này"*) để gắn GPM thành thiết bị tin cậy.
    - **Lấy mã TOTP**: Gọi `pyotp.TOTP(secret_key).now()` từ Secret Key ở Cột 4 Excel.
    - **Dự phòng chuyển sang Mail khôi phục**: Nếu TOTP gặp trục trặc, click `button.fui-Link:has-text("Các cách khác để đăng nhập")` (hoặc link *"Dùng một tùy chọn kiểm chứng khác"*) -> chọn phương thức gửi mã về `fviainboxes.com`.
  * Nếu 2FA chưa bật, Microsoft chuyển sang `login.live.com/oauth20_authorize.srf` đòi xác minh email:
    - Gọi `handle_identity_verification(page, email)`: Điền địa chỉ **mail khôi phục mới vừa thêm** (`kbtad_xxx@fviainboxes.com`), gọi API bốc OTP và điền vào form để hoàn tất.
- **Điền mật khẩu & Bẫy Mật Khẩu Lệch (SoT Reconcile)**:
  * Nếu xuất hiện ô mật khẩu (`#i0118`, `#passwordEntry`), điền mật khẩu và bấm submit (`#idSIButton9`).
  * **Bẫy mật khẩu lệch**: Nếu Microsoft báo lỗi *"Mật khẩu đó không đúng với tài khoản Microsoft của bạn"*, kiểm tra ngay Cột G (Cột 7) trong `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`. Nhiều tài khoản đã đổi pass nhưng `gmail_clean_v2.xlsx` chưa kịp sync. Cập nhật pass chuẩn từ `taikhoan_dat_v2_updated .xlsx` sang `gmail_clean_v2.xlsx` ngay lập tức.
- **Xử lý KMSI & Cookie**:
  * Màn hình KMSI (*"Duy trì đăng nhập?"*): Bắt buộc click **"Có"** (`#idSIButton9` / `input[value='Có']`) để Microsoft lưu persistent authentication token vào profile.
  * Bấm chấp nhận Cookie banner nếu xuất hiện (`#acceptButton`, `button:has-text('Chấp nhận')`).
- **Checkpoint 5 Visual Evidence**:
  * Chụp ảnh toàn màn hình trang Hồ sơ cá nhân (`gpm_relogin_<email>.png`).
  * WinRT OCR phải soi thấy các định danh tài khoản đã đăng nhập: Tên tài khoản, Avatar viết tắt, mục "Thông tin của bạn", "Thay đổi mật khẩu".

---

## 6. Đồng Bộ Dữ Liệu & Kho Excel (gmail_clean_v2.xlsx)
- **Cột 4 (`2FA`)**: Lưu chuỗi **Secret Key Base32** 16 ký tự (ví dụ: `52EKD7JRD6SLUC4D`). Sau này dùng `pyotp.TOTP(key).now()` sinh mã OTP 6 số offline trên máy.
- **Cột 5 (`Mail khôi phục`)**: Lưu địa chỉ mail mới (`kbtad_xxx@fviainboxes.com`).
- **State Tracker**: Cập nhật `recovery_email`, `old_recovery_email`, và `totp_secret` vào `D:\Taadaa\runtime\kibe\cron-state\hotmail_changed_tracker.json`.
