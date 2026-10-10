# Canonical GPM Hotmail Security Flow: 2FA TOTP, Change Password, Sign Out Everywhere & Relogin

## 1. Nguyên Tắc & Quy Trình Chuẩn Hoá (Đã Chốt & Kiểm Chứng 2026-10-10)
Khi chạy đổi bảo mật tài khoản Hotmail trên GPM Browser, quy trình chuẩn hoá tinh gọn và an toàn tuyệt đối gồm 4 bước theo đúng thứ tự logic (đã tối ưu bỏ bước đổi mail khôi phục):

```text
GPM CDP Connect 
       │
       ▼
[BƯỚC 1]: THIẾT LẬP 2FA TOTP (AUTHENTICATOR APP) TRƯỚC
       ├─ Điều hướng https://account.live.com/proofs/manage/additional
       ├─ Kiểm tra nếu chưa có 2FA -> Thêm Authenticator App
       ├─ Lấy Secret Key Base32 -> Lưu ngay vào Cột 4 (2FA) trong Excel
       ├─ Sinh mã 6 số offline (pyotp) xác nhận kích hoạt
       └─ Kích hoạt công tắc tổng Two-step verification (EnableTfa = ON)
       │
       ▼
[BƯỚC 2]: ĐỔI MẬT KHẨU MỚI
       ├─ Điều hướng https://account.live.com/password/change
       ├─ Giải challenge 2FA nếu có (dùng ngay mã TOTP vừa tạo)
       ├─ Điền mật khẩu mới 14 ký tự mạnh mẽ
       └─ Submit đổi mật khẩu -> Lưu Mật khẩu vào Cột 3 Excel (và Cột G taikhoan_dat_v2)
       │
       ▼
[BƯỚC 3]: SIGN OUT EVERYWHERE (ĐĂNG XUẤT KHỎI MỌI NƠI)
       ├─ Điều hướng https://account.live.com/proofs/manage/additional
       ├─ Click #DeleteTrustedDevices
       ├─ Bắt modal dialog -> Xác nhận "Đăng xuất"
       └─ Thu hồi toàn bộ token, cookie, session của bên bán trên toàn cầu
       │
       ▼
[BƯỚC 4]: ĐĂNG NHẬP LẠI DUY TRÌ PHIÊN (RELOGIN LIVE TRÊN GPM)
       ├─ Điều hướng https://account.microsoft.com/profile
       ├─ Điền Email + Mật khẩu mới
       ├─ Tự động điền mã 2FA TOTP offline
       ├─ Bấm "Có" tại màn hình KMSI ("Duy trì đăng nhập?") để lưu sống cookie
       └─ Hoàn tất lưu session vào GPM Profile
```

---

## 2. Chiến Lược Giữ Nguyên Mail Khôi Phục Gốc & Bán Hotmail Kèm TikTok (2026-10-10)
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

## 3. Khắc Phục Tận Gốc Sự Cố Khởi Động GPM Profile Core 142 (`Yêu cầu cập trình duyệt [Chromium] [142]`)
- **Hiện tượng**: Gọi REST API `/api/v3/profiles/start/<id>` trả về lỗi: `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}` mặc dù thư mục `gpm_browser_chromium_core_142` đã có `chrome.exe` và `142.0.7444.163`.
- **Nguyên nhân cốt lõi trong GPMLogin binary**:
  * GPMLogin kiểm tra 2 điều kiện tại thư mục core `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142`:
    1. Phải tồn tại file `data-variations.gpm`.
    2. File `version` phải mang giá trị `1.1` (trước đó là `1.0` nên GPMLogin coi là tài nguyên cũ/chưa hoàn tất).
- **Lệnh sửa triệt để (Programmatic Fix 1 giây)**:
  ```bash
  python -c "
  import shutil
  src = r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\default\data-variations.gpm'
  dst = r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\data-variations.gpm'
  shutil.copy2(src, dst)
  with open(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\version', 'w') as f:
      f.write('1.1')
  print('Core 142 updated to 1.1 successfully!')
  "
  ```
  Sau khi chạy lệnh trên, API `/api/v3/profiles/start` lập tức trả về `success: true` và cung cấp cổng CDP bình thường.

---

