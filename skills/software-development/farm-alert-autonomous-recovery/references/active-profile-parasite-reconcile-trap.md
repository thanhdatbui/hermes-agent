# Active Profile Parasite Trap & False "DONE" Reconciliation Protocol

## Bối cảnh & Hiện tượng (Symptom)
Khi vận hành Farm, xuất hiện tình trạng:
1. Telegram báo cảnh báo P0 văng account: `UploadHook: [ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found`.
2. Máy chạm trần 8 tài khoản nhưng tài khoản cần chạy (ví dụ Row 1 `@xuanpham81`) không có trên máy, hoặc bị tài khoản lạ đẩy ra ngoài viewport.
3. Trước đó hệ thống dọn dẹp (`watchdog_idle_parasite_reconcile.py`) đã từng đánh dấu `"DONE"` cho nick kí sinh này trong `parasite_reconcile_state.json`, nhưng thực tế nick kí sinh vẫn nằm lù lù trên máy!

---

## Căn nguyên cốt lõi: Bẫy "Active Profile" trong Switcher (The Active Profile Trap)
* **Cơ chế hiển thị của TikTok Switcher Bottom Sheet**:
  - Khi tap vào header profile hoặc mở Switcher qua Settings, app TikTok **CHỈ hiển thị danh sách các tài khoản phụ (chưa kích hoạt)** để người dùng chuyển sang.
  - Tài khoản **đang active trên Profile chính** HOÀN TOÀN KHÔNG XUẤT HIỆN trong danh sách chuyển đổi này (hoặc chỉ nằm ở header tĩnh riêng biệt).
* **Lỗ hổng logic của script dọn dẹp cũ**:
  - Script mở Switcher sheet rồi duyệt cây UI XML tìm node khớp `username`:
    ```python
    target_node = find_in_switcher(xml, username)
    if not target_node:
        print(f"[{machine_id}] Nick @{username} da khong con trong Switcher!")
        return True  # <-- BẪY TỬ HUYỆT: TƯỞNG ĐÃ OUT SẠCH!
    ```
  - Nếu nick kí sinh tình cờ đang là tài khoản active trên Profile (do lần mở app trước hoặc do vừa đăng ký xong), `target_node` trả về `None`!
  - Script ngộ nhận là nick đã được đăng xuất từ trước, tự động trả về `True` và ghi nhận `"DONE"` vào `parasite_reconcile_state.json`.
  - **Hậu quả**: Nick kí sinh không hề bị đăng xuất, tiếp tục chiếm giữ slot 8, làm máy luôn trong tình trạng full 8 nick và ngăn cản nick chính chủ đăng nhập.

---

## Quy trình Chuẩn đoán & Phục hồi Chuẩn hóa (Triage & Recovery Protocol)

### 1. Dual-Surface Detection Gate (Kiểm tra 2 lớp trước khi hành động)
Trước khi mở Switcher, BẮT BUỘC kiểm tra cả 2 bề mặt giao diện:
1. **Lớp 1 - Active Profile Header**:
   - Trích xuất identity từ Profile screen: `handle, display_name = extract_profile_identity(xml)` hoặc chạy WinRT OCR trên screencap Profile.
   - Nếu `handle == target_parasite_username`: **Khẳng định nick kí sinh đang là active account!** Tuyệt đối không mở Switcher để tìm.
2. **Lớp 2 - Switcher Bottom Sheet**:
   - Chỉ khi active profile KHÔNG PHẢI nick kí sinh, mới mở Switcher sheet để tìm nick mục tiêu trong danh sách chuyển đổi.

---

### 2. Active Profile Direct Logout Flow (Quy trình Đăng xuất Trực tiếp Nick Active)
Khi nick kí sinh đang là active account:
1. Từ màn hình Hồ sơ (Profile), tap nút **Menu hồ sơ (3 gạch)** ở góc trên bên phải: `bounds=[954,96][1056,204]`, tâm `(1005, 150)`.
2. Tap mục **"Cài đặt và quyền riêng tư"** (Settings and privacy): `bounds=[235,1247][860,1305]`, tâm `(548, 1276)`.
3. Cuộn nhanh xuống đáy trang Settings:
   ```bash
   for i in 1 2 3 4; do input swipe 540 1400 540 400 300; sleep 1; done
   ```
