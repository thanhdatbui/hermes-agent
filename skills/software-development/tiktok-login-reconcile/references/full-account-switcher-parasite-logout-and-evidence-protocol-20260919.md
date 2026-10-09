# Full Account Switcher Reconcile & Coordinate-OCR Logout Architecture (2026-09-19)

## 1. Bản Chất Sự Cố: Nguồn Gốc Nick Ký Sinh Khi Chạm Trần 8 Nick
- **Nguyên nhân gốc lịch sử (Đợt reg cũ 2026-08-26)**:
  - Code reg cũ chạy song song (batch multithread) nhưng file Excel nguồn (`gmail_clean_v2.xlsx`) và tracking workbook (`taikhoan_dat_v2_updated .xlsx`) chưa có cơ chế Deferred Tracking Writer khóa tức thì.
  - Cùng 1 email bị nhiều máy bốc cùng lúc (ví dụ: `cyenniferos@hotmail.com` bị cả M36 và M76 bốc; `yanesintzelar@hotmail.com` bị cả M26 và M42 bốc; `verdherichir74@hotmail.com` bị cả M16 và M40 bốc).
  - Máy thứ hai nhập email -> TikTok nhận diện đã có tài khoản -> OTP gửi về inbox -> đọc OTP đăng nhập thẳng vào app -> nick chính chủ của máy gốc trở thành nick ký sinh âm thầm nằm trên máy thứ hai từ ngày 26/08.
  - Khi hệ thống chạy reg bù Row 7 & Row 8 chạm trần 8 nick (`MACHINE_FULL_8_ACCOUNTS`), các tàn dư này mới phát lộ.
  - **Khẳng định**: Từ sau khi cập nhật bộ đếm `MAX_ACCOUNTS_PER_MACHINE = 8` và cơ chế Deferred Tracking Writer khóa tuần tự, **hoàn toàn không phát sinh thêm nick ký sinh mới**.

## 2. Invariant Tài Sản Farm: Phân Biệt Nick Ký Sinh vs Nick Reg Chưa Ghi Info
- **Tất cả nick trên máy đều là tài sản của User**:
  1. **Nick ký sinh**: Đã được đăng ký và thuộc quyền sở hữu chính thức của một máy khác trong hệ thống (đã có dòng ghi nhận đầy đủ trên file Excel master).
     👉 **Xử lý**: Xác minh đúng máy gốc đang giữ -> Đăng xuất khỏi máy hiện tại để nhả slot.
  2. **Nick reg chưa kịp ghi info**: Được reg thành công từ email cấp cho chính máy đó nhưng do runner crash/văng ở bước cuối nên chưa kịp cập nhật Excel.
     👉 **Xử lý**: **BẢO TOÀN TUYỆT ĐỐI**, CẤM ĐĂNG XUẤT VỨT BỎ. Bắt buộc trích xuất ID + mail để backfill vào slot còn thiếu của máy trong file master và runtime.

## 3. Pitfalls Kỹ Thuật Khi Logout Trên Samsung S7 / Android 7

### Pitfall 1: Bẫy `uiautomator dump` Exit Code 137 (SIGKILL) & Subprocess Treo Vô Hạn
- Tiến trình `uiautomator` trên Samsung S7 rất dễ bị kernel futex deadlock (`futex_wait_queue_me`) hoặc văng SIGKILL 137 do OOM khi app TikTok 46.x ngốn RAM.
- **Hậu quả**: Các script gọi `subprocess.run(["adb", ...])` không có `timeout` sẽ bị block vĩnh viễn $\infty$ đến khi chạm trần 600s của agent runner.
- **Giải pháp**:
  - Mọi lệnh ADB subprocess trong Python **BẮT BUỘC có `timeout=15`**.
  - Không dựa dẫm vào `uiautomator dump` cho các bước thao tác Logout. Chuyển sang dùng **Screencap + Windows Native WinRT OCR + Bounding Box Coordinates**.

### Pitfall 2: Layout Profile Mới Mất Dropdown Chevron `▼`
- Trên TikTok bản mới, nút dropdown chevron `rv5` cạnh tên user ở đầu Profile có thể bị ẩn hoặc không click được.
- **Giải pháp bung Switcher chuẩn xác 100%**:
  1. Vào tab Hồ sơ: `adb shell input tap 972 1857`.
  2. Vuốt nhẹ Profile lên: `adb shell input swipe 540 1000 540 500 250` để bung thanh Sticky Header dính ở mép trên cùng.
  3. Tap vào thanh Sticky Header tại `(500, 140)` -> Dropdown Switcher bung ra 100%.

### Pitfall 3: Popup Story / Bàn Phím Đè Màn Hình
- Sau khi switch nick hoặc mở profile, TikTok có thể bật popup "Tám chuyện nào / Bạn đang nghĩ gì" kèm bàn phím Samsung (`com.sec.android.inputmethod`).
- **Giải pháp**: Gửi `adb shell input keyevent 4` (BACK) 1-2 lần để hạ bàn phím và đóng dialog trước khi mở Menu 3 gạch.

### Pitfall 4: Báo Cáo Ảo / Nghiệm Thu Dối Khi Popup Đăng Xuất Chưa Ăn
- Script cũ bấm nút "Đăng xuất" ở đáy Settings nhưng không kiểm tra popup xác nhận màu đỏ -> nick chưa bị out nhưng script đã vội vàng kết luận xong.
- **Tọa độ thực tế đã kiểm chứng**:
  - Mở Menu 3 gạch: `input tap 1005 150`.
  - Cài đặt và quyền riêng tư: nằm ở dòng cuối menu, tọa độ `(540, 1102)` hoặc `(540, 1227)` hoặc `(540, 1250)`.
  - Cuộn xuống đáy Settings: lặp 6 lần `input swipe 540 1600 540 300 250`.
  - Nút "Đăng xuất" ở đáy trang: `input tap 240 1640` (hoặc `300 1640`).
  - Popup xác nhận "Bạn có chắc chắn muốn đăng xuất không?": Nút xác nhận màu đỏ nằm tại **`input tap 540 1640`** (hoặc `500 1640`).

## 4. Quy Chuẩn Nghiệm Thu 2 Lớp (Gate 6 Media Evidence)
Chỉ được phép kết luận hoàn thành khi:
1. Mở lại Switcher sau khi logout.
2. Dùng Windows Native OCR quét toàn bộ Switcher: **Nick ký sinh BẮT BUỘC biến mất hoàn toàn**.
3. Vuốt Switcher lên và xác nhận dòng **"Thêm tài khoản"** (Add account) đã xuất hiện trở lại ở đáy Switcher (tọa độ khoảng X=253, Y=1769).
4. Lưu screencap vào `D:/Taadaa/reports/m{m}_verified_logout.png` và đính kèm `MEDIA:` vào báo cáo nghiệm thu.