## 4. Kỷ Luật Chạy Canary: Phải Chạy Full Flow Thật (`--canary --live`)
- **Pitfall nghiêm trọng**: Chạy lệnh `python gpm_change_hotmail_security.py --email ... --canary` mà **quên `--live`** sẽ chỉ là dry-run (dừng trước nút Save, không đổi mật khẩu thật, không sign out thật).
- **Kỷ luật người dùng**: Khi user bảo **"Chạy canary đi"**, mục đích là kiểm chứng end-to-end hoàn chỉnh cả vòng đời trên 1 account mẫu để nghiệm thu kết quả thực tế.
- **Lệnh bắt buộc**:
  ```bash
  python "D:/Taadaa/Hotmail/scripts/gpm_change_hotmail_security.py" --email "<email_muc_tieu>" --canary --live
  ```
- **Hậu kiểm**: Kiểm tra đồng bộ cả 2 file Excel (`gmail_clean_v2.xlsx` và `taikhoan_dat_v2_updated .xlsx`), đảm bảo mật khẩu mới và Secret Key 2FA đã được lưu cứng.

---

## 5. Bẫy Tên Sheet Giữa 2 File Excel Kho Dữ Liệu
- **`taikhoan_dat_v2_updated .xlsx`**: Tên sheet là `'Tài Khoản'`.
  * Cột A (1): Máy
  * Cột F (6): Email Hotmail
  * Cột G (7): PASS MAIL
- **`gmail_clean_v2.xlsx`**: Tên sheet là `'Gmail Accounts'` (KHÔNG PHẢI `'Tài Khoản'`).
  * Gọi `wb['Tài Khoản']` trên file này sẽ văng crash: `KeyError: 'Worksheet Tài Khoản does not exist.'`.
  * Cột B (2): Email
  * Cột C (3): PASS
  * Cột D (4): 2FA Secret Key Base32
  * Cột E (5): Recovery Email gốc
- **Kỷ luật code**: Luôn dùng logic an toàn `ws = wb['Gmail Accounts'] if 'Gmail Accounts' in wb.sheetnames else (wb['Tài Khoản'] if 'Tài Khoản' in wb.sheetnames else wb.active)`.

---

## 6. Xử Lý Challenge 2FA & KMSI Khi Đăng Nhập Lại (Relogin Handler)
- **Hiện tượng**: Sau khi bấm `Sign out everywhere`, phiên cũ bị revoke hoàn toàn. Khi script truy cập `account.microsoft.com/profile` để relogin bằng mật khẩu mới, Microsoft lập tức dựng form challenge 2FA đòi mã từ Authenticator App (`#idTxtBx_SAOTCC_OTC`).
- **Xử lý tự động**:
  * Bắt selector `#idTxtBx_SAOTCC_OTC` hoặc input OTC, lấy Secret Key vừa tạo (hoặc tra cứu từ Cột 4 Excel).
  * Dùng `pyotp.TOTP(sec_key).now()` sinh mã và điền tự động.
  * Chụp ảnh `gpm_relogin_totp_<email>.png` làm bằng chứng.
  * Tiếp tục bắt màn hình KMSI ("Duy trì đăng nhập?"), chụp ảnh `gpm_kmsi_<email>.png` rồi click `#idSIButton9` (nút [Có]) để lưu cookie lâu dài vào GPM Profile.
- **Kỷ luật báo cáo bằng chứng (Bắt buộc đủ 5 Chặng Visual Evidence, Cấm Làm Nửa Vời)**:
  * User cực kỳ dị ứng với việc báo cáo thiếu bước hoặc làm nửa chừng ("bước sign out sign in lại đâu sao cứ làm đéo đủ v"). Khi kiểm chứng Canary / đổi info Hotmail, BẮT BUỘC cung cấp đủ 5 chặng ảnh:
    1. *Add 2FA*: Form cấp key + điền mã 6 số kích hoạt (`evidence_1_add_2fa.png`).
    2. *Đổi Pass*: Form đổi pass + nút Lưu (`evidence_2_change_pass.png`).
    3. *Sign out everywhere*: Modal dialog xác nhận đăng xuất (`evidence_3_signout_dialog.png`).
    4. *Relogin 2FA*: Form giải mã TOTP khi đăng nhập lại (`evidence_4_relogin_totp.png`).
    5. *KMSI*: Màn hình "Duy trì đăng nhập?" bấm [Có] để lưu phiên sống (`evidence_5_kmsi_yes.png`).
  * **Chọn acc Canary**: Khi user bảo "canary acc khác", BẮT BUỘC chọn acc **chưa từng có 2FA** (`Col 4 is None`) để thể hiện đủ cả 5 bước. Nếu acc đã có 2FA mà script skip bước tạo key sẽ khiến user hiểu nhầm là tool chạy thiếu/lỗi.
  * **Kích hoạt form Relogin**: Sau khi Sign out everywhere, điều hướng qua `https://login.live.com/logout.srf` rồi mới vào `account.microsoft.com/profile` để xóa cookie cục bộ, buộc Microsoft hiện form đăng nhập lại để chụp ảnh relogin + 2FA + KMSI.
  Tuyệt đối không được báo cáo kết quả chung chung mà thiếu ảnh của bất kỳ chặng nào.