4. Tìm và tap nút **"Đăng xuất"** (Log out) ở đáy trang Settings: tâm `(282, 1662)`.
5. Trong modal xác nhận *"Bạn có chắc chắn muốn đăng xuất?"*:
   - Modal hiển thị 2 lựa chọn: `[Chuyển đổi tài khoản]` và `[Đăng xuất]`.
   - BẮT BUỘC tap vào nút **"Đăng xuất"** màu đỏ ở dòng dưới: tâm `(540, 1664)`.
6. Sau khi đăng xuất, TikTok sẽ tự động chuyển active sang 1 tài khoản hợp lệ khác hoặc đẩy về Feed.

---

### 3. Visual Verification Gate (Gate 6 - WinRT OCR Kiểm chứng Hiện trường)
Sau khi đăng xuất, thực hiện kiểm tra nghiệm thu thị giác:
1. Mở lại TikTok $\rightarrow$ vào Profile $\rightarrow$ mở Switcher sheet.
2. Chụp screencap và chạy WinRT OCR (`windows-native-ocr`):
   - **Xác nhận 1**: Nick kí sinh đã biến mất 100% khỏi cả active profile lẫn danh sách switcher.
   - **Xác nhận 2**: Nút **"Thêm tài khoản"** (`+ Thêm tài khoản` / `Add account`) đã xuất hiện trở lại ở đáy switcher sheet.
   - **Xác nhận 3**: Số lượng tài khoản trên máy giảm từ 8 xuống đúng 7 tài khoản chính chủ.
3. Chụp và gửi ảnh nghiệm thu đính kèm `MEDIA:<path>` kèm highlight ô "Thêm tài khoản".

---

### 4. Nạp lại Nick Chính chủ còn thiếu (Account Replenishment)
1. Xác định nick chính chủ còn thiếu của máy qua Master Excel `taikhoan_dat_v2_updated .xlsx` (ví dụ Row 1 Máy 34 là `@xuanpham81`).
2. Chạy login runner:
   ```bash
   export TIKTOK_REG_FEED_AFTER_REG=0
   export TIKTOK_REG_AVATAR_AFTER_REG=0
   python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <target_username> --ss
   ```
3. Runner sẽ tự động điền password và lấy mã 2FA Authenticator TOTP từ cơ sở dữ liệu.
4. **BẪY `TRACKING_WORKBOOK_WRITE_LOCKED` ([Errno 9] Bad file descriptor)**:
   - Khi runner đăng nhập thành công vào app TikTok và đạt màn hình Profile, ở bước cuối cùng nó cố ghi update vào Excel.
   - Nếu file Excel đang bị khóa bởi tiến trình khác hoặc OneDrive sync, runner có thể exit code 1 với thông báo:
     `BLOCK TRACKING_WORKBOOK_WRITE_LOCKED ... [Errno 9] Bad file descriptor`.
   - **Đánh giá**: Đây là lỗi ghi file thứ cấp, **TRÊN THIẾT BỊ APP TIKTOK ĐÃ ĐĂNG NHẬP THÀNH CÔNG 100%**. Dữ liệu tài khoản vốn đã có sẵn trong Master Excel từ trước.
   - *Hành động*: Kiểm tra lại Switcher của máy qua OCR; nếu nick đích đã xuất hiện trong danh sách và tổng số tài khoản đạt 8/8 thì nghiệm thu **HOÀN TẤT THÀNH CÔNG**, tuyệt đối không revert hay coi là thất bại.

---

### 5. Kỷ luật Rà soát Device Lock (Dead-Owner vs Live Running Batch)
Khi kiểm tra kẹt lock thiết bị (`~/.codex/device-locks`):
- **CẤM TUYỆT ĐỐI** xóa mù hoặc dùng `taskkill` bừa bãi khi chưa đối soát PID tiến trình.
- Kiểm tra liveness qua `psutil.pid_exists(pid)`.
- Nếu PID tương ứng với tiến trình batch đang chạy hợp lệ (ví dụ `run_tiktok.py --mode multi-machine-feed-session` với commandline chứa `--artifact-root .../row-X-...`): Đây là **Live Active Lock**, đang bảo vệ máy trong ca nuôi tự nhiên. Tuyệt đối không can thiệp.
- Chỉ khi PID không tồn tại trong hệ điều hành (dead process) hoặc lock file quá hạn TTL (`ttl_seconds`) mà không có heartbeat mới được coi là **Dead-Owner Lock** và kích hoạt `reap-dead-owner-locks.py` để dọn dẹp an toàn.
