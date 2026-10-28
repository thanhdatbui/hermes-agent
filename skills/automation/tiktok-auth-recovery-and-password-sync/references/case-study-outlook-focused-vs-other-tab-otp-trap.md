# Case Study: Bẫy Phân Loại Outlook Web Chia 2 Tab "Ưu Tiên" vs "Khác" (Focused vs Other Tab Trap)

## Bối cảnh hiện trường (Máy 261 - Tài khoản `thuthanh2911`)
- **Tài khoản**: `thuthanh2911` | Email Hotmail: `e6ahwg7.2911.tooct@hotmail.com` | GPM Profile: `a95dedbf-4170-495c-9249-4539c419a112`.
- **Triệu chứng ban đầu**:
  - TikTok trên điện thoại M261 yêu cầu nhập mã OTP gửi về email `e6ahwg7.2911.tooct@hotmail.com`.
  - Runner tự động bấm "Gửi lại mã" trên điện thoại.
  - Script Playwright kết nối CDP vào GPM Profile mở `https://outlook.live.com/mail/0/`, kiểm tra Inbox và báo: chỉ thấy 3 email cũ từ tháng 09/2026 (`369520`, `270527`, `422819`), hoàn toàn không thấy email nào mới của ngày hôm nay.
  - Agent vội vã kết luận: "TikTok bị throttling / blacklist OTP, không gửi thư về hộp thư".

## Phát hiện nút thắt kỹ thuật từ Operator
- Operator nhìn vào ảnh chụp màn hình Outlook Web và chỉ ra: **"Dòng email khác (12) kìa? Bấm vào chưa"**.
- Kiểm tra lại cấu trúc giao diện Microsoft Outlook Web:
  - Outlook mặc định bật tính năng **Focused Inbox** (Hộp thư Ưu tiên).
  - Giao diện danh sách thư được chia làm 2 tab tách biệt:
    1. Tab **"Ưu tiên"** (Focused): Chứa các email quan trọng từ người dùng thực tế.
    2. Tab **"Khác"** (Other): Chứa các email thông báo tự động, bản tin, quảng cáo và **MÃ XÁC THỰC OTP TỪ CÁC NỀN TẢNG MẠNG XÃ HỘI (TikTok, Facebook, Instagram...)**.
  - Phía trên danh sách thư xuất hiện dòng nhóm thư: **`Email khác (12)`** và tab **`Khác`**.
  - Các email OTP gửi lúc 4:46 PM (`171132`), 4:48 PM (`171132`), và 11:18 PM (`998702`) đều nằm trọn vẹn trong tab **"Khác"**!

## Giải pháp cơ giới hóa tự động (Automated Fix)
Trong `D:/Taadaa/Hotmail/scripts/read_otp_gpm.py`:
1. Sau khi mở Outlook Web, script kiểm tra danh sách thư ở tab mặc định.
2. Nếu chưa thấy mã OTP mới hợp lệ, script tự động tìm nút tab có chữ `"khác"` hoặc `"other"`:
   ```python
   for tab_btn in page.locator("[role=tab], button").all():
       t_name = tab_btn.inner_text().strip().lower()
       if "khác" in t_name or "other" in t_name:
           tab_btn.click()
           time.sleep(1.5)
           break
   code = _extract_tiktok_otp(page, exclude_codes=excluded_set)
   ```
3. Sau khi switch sang tab "Khác", mã OTP `998702` được bóc tách ngay lập tức (<1 giây), điền thẳng vào app TikTok trên điện thoại M261.
4. Tài khoản `@thuthanh2911` đăng nhập thành công 100%, lướt 8 video feed và hoàn tất lưu tracking.

## Bài học vận hành
- Tuyệt đối không kết luận "TikTok không gửi OTP" khi chỉ mới kiểm tra tab mặc định của Outlook Web.
- Luôn kiểm tra cả 2 tab `Ưu tiên` và `Khác` trước khi đánh giá tình trạng nhận thư của hộp thư Microsoft.
