# Phân biệt Nick Ký sinh vs Nick Farm Reg dở dang & Quy tắc Đăng xuất An toàn (2026-09-19)

## 1. Bản chất cốt lõi: Mọi tài khoản trên thiết bị đều là tài sản của Farm

> **Nguyên tắc bất biến (User Correction 2026-09-19):**
> *"Đã là nick có trên máy: 1 là ký sinh (đã login ở máy khác), 2 là nick reg chưa kịp ghi info. Tuyệt đối KHÔNG có khái niệm 'nick rác ngoài luồng' để tự ý vứt bỏ! Chỉ được phép đăng xuất nếu chứng minh được nick đó là KÝ SINH (đã có máy chủ quản khác)."*

### A. Nick Ký sinh (Parasite Account)
- **Định nghĩa:** Nick đã được đăng ký và ghi nhận chính thức ở một máy khác (ví dụ: `@verdhsclf6f` thuộc Máy 16, `@yanesbgvmuq` thuộc Máy 26, `@cyennffqko8` thuộc Máy 36, `@thanhlee372` thuộc Máy 37).
- **Nguyên nhân lịch sử:** Do các batch reg cũ chạy đa luồng trước đây cùng bốc chung email từ `gmail_clean_v2.xlsx` khi chưa có khóa tracking thời gian thực, hoặc do reconcile login sai target.
- **Cách xử lý:** Xác minh máy gốc đã sở hữu nick an toàn $\rightarrow$ Đăng xuất nick ký sinh khỏi máy hiện tại để nhả slot.

### B. Nick Reg chưa kịp ghi info (Unrecorded Farm Account)
- **Định nghĩa:** Nick được tạo từ chính email được cấp cho máy đó trong `gmail_clean_v2.xlsx` (ví dụ: `@guadazvvrn5` trên Máy 40 từ mail `guadarramanilges923@hotmail.com`), nhưng runner bị văng/timeout ở bước cuối nên chưa kịp cập nhật vào `taikhoan_dat_v2_updated .xlsx`.
- **Cách xử lý:** **BẢO TOÀN TUYỆT ĐỐI**, backfill ngay thông tin ID, mail, pass mail vào dòng/slot tương ứng trong Master DAT và Run Safe Excel. CẤM ĐĂNG XUẤT NHẦM.

---

## 2. Bẫy tử thần khi đăng xuất trên Samsung Galaxy S7 (Android 7/8)

### Pitfall 1: `uiautomator dump` chết / treo vĩnh viễn (Exit code 137)
- Trên Samsung S7, tiến trình `uiautomator dump` thường xuyên bị wedged hoặc kernel OOM trả về exit code 137.
- **Hậu quả:** Các script dùng `subprocess.run(['adb', 'shell', 'uiautomator', 'dump'])` mà **không có `timeout=15`** sẽ bị deadlock vô hạn đến khi cạn sạch budget 600s của subagent.
- **Giải pháp:** Bắt buộc đặt `timeout=15` cho mọi lệnh ADB subprocess. Ưu tiên dùng Screencap + Windows Native OCR (`do_ocr.ps1`) kết hợp Coordinates chuẩn.

### Pitfall 2: Nghiệm thu giả / Logout ảo (Báo cáo láo)
- Script cuộn trang Cài đặt và tap theo tọa độ cũ `(540, 1750)` hoặc tap dialog popup `(750, 1100)` nhưng bị trượt do giao diện TikTok bản mới dài hơn.
- Script chụp ảnh màn hình nhưng **không OCR đối soát lại Switcher**, vội vã ghi nhận `"DONE"` dẫn tới nick ký sinh vẫn còn nguyên.

### Pitfall 3: Khẳng định "hết ký sinh" khi chỉ nhìn Excel & Bẫy Switcher nông 7 dòng (User Correction 2026-10-02)
- Nhầm lẫn giữa "Excel sạch duplicate" và "thiết bị thật sạch nick": Khi Excel đã dọn sạch, thiết bị vật lý vẫn lưu phiên. Hàng ngày máy chạy feed vẫn bình thường, chỉ khi máy đó bị thiếu slot khác và gọi reg bù thì runner mới phát hiện trần 8 nick (`MACHINE_FULL_8_ACCOUNTS`).
- Trên layout TikTok Samsung S7, Switcher chỉ hiển thị vừa 7 accounts. Nick thứ 8 luôn bị khuất dưới đáy (Y > 1850). Nếu không cuộn `swipe 540 1500 540 1000 300` trước khi dump UI/OCR thì sẽ bị false negative (tưởng nick không có nhưng thực tế đang nằm dưới đáy).
- Danh sách gốc toàn farm gồm 14 tài khoản bị bốc trùng Hotmail đợt 25-26/08 cần rà soát thực tế thiết bị: `miumiu67971` (M3), `verdhsclf6f` (M40 - đã out), `gabruync3o9` (M19), `rillecoq5ml` (M11), `jomegbym8n8` (M24), `yanesbgvmuq` (M42), `phamnhi1770` (M75 - đã out), `lebaothao8787` (M69), `anillpboe98` (M34), `cyennffqko8` (M76 - đã out), `thleyzilkva` (M13), `annapmfdh0a` (M28 - đã out), `chichi13853` (M53), `anggiathinh2905` (M61 - đã out) và `thanhlee372` (M32).

---

## 3. Quy trình Đăng xuất Chuẩn xác & Nghiệm thu 2 lớp

1. **Mở Switcher & Chuyển sang nick ký sinh:**
   - Tap Profile `(972, 1857)` $\rightarrow$ Vuốt nhẹ `(540, 1200 -> 540, 800)` $\rightarrow$ Tap header `(540, 140)`.
   - OCR tìm vị trí nick ký sinh $\rightarrow$ Tap chọn để switch sang nick đó (chờ 6s).
2. **Vào Cài đặt và quyền riêng tư:**
   - Tap Profile `(972, 1857)` $\rightarrow$ Menu 3 gạch `(1005, 150)` $\rightarrow$ Tap Cài đặt `(540, 1250)`.
   - Vuốt 6 lần xuống đáy trang: `input swipe 540 1600 540 300 250`.
3. **Kích hoạt Đăng xuất & Xác nhận Popup:**
   - Tap nút "Đăng xuất" ở đáy trang tại `(300, 1640)`.
   - Khi popup xác nhận hiện ra: Tap nút "Đăng xuất" màu đỏ tại `(540, 1640)`. Chờ 6s.
4. **Nghiệm thu 2 lớp bắt buộc:**
   - Mở lại Profile $\rightarrow$ mở Switcher $\rightarrow$ Chụp screencap `MEDIA:<path>`.
   - Chạy OCR đọc lại danh sách Switcher: BẮT BUỘC xác nhận nick ký sinh **ĐÃ BIẾN MẤT** và nút **"Thêm tài khoản"** (Add account) đã xuất hiện trở lại (hoặc Switcher còn $\le 7$ nick).
   - Nếu nick vẫn còn: Phải coi là THẤT BẠI, không được kết luận xong.
5. **Dọn dẹp:**
   - `am force-stop com.ss.android.ugc.trill` và đưa máy về Home (`keyevent 3`).
