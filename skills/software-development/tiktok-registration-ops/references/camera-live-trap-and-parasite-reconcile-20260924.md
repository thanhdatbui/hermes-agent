# Camera LIVE Trap, ADB Zombie Cleanup & Parasite Account Logout (24/09/2026)

## 1. Cạm Bẫy Text Match "Dong" (Đóng) Dính "Trò Chơi Di Động" Trên Màn Hình Camera/LIVE
- **Hiện tượng (Case Máy 69):**
  - Script cố gắng dismiss màn hình Camera / Tạo video bằng lệnh:
    ```python
    find_text_tap(device_id, "Đóng", "Dong", "Close", wait=D_SHORT)
    ```
  - Thay vì đóng màn hình, script liên tục tap vào nút `(567, 1666)` có nhãn `'Trò chơi di động'`:
    ```text
    ✓ tap (567, 1666) | text='Trò chơi di động' desc='' rid='com.ss.android.ugc.trill:id/z2q'
    ```
  - Quá trình này lặp lại 15+ lần cho đến khi timeout mở account dropdown (`[03_dropdown] Khong mo duoc account dropdown`).
- **Nguyên nhân cốt lõi (Root Cause):**
  - Trong hàm `node_has_target(attrs, targets)`:
    ```python
    for v in values_flat:
        if t_flat and (t_flat == v or t_flat in v):
            return True
    ```
  - Chuỗi target `"Dong"` sau khi normalize bỏ dấu là `"dong"`.
  - Giá trị node `'Trò chơi di động'` sau khi bỏ dấu là `"tro choi di dong"`.
  - Điều kiện substring `t_flat in v` (`"dong" in "tro choi di dong"`) trả về `True`!
  - Script coi tab trò chơi là nút "Đóng" và liên tục bấm vào giữa tab, kích hoạt vòng lặp vô tận.
- **Giải pháp chuẩn:**
  1. Nhận diện màn hình Camera/LIVE qua layout ID: `ttlive_preview_surfaceview` hoặc nút quay lại `com.ss.android.ugc.trill:id/eaw` (`bounds="[18,72][150,204]"`).
  2. Dùng exact match hoặc regex word boundary `r"\bdong\b"` khi match target ngắn như "Dong" / "Đóng", cấm kiểm tra substring trần (`t_flat in v`) với các từ 1 âm tiết phổ biến.
  3. Fallback bấm trực tiếp tọa độ góc trái trên `(84, 150)` hoặc `keyevent 4` (Back).

---

## 2. Kỷ Luật Xử Lý Nick Ký Sinh & Đăng Xuất An Toàn Từ Cài Đặt (User Correction)
- **Bối cảnh:** Máy 61 bị đăng nhập nhầm nick `@anggiathinh2905` (nick thuộc Máy 28 STT 221), khiến app TikTok đạt trần 8 nick (`MACHINE_FULL_8_ACCOUNTS`) và từ chối reg bù tài khoản mới.
- **Quy tắc an toàn (User xác nhận: "Log out kí sinh đc mà k lỗi đâu"):**
  - Việc đăng xuất nick ký sinh **HOÀN TOÀN AN TOÀN KHI THỰC HIỆN QUA MENU CÀI ĐẶT CỦA TIKTOK**.
  - Khác với lo ngại trước đây, TikTok Android chỉ hủy session của nick đang active được chọn, các tài khoản còn lại trong switcher vẫn được bảo toàn nguyên vẹn.
- **Quy trình chuẩn hóa 4 bước:**
  1. Mở switcher (`open_account_dropdown`), tap chuyển sang nick ký sinh mục tiêu.
  2. Vào Profile -> Menu 3 gạch (`(1005, 150)`) -> Chọn *Cài đặt và quyền riêng tư* (`(540, 1248)`).
  3. Cuộn xuống đáy trang (swipe 5-6 lần), tap *Đăng xuất* (`(540, 1750)`).
  4. Xác nhận popup Đăng xuất (`(750, 1100)`).
  5. Mở lại Account Switcher để chụp ảnh nghiệm thu xác nhận danh sách nick active (`MEDIA:...`).

---

## 3. Cứu Hộ ADB Socket :5037 Bị Kẹt Zombie Process
- **Hiện tượng:**
  - Hàng loạt thiết bị chuyển sang trạng thái `offline` bất thường.
  - Lệnh ADB báo lỗi: `could not read ok from ADB Server` hoặc `cannot connect to daemon`.
- **Nguyên nhân:** Các process con `adb.exe` bị kẹt sau timeout giữ exclusive connection tới cổng `5037`, khiến ADB server không thể cấp socket mới.
- **Xử lý dứt điểm O(1):**
  ```bash
  cmd.exe /c "taskkill /f /im adb.exe"
  ```
  Quét sạch toàn bộ các process zombie. Lệnh ADB tiếp theo sẽ tự động khởi động daemon ADB sạch và nhận diện đầy đủ thiết bị online trở lại.