---

## 8. Bẫy Playwright CDP Sau Khi Submit Form Đổi Mật Khẩu (Navigation Race Condition)
- **Hiện tượng**: Bấm submit nút `#save` hoặc `#UpdatePasswordAction` xong, gọi ngay `page.content()` để kiểm tra thông báo lỗi thì Playwright văng exception:
  `[-] Lỗi trong quá trình thao tác CDP/Playwright: Page.content: Unable to retrieve content because the page is navigating and changing the content.`
- **Nguyên nhân**: Ngay khi click Lưu, Microsoft lập tức điều hướng trang (active navigation). Playwright không cho phép đọc DOM qua `page.content()` khi trang đang trong quá trình chuyển hướng.
- **Cách xử lý chuẩn**:
  ```python
  try:
      page.wait_for_load_state("domcontentloaded", timeout=5000)
      page_content = page.content()
      if any(err_msg in page_content for err_msg in err_patterns):
          raise RuntimeError("Microsoft từ chối đổi mật khẩu: mật khẩu không hợp lệ.")
  except Exception as e_cnt:
      log(f"Kiểm tra nội dung trang sau đổi pass (an toàn trước navigation): {e_cnt}")
  ```
- **Selector linh hoạt cho form đổi mật khẩu**:
  * Ô mật khẩu hiện tại (có thể không xuất hiện nếu vừa re-auth): `#currentPassword, input[name='CurrentPassword']`.
  * Ô mật khẩu mới: `#iPassword, #newPassword, #newPasswordInput, input[name='Password']`.
  * Ô xác nhận mật khẩu: `#iRetypePassword, #confirmPassword, #confirmPasswordInput, input[name='RetypePassword']`.
  * Ô nhập mã 2FA TOTP: `#iVerifyText` (thường là type `number`, placeholder `Nhập mã`) hoặc `#idTxtBx_SAOTCC_OTC`.

---

## 9. Cảnh Báo "Tạm Thời Có Lỗi Với Dịch Vụ", Kỷ Luật Fail-Fast & Báo Cáo Minh Bạch (2026-10-10)
- **Bắt lỗi "Tạm thời có lỗi với dịch vụ" & Bẫy Silent Try/Except**:
  * Khi bấm Lưu đổi mật khẩu, nếu Microsoft trả về thông báo:
    `Tạm thời có lỗi với dịch vụ. Xin vui lòng thử lại...` (hoặc `There's a temporary problem with the service. Please try again...`)
    thì **MẬT KHẨU CHƯA ĐƯỢC ĐỔI THẬT TRÊN MÁY CHỦ MICROSOFT**!
  * **CẤM TUYỆT ĐỐI bọc kiểm tra này trong khối `try...except` bắt lỗi im lặng**: Nếu chỉ log warning mà không raise exception ngắt flow, script sẽ chạy tiếp các bước sau và ghi đè pass mới vào Excel $\rightarrow$ gây mất đồng bộ dữ liệu nghiêm trọng, tài khoản trên Microsoft vẫn pass cũ nhưng Excel ghi pass mới!
  * **KỶ LUẬT BÁO CÁO MINH BẠCH VỚI USER**:
    * Khi gặp lỗi đổi pass, Coordinator BẮT BUỘC phải thông báo ngay lập tức cho User biết tài khoản chưa đổi được mật khẩu kèm lý do thực tế. CẤM TUYỆT ĐỐI ỉm lỗi, báo cáo chung chung hoặc báo cáo "thành công" khi thực tế mật khẩu chưa đổi được.
  * **Cơ chế Fail-Fast Bắt Buộc Trong Code**:
    ```python
    page_content = page.content()
    err_patterns = [
        "Mật khẩu của bạn không được chứa",
        "Your password cannot contain",
        "Mật khẩu quá ngắn",
        "Mật khẩu không khớp",
        "Tạm thời có lỗi với dịch vụ",
        "There's a temporary problem with the service",
        "Xin vui lòng thử lại",
        "Please try again",
    ]
    for err_msg in err_patterns:
        if err_msg.lower() in page_content.lower():
            raise RuntimeError(f"Microsoft từ chối đổi mật khẩu: phát hiện '{err_msg}'. DỪNG NGAY KHÔNG GHI EXCEL!")
    ```
