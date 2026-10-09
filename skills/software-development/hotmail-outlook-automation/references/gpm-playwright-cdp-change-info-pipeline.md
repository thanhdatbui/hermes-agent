# GPM Hotmail Security Change-Info Pipeline (Playwright CDP)

## 1. Tại sao chuyển đổi info Hotmail từ S7 sang GPMLogin (PC)
- **Hạn chế của máy S7 (Android Chrome)**:
  - Tranh chấp DeviceLock: Máy S7 bận nuôi feed TikTok (00:00 - 05:00 sáng và các ca ngày), watchdog vào chạy sẽ bị `DeviceLockUnavailable`.
  - Giới hạn phần cứng: Samsung S7 (4GB RAM) mở web Microsoft Security (`account.live.com/proofs`) rất nặng, dễ OOM, crash app hoặc đơ ADB.
  - UI Mobile biến động: Giao diện web mobile của Microsoft liên tục đổi responsive khiến ADB tap trượt toạ độ.
- **Ưu thế của GPMLogin trên PC**:
  - Chạy độc lập 100% trên PC bằng Playwright CDP (`connect_over_cdp`) trong 0.2s - 1s, giải phóng toàn bộ dàn S7 để nuôi nick.
  - Tận dụng Profile GPM Gmail sẵn có của từng máy (map `f"{machine:02d} - "`): dùng đúng proxy 4G tương ứng (Mobi/Singbox port `20000+N` hoặc `5100+N`) ➔ **Đồng nhất IP 100%**.
  - Tự do lên lịch cron cuốn chiếu 24/7 (VD: `0 10,14,18,22 * * *`).

---

## 2. Quy trình Tự động hóa Playwright CDP trên Microsoft Account

### A. Điều hướng & Xác thực
1. **Entry Point tối ưu**: Điều hướng thẳng vào `https://account.live.com/password/change`.
2. **Switch to Password Link**:
   - Khi nhập email xong, Microsoft có thể hiển thị màn hình gợi ý gửi mã xác minh thay vì ô password.
   - Bắt buộc xử lý selector chuyển sang mật khẩu:
     ```python
     for sel in ["#idA_PWD_SwitchToPassword", "a:has-text('Sử dụng mật khẩu của bạn')", "text='Sử dụng mật khẩu của bạn'"]:
         loc = page.locator(sel)
         if loc.is_visible(timeout=2000):
             loc.click()
             break
     ```
3. **Vượt Terms Update & KMSI**:
   - Màn hình *"Chúng tôi đang cập nhật các điều khoản"*: Click `#iNext` hoặc `button:has-text('Tiếp theo')`.
   - Màn hình *"Duy trì đăng nhập?" (KMSI)*: Bắt buộc click `#idBtn_Back` ("Không") để tránh lưu session rác trên browser.

### B. Form Đổi Mật Khẩu (Locators chuẩn)
- Ô mật khẩu hiện tại (nếu yêu cầu): `#currentPassword`.
- Ô mật khẩu mới và nhập lại:
  ```python
  new_pwd = page.locator('#iPassword, #newPassword, input[name="Password"]').first
  confirm_pwd = page.locator('#iRetypePassword, #confirmPassword, input[name="RetypePassword"]').first
  ```
  *(Lưu ý: Dùng `.first` hoặc id cụ thể `#iPassword`/`#iRetypePassword` để tránh lỗi Playwright strict mode violation khi form có 2 ô password).*

### C. Ironclad Guard: Readback sau Submit (Chống Ghi Đè Pass Ảo)
- **Hiện tượng Rate-limit của Microsoft**:
  Khi submit đổi mật khẩu, Microsoft có thể trả về thông báo lỗi:
  > *"Tạm thời có lỗi với dịch vụ. Xin vui lòng thử lại. Nếu bạn tiếp tục thấy thông báo này, xin vui lòng thử lại vào lúc khác."*
- **Quy tắc bảo vệ dữ liệu Excel**:
  - Bắt buộc chụp ảnh Checkpoint sau submit (`page.screenshot`).
  - Kiểm tra nội dung trang (`page.content()`): Nếu xuất hiện chuỗi `"Tạm thời có lỗi với dịch vụ"` hoặc `"temporary problem with the service"`:
    ➔ **BẮT BUỘC DỪNG VÀ GIỮ NGUYÊN MẬT KHẨU CŨ TRONG EXCEL (CỘT G)**.
    ➔ Tuyệt đối không ghi đè mật khẩu mới vào workbook khi Microsoft chưa chấp nhận lưu thật.

### D. Sign Out Everywhere
- Điều hướng tới `https://account.live.com/proofs/manage/additional`.
- Click selector `text='Đăng xuất khỏi mọi nơi'` / `text='Sign out everywhere'` / `#sign-out-everywhere-button`.
- Bấm xác nhận trên dialog confirm để hủy toàn bộ session và token cũ của bên bán mail.
