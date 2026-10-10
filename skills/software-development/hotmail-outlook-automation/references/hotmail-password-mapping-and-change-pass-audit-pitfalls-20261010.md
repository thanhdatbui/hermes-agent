# Hotmail Password Mapping, TikTok Fallback Bug & Change-Pass Audit Pitfalls (2026-10-10)

## 1. Sự cố Mapping Mật khẩu & Bug Fallback sang Pass TikTok

### Hiện tượng & Bẫy chẩn đoán sai:
- Khi đăng nhập Hotmail trên Web / GPM Playwright (`login.live.com`), Microsoft hiển thị thông báo đỏ: *"Mật khẩu đó không đúng với tài khoản Microsoft của bạn"*.
- Tuy nhiên, tài khoản TikTok gắn với Hotmail đó vẫn đăng ký thành công và hoạt động bình thường trên dàn Farm.
- **Bẫy chẩn đoán sai:** Vội vàng kết luận là tài khoản mua từ shop (`boxtaikhoan.com`) bị sai pass từ đầu và đổ lỗi cho shop.

### Nguyên nhân kỹ thuật cốt lõi:
1. **Lệch cột & State không refresh:**
   - Trong Master Excel `taikhoan_dat_v2_updated .xlsx`, Cột 4 (`PASS`) là **Mật khẩu TikTok**, Cột 7 (`PASS MAIL`) mới là **Mật khẩu Hotmail**.
   - Khi supervisor nạp state (`load_state`), code chỉ khởi tạo `mail_password` cho profile mới. Khi profile đã tồn tại trong state nhưng `mail_password` bị rỗng/thiếu, lệnh update lại cố tình bỏ qua `mail_password`:
     ```python
     # BUG CŨ:
     profiles[key].update({k: v for k, v in account.items() if k not in {"password", "mail_password", "chatgpt_password"}})
     ```
2. **Fallback tai hại sang Pass TikTok:**
   - Lúc gọi lệnh đăng nhập Hotmail (`batch_gpm_hotmail_password_login.py`), script có dòng fallback:
     ```python
     # BUG CŨ:
     "--password", info.get("mail_password") or info.get("password") or ""
     ```
   - Khi `mail_password` rỗng, script tự động lấy trường `password` (mật khẩu TikTok) điền vào ô đăng nhập Hotmail!
3. **Tại sao TikTok vẫn reg được?**
   - Flow đăng ký TikTok đọc mã xác minh qua Microsoft Graph API Token (`Mail.Read`) hoặc Outlook app. TikTok chỉ cần OTP để tạo nick chứ không bao giờ kiểm tra hay xác thực mật khẩu web của Hotmail.

### Quy tắc bất biến (Fix chuẩn):
- Bắt buộc đồng bộ lại `mail_password` từ Excel vào state nếu Excel có dữ liệu.
- **CẤM TUYỆT ĐỐI** fallback sang `password` TikTok khi login Hotmail. Nếu `mail_password` trống, lập tức fail-closed báo lỗi thiếu mật khẩu mail, tuyệt đối không lấy mật khẩu dịch vụ khác điền bừa.

---

## 2. Bằng chứng nhận biết Tài khoản ĐÃ TỪNG ĐỔI PASS (Change Info)

### Dấu hiệu nhận biết 100%:
- Mail mua từ các web shop (`boxtaikhoan.com`, `clonefbig.com`...) ban đầu chỉ có mail khôi phục mặc định dạng `...fviainboxes.com` hoặc không có mail khôi phục.
- Khi truy cập màn hình đăng nhập hoặc quên mật khẩu, nếu Microsoft hiển thị gợi ý:
  `"Gửi mã đến th*****@gmail.com"` (hoặc email khôi phục cá nhân của Operator)
  -> **Điều này chứng minh 100% tài khoản này đã từng được User/hệ thống thực hiện quy trình ĐỔI MẬT KHẨU / THÊM MAIL KHÔI PHỤC trước đây!**

### Nguyên nhân mất mật khẩu mới (Lưu ẩu):
1. **Bỏ quên Master Excel:** Script đổi mật khẩu (`gpm_change_hotmail_security.py`) chỉ cập nhật vào `gmail_clean_v2.xlsx` mà bỏ quên cập nhật Master Tracking `taikhoan_dat_v2_updated .xlsx`.
2. **Lock file âm thầm:** Do OneDrive/Excel lock tiến trình ghi file, lệnh `wb.save()` bị fail hoặc ghi đè không hoàn tất, làm mất chuỗi mật khẩu mới.
3. **Khắc phục:** Khi tài khoản đã có mail khôi phục cá nhân mà mất pass, bắt buộc dùng quy trình khôi phục: gửi OTP về Gmail cá nhân -> reset mật khẩu mới -> đồng bộ ngay lập tức vào CẢ HAI file Excel (`gmail_clean_v2.xlsx` Cột 3 và `taikhoan_dat_v2_updated .xlsx` Cột 7).

---

## 3. Xử lý Cookie Consent Banner trên Microsoft Account

- Sau khi đăng nhập thành công vào Microsoft Live, trang web thường redirect qua `account.microsoft.com` kèm popup/banner Cookie Consent:
  `"Chúng tôi dùng cookie tùy chọn... Chấp nhận / Từ chối / Quản lý cookie"`.
- Nếu không click qua banner này, trang web bị chặn tương tác hoặc giữ nguyên trên màn hình điều khoản khiến script tưởng lầm là chưa login.
- **Selector chuẩn:**
  ```python
  cookie_selectors = [
      "button:has-text('Chấp nhận')", "button:has-text('Accept')",
      "input[value='Chấp nhận']", "input[value='Accept']",
      "button:has-text('Từ chối')", "button:has-text('Decline')",
      "#acceptButton", "#onetrust-accept-btn-handler",
      "button[id*='accept']", "button[id*='Accept']"
  ]
  ```

---

## 4. Kỷ luật giao tiếp & Thuật ngữ

- **CẤM DÙNG THUẬT NGỮ JARGON GÂY KHÓ CHỊU:** Tuyệt đối không gọi tài khoản TikTok là `@handle` hay `TikTok ID handle`. Trong hệ thống và giao tiếp với User, chỉ gọi đơn giản là **ID** hoặc **tên nick TikTok** (ví dụ: `@thanhlee327`, nick `thanhlee327`).