- **Lọc Tiền Điều Kiện Kho Tài Khoản (Prerequisite Gate: RecMail != None)**:
  * Trong `gmail_clean_v2.xlsx`, các tài khoản được chia làm 2 nhóm:
    1. *Nhóm có mail khôi phục (324 acc, có 137 acc khớp profile GPM)*: Đã có phương thức bảo mật chứng minh danh tính $\rightarrow$ Microsoft cho phép đổi pass và thêm 2FA mượt mà 100% (ví dụ: `vistemeggett3761`).
    2. *Nhóm chưa có mail khôi phục (220 acc, Cột 5 = None)*: Microsoft nghi ngờ phiên truy cập bất thường và chặn cứng với câu `"There's a temporary problem with the service"` khi vào form đổi pass trực tiếp.
  * **Quy tắc chọn mục tiêu**: Khi chạy batch hoặc chọn acc Canary, BẮT BUỘC chỉ lọc các tài khoản đã có sẵn mail khôi phục hợp lệ (`Col 5 is not None`) để tránh tỷ lệ fail 100% do thiếu bằng chứng bảo mật.
- **Quy Trình Rollback Dữ Liệu Khi Gặp Sự Cố**:
  * Nếu phát hiện lỗi đổi pass không thành công trên Microsoft, Coordinator BẮT BUỘC kiểm tra và khôi phục (rollback) ngay lập tức giá trị mật khẩu gốc trong cả 2 file:
    - `taikhoan_dat_v2_updated .xlsx` (Cột G - PASS MAIL).
    - `gmail_clean_v2.xlsx` (Cột 3 - PASS).
  * Đồng thời dọn sạch bản ghi lỗi trong runtime state (`hotmail_changed_tracker.json`). Không để rác mật khẩu ảo.
- **Thực Tế Dual OAuth Gating Trên Hotmail**:
  * Trong kho Hotmail, chỉ có 5 tài khoản đã sync đồng thời lên cả OmniRoute (`:20129`) VÀ 9Router (`:20128`).
  * Các tài khoản còn lại (như 23 acc ở rows 317-529) chỉ có OAuth trên OmniRoute (`:20129`).
  * Khi vận hành batch, cần đối chiếu rõ cổng gating để tránh bị chặn toàn bộ tài khoản hợp lệ.
- **Selector chọn "Sử dụng ứng dụng" trong menu Thêm cách đăng nhập mới & Đa Ngôn Ngữ EN/VI**:
  * Khi click `#AddProofLink` ("Thêm một cách đăng nhập khác cho tài khoản" / "Add another way to sign in"), giao diện có thể là tiếng Việt hoặc tiếng Anh:
    - Tiếng Việt: `text='Sử dụng ứng dụng'`, nút `Tiếp theo`, `Hoàn tất`, `Lưu`, `Đăng xuất`, `Có`.
    - Tiếng Anh: `text='Use an app'`, nút `Next`, `Finish`, `Save`, `Sign out`, `Yes`.
  * Bộ selector chuẩn hoá hỗ trợ song ngữ:
    - Add link: `locator("#AddProofLink, a:has-text('Thêm một cách đăng nhập khác'), a:has-text('Add a new way to sign in'), a:has-text('Add another way to sign in'), a:has-text('Add another way')")`
    - App button: `locator("#Add_msAuthApp, a:has-text('Sử dụng ứng dụng'), div:has-text('Sử dụng ứng dụng'), a:has-text('Use an app'), div:has-text('Use an app')")`
    - EnableTfa: `locator("#iNext, input[value='Tiếp theo'], button:has-text('Tiếp theo'), input[value='Hoàn tất'], button:has-text('Hoàn tất'), input[value='Next'], button:has-text('Next'), input[value='Finish'], button:has-text('Finish')")`
    - Save pass: `locator("#UpdatePasswordAction, input[value='Lưu'], button:has-text('Lưu'), input[value='Save'], button:has-text('Save'), #save, #idSubmit_SAV_btnSubmit")`
  * Ô đổi mật khẩu `#iPassword`, `#iRetypePassword` bắt buộc `.click()` để nhận focus trước khi `.fill()` nhằm kích hoạt input event của Microsoft.
* Kỷ luật báo cáo Canary tài khoản mới:
* Khi user yêu cầu "canary acc khác t coi", user kỳ vọng **nghiệm thu thực tế toàn diện**.
* BẮT BUỘC gửi ngay 4 chặng ảnh chứng minh trong cùng 1 báo cáo:
  1. Ảnh nhập mã kích hoạt 2FA Authenticator (`gpm_totp_pre` / Proofs).
  2. Ảnh điền mật khẩu mới và nút [Lưu] (`gpm_pre_change`).
  3. Ảnh modal dialog xác nhận `Sign out everywhere` (`gpm_signout_confirm_dialog`).
  4. Ảnh đăng nhập lại thành công (giải 2FA TOTP + màn hình KMSI bấm [Có] hoặc Account Dashboard).
* Không bao giờ gửi kết quả sơ sài thiếu ảnh của bất kỳ chặng nào.

---

## 10. Kỷ Luật Cooldown 24H Khi Gặp Lỗi Dịch Vụ & Thứ Tự Bắt Buộc (2026-10-10)
- **Quy tắc thứ tự bất biến: Add 2FA TRƯỚC, Đổi Pass SAU**:
* Luồng bảo mật Hotmail bắt buộc thực thi theo trình tự:
  1. **BƯỚC 1**: Thêm 2FA Authenticator (TOTP) trước -> Lưu Secret Key Cột 4 Excel -> Bật công tắc tổng Two-step verification (`EnableTfa = ON`).
  2. **BƯỚC 2**: Đổi Mật khẩu mới sau (dùng chính 2FA vừa tạo để giải challenge bảo mật nếu Microsoft yêu cầu).
  3. **BƯỚC 3**: Sign out everywhere -> Xác nhận dialog thu hồi token toàn cầu.
  4. **BƯỚC 4**: Relogin Live trên GPM Profile -> Điền pass mới + TOTP -> Bấm "Có" màn hình KMSI để lưu phiên sống.
* Tuyệt đối không được đảo ngược hoặc bỏ qua bước 2FA.
- **Cơ chế Cooldown 24H Ngay Lập Tức Khi Gặp Lỗi Dịch Vụ Microsoft**:
* Khi bấm Lưu đổi mật khẩu mà Microsoft trả về thông báo lỗi dạng:
  `There's a temporary problem with the service...` / `There was a problem...` / `Tạm thời có lỗi với dịch vụ. Xin vui lòng thử lại...`
* **Hành động bắt buộc ngay lập tức**:
  1. Gọi `set_cooldown(email, hours=24, reason=err_msg)` để ghi nhận thời điểm hết hạn cooldown (`cooldown_until = now + 24h`) vào state file (`hotmail_changed_tracker.json`).
  2. **Dừng luồng ngay lập tức (Fail-Fast)**, ném exception ngắt tiến trình.
  3. **TUYỆT ĐỐI CẤM GHI ĐÈ MẬT KHẨU VÀO EXCEL**: Giữ nguyên mật khẩu gốc trong cả `taikhoan_dat_v2_updated .xlsx` và `gmail_clean_v2.xlsx`.
  4. Báo cáo trung thực, rõ ràng ngay cho User về hiện tượng bị chặn và trạng thái cooldown của nick. Cấm ỉm lỗi hoặc báo hoàn thành ảo.
* **Bỏ qua tự động ở các lượt chạy sau**:
  * Trong hàm `find_target_accounts()`, bắt buộc kiểm tra `is_in_cooldown(email)`. Nếu tài khoản còn trong thời gian 24h cooldown thì tự động bỏ qua (`[COOLDOWN_SKIP]`), không cố chấp retry làm tăng rủi ro spam/flag tài khoản.
- **Kỷ luật Visual Evidence - Đủ 5 Chặng Bằng Chứng**:
* Mọi lượt chạy Canary nghiệm thu BẮT BUỘC phải gửi đủ 5 chặng ảnh hiện trường đã qua WinRT OCR soi chữ:
  1. Ảnh nhập mã OTP liên kết 2FA Authenticator.
  2. Ảnh form điền mật khẩu mới kèm nút Lưu.
  3. Ảnh modal dialog xác nhận Đăng xuất khỏi mọi nơi.
  4. Ảnh nhập mã 2FA TOTP khi đăng nhập lại.
  5. Ảnh màn hình Duy trì đăng nhập (KMSI) bấm nút "Có".


---

## 7. Kỷ Luật Đường Dẫn Media Telegram (Chống Nuốt Ảnh)
- **Pitfall**: Sử dụng dấu gạch ngược Windows trong tag `MEDIA:D:\Taadaa\runtime\artifacts\...` làm xuất hiện escape character `\a` (ASCII Bell), khiến bộ chuyển đổi gateway Telegram (`extract_media`) nuốt chửng thẻ ảnh và không gửi ảnh tới user.
- **Quy tắc bất biến**: Mọi đường dẫn trong thẻ `MEDIA:` **BẮT BUỘC** phải chuẩn hóa dùng dấu gạch chéo `/`:
  ```text
  MEDIA:D:/Taadaa/runtime/artifacts/ten_anh.png
  ```
- **Soi mắt OCR**: Trước khi gửi bất kỳ thẻ `MEDIA:` nào, phải dùng WinRT OCR đọc xác nhận text trên ảnh để đảm bảo không bị đen hình hay mất viền.

---

## 11. Kỷ Luật 1 IP Chỉ Được Chạy Mỗi 24H (IP Rate-Limiting) & Interstitial Handlers (2026-10-10)
- **Yêu Cầu Cốt Lõi**:
  * Khi chạy script hoặc cron batch đổi thông tin bảo mật Hotmail (`change info hotmail`), **MỖI 1 IP / PROXY CHỈ ĐƯỢC PHÉP CHẠY TỐI ĐA 1 LẦN MỖI 24 GIỜ**.
  * Chạy nhiều tài khoản trên cùng 1 IP trong ngày sẽ kích hoạt hệ thống Fraud Detection của Microsoft, dẫn đến lỗi hàng loạt: *"There's a temporary problem with the service"* hoặc khóa tính năng đổi pass.
- **Cơ Chế Kiểm Tra IP 2 Lớp (Dual-Layer IP Gate)**:
  1. *Lớp 1 (Pre-flight by Proxy Endpoint)*: Trước khi khởi động profile, đọc `raw_proxy` từ thông tin GPM profile, tách ra `proxy_endpoint` dạng `host:port` (ví dụ `test.taadaa.click:5112`). Nếu endpoint này đã chạy trong 24h qua -> Bỏ qua ngay (`[COOLDOWN_BLOCKED]`), không tốn tài nguyên start browser.
  2. *Lớp 2 (Post-start by Live Egress IP)*: Ngay khi kết nối CDP, mở tab phụ truy cập `https://api.ipify.org?format=json` để lấy IP công cộng thực tế đang ra ngoài của proxy. Nếu IP thực tế này đã chạy trong 24h qua -> Ngắt profile ngay lập tức (`[IP_COOLDOWN_BLOCKED]`) và bỏ qua để bảo vệ nick.
- **Kích Hoạt Cooldown 24h Cho Cả Nick Lẫn IP Khi Gặp Lỗi**:
  * Khi Microsoft trả về lỗi dịch vụ (*"There's a temporary problem with the service"*, *"There was a problem"*, *"Tạm thời có lỗi với dịch vụ"*):
    - Đặt cooldown 24h cho tài khoản: `set_cooldown(email, hours=24, reason=err_msg)`.
    - Đặt cooldown 24h cho cả IP lẫn Proxy: `set_ip_cooldown(ip, proxy, email, hours=24, reason=err_msg)`.
    - Dừng tiến trình ngay lập tức (Fail-Fast), **TUYỆT ĐỐI CẤM** ghi đè mật khẩu vào Excel.
- **Khắc Phục Interstitial "Ghi chú nhanh về tài khoản Microsoft"**:
  * Microsoft thường chèn màn hình thông báo *"Ghi chú nhanh về tài khoản Microsoft"* (hoặc *"A quick note about your Microsoft account"*) chắn trước trang proofs / change password.
  * Nếu không xử lý, trang sẽ bị kẹt lại, script không tìm thấy `#AddProofLink` và bỏ qua bước Add 2FA.
  * Bắt buộc có selector click `[OK]`: `button:has-text('OK')`, `input[value='OK']`, `#iShowG`, `button[id*='ok']`.
  * Đồng thời click `Bỏ qua / Skip` cho các gợi ý Passkey / FIDO / Windows Hello (`button:has-text('Bỏ qua')`, `button:has-text('Skip')`, `button:has-text('Không, cảm ơn')`).
- **Khóa Logic: BẮT BUỘC 2FA KÍCH HOẠT XONG MỚI ĐƯỢC SANG BƯỚC ĐỔI PASS**:
  * Kiểm tra `has_totp_final = bool(totp_secret_key or get_2fa_secret(email) or page.locator("#TOTPAuthenticator").is_visible())`.
  * Nếu `has_totp_final == False`: Ném `RuntimeError` dừng ngay lập tức, cấm tuyệt đối nhảy sang trang `password/change` khi chưa có 2FA!

---

## 12. Bẫy Xác Minh Kép Khi Reset/Change Password Sau Khi Bật 2FA (Two-Step Verification Proof Picker)
- **Hiện tượng**: Sau khi bật Two-step verification (`EnableTfa = ON`), khi tài khoản yêu cầu đổi mật khẩu hoặc đặt lại mật khẩu (`ResetPassword.aspx`):
  * Microsoft yêu cầu **2 phương thức xác thực liên tiếp** ("Thêm một lần nữa / Two-step verification identity proof").
  * **Proof 1**: Nhập mã từ Authenticator App (TOTP) (`#iVerifyText` -> Điền mã 6 số từ `pyotp.TOTP(secret).now()` -> Bấm `#iVerifyIdentityAction`).
  * **Proof 2**: Chọn gửi mã qua email khôi phục (`Gửi email đến ga*****@fviainboxes.com`):
    - Selector: `label:has-text('fviainboxes.com'), span:has-text('fviainboxes.com'), #textproofOption1`.
    - Xuất hiện ô input xác nhận email: `#proofInput1` (`name="proofPickerEmail"`, `aria-label="Địa chỉ email"`).
    - **CẠM BẪY NGHIÊM TRỌNG**: Microsoft đã in sẵn phần đuôi `@fviainboxes.com` ngay bên cạnh ô input.
      * Nếu script điền **TOÀN BỘ EMAIL** (ví dụ `gabrielesalgero760jod@fviainboxes.com`), Microsoft sẽ báo lỗi đỏ:
        *"Email này không trùng với email thay thế liên kết với tài khoản của bạn. Email chính xác bắt đầu bằng @fviainboxes.com"*.
      * **BẮT BUỘC CHỈ ĐIỀN USERNAME**: Chỉ lấy phần trước `@` (ví dụ `rec_email.split('@')[0]` -> `gabrielesalgero760jod`).
    - Bấm nút **[Nhận mã]** (`#iSelectProofAction`).
    - Lấy mã OTP từ `fetch_recovery_email_otp(rec_email)`.
    - Điền mã OTP vào `#iVerifyText` và bấm `#iVerifyIdentityAction`.
  * Sau khi hoàn tất 2 Proofs: Trang đặt lại mật khẩu hiển thị (`#iPassword`, `#iRetypePassword`).
  * Điền mật khẩu mới 14 ký tự mạnh mẽ và submit `#iResetPasswordAction`.
  * Đăng nhập lại với Mật khẩu mới + TOTP + KMSI [Có] để hoàn tất phiên.
  * **Lợi ích**: Luồng này giải phóng triệt để các tài khoản bị Microsoft chặn form đổi pass trực tiếp, đồng thời cập nhật mật khẩu mới và 2FA chuẩn thương mại 100%.
