# Cat Niche Realignment, Version Contract & Feed Session Lock Waiter (2026-10-10)

## 1. Bối cảnh & Hiện trường (@annapmfdh0a — Máy 44 Tik 6)
- **Tài khoản:** `@annapmfdh0a` (Tên hiển thị: **Ngô Bảo Long**).
- **Vị trí thiết bị:** **Máy 44** (Serial: `ce041604e3517c0a05`, cụm Kibe) · **Tik 6**.
- **Lệch hệ thống 3 tầng:**
  1. **Lệch Avatar trên App:** Avatar là hình một cô gái trẻ buộc tóc mặc áo trắng (ảnh đại diện mặc định/reg từ trước), trong khi 100% video thực tế của kênh (7 video đã đăng, 54 video trong folder 350) là nội dung hài hước về thú cưng / mèo (Mèo Dứa, Mèo Mi Mi, Mèo Mun).
  2. **Lệch Niche & Hashtag trong Workbook (`Tik6.xlsx`):** Cột `Keyword Video` ghi nhãn `Hài hước` chung chung, hashtag pool `#haihuoc #haihuocvietnam...` không đánh trúng tệp khán giả yêu mèo / thú cưng cute.
  3. **Lệch Niche Database (`state.db`):** Thư mục 350 đang gán nhãn `haihuoc` thay vì `thucung`.

---

## 2. Quy trình 4 Tầng Đồng bộ Dữ liệu
1. **Trích xuất Avatar Độc bản Chuẩn Niche:**
   - Trích xuất frame từ video `1.mp4` ("Tôi không ngờ Dứa bị quỷ xui xẻo ám!"): chú mèo trắng Dứa nhìn trực diện camera, mắt to tròn, đeo vòng cổ len quả cherry đỏ.
   - Crop vuông 512×512, tỷ lệ khuôn mặt chiếm 82.8% diện tích, khoảng thở đỉnh đầu (headroom) 10.3%, tâm mặt cân xứng (lệch trục ngang < 1px), 100% sạch phụ đề vietsub/text banner.
   - Đồng bộ nguyên tử (`.tmp.jpg` $\to$ `os.replace`) vào cả 2 đầu kho:
     * `D:\TIKTOK-videonuoinick\350\avatar.jpg`
     * `D:\video goc\350\avatar.jpg`
     *(MD5 khớp tuyệt đối: `22409bb23bf40db6f95aab784aef8dd5`)*
2. **Workbook `Tik6.xlsx` (Hàng 45 · Máy 44):**
   - Khóa cứng `video gốc = 350` (bằng `Folder Video = 350`).
   - Cập nhật `Keyword Video = 'Thú cưng cute'`.
   - Cập nhật `Hashtag Pool = '#thucung #thucungcute #meocung #meohaihuoc #boss #sen #thucungdangyeu #petvietnam #tiktokvietnam #xuhuong #fyp #videohay'`.
   - Đặt cờ `Avatar = 'PENDING'`.
3. **Cơ sở dữ liệu Niche (`state.db`):**
   - Cập nhật cả 2 bản C: (`C:\CodexRuntime\tiktok-video\state.db`) và D: (`D:\CodexRuntime\tiktok-video\state.db`): `UPDATE folders SET niche = 'thucung' WHERE folder_num = 350`.
4. **Hàng đợi SQLite (`tiktok_tracker.db`):**
   - Cập nhật `avatar_replace_queue`: `UPDATE avatar_replace_queue SET video_goc = '350', status = 'PENDING', last_error = NULL, updated_at = ... WHERE username = 'annapmfdh0a'`.

---

## 3. Pitfall Mismatch Version Contract `automation-core` trên Kibe Local
- **Triệu chứng:** Khi khởi chạy PowerShell batch upload avatar, nếu thiết lập `os.environ["TIKTOK_VIDEO_AUTOMATION_CORE_VERSION"] = "0.4.45"`, script crash ngay tại preflight:
  `automation-core version mismatch: expected=0.4.45; actual=0.4.44; runtime=D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe`
- **Nguyên nhân:** Trên Kibe local, runtime `venv-core024` mặc định báo `0.4.44`.
- **Quy tắc:** Trên Kibe farm, BẮT BUỘC đặt `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION = "0.4.44"` hoặc để mặc định, TUYỆT ĐỐI KHÔNG ép `0.4.45`.

---

## 4. Kỹ thuật Chờ Nhả Lock Tự nhiên & Khởi chạy Event-Driven Nền
- **Xung đột Lock:** Máy 44 đang chạy dở ca nuôi nick `multi-machine-feed-session` (PID 40332, `machine_44.lock.json`).
- **Kỷ luật:** CẤM kill tiến trình nuôi nick hay xóa ép file lock.
- **Giải pháp Event-Driven Waiter:** Viết script wrapper (`wait_and_run_avatar_m44.py`) chạy nền:
  ```python
  lock_file = os.path.expanduser("~/.codex/device-locks/machine_44.lock.json")
  while os.path.exists(lock_file):
      time.sleep(3)
  time.sleep(2)  # Settle time
  # Launch canonical runner:
  subprocess.Popen(["powershell.exe", "-File", "D:\\Taadaa\\Tiktok-video\\run_tiktok_upload_avatar.ps1", ...])
  ```
  Khởi chạy qua `terminal(command="python ...", background=True, notify_on_complete=True)` để Coordinator nhả context ngay lập tức và harness tự đánh thức khi runner hoàn tất.

---

## 5. Chuỗi Triage Khi Gặp `ACCOUNT_VERIFY_MISMATCH` & Khôi phục Đăng nhập OTP
1. **Phát hiện Missing Account:**
   - Khi runner chạy xong báo: `Máy 44: LỖI (reason=[ACCOUNT_SWITCHER_FAILED] ACCOUNT_READY verify failed: ACCOUNT_VERIFY_MISMATCH)`.
   - Kiểm tra Switcher UI trên thiết bị: máy có 7 nick nhưng thiếu nick `@annapmfdh0a`.
   - **Chỉ đạo Operator:** *"Thì chạy tiktok login acc đó vào"*.
2. **Bẫy Fake Password trong Sổ cái:**
   - Chạy login thông thường bằng pass trong Excel báo `Mật khẩu sai` / `AUTH_BLOCKED`.
   - **Tra cứu lịch sử log:** Nick đăng ký ngày 26/08/2026 bằng Email OTP, không có bước đặt pass (`[pw] Không có màn nhập password → KHÔNG lưu pass (để trống)`). Bug code cũ tự sinh pass ngẫu nhiên lưu vào file.
   - **Quy tắc:** CẤM thử lại pass vô vọng. BẮT BUỘC dùng `--otp-only`.
3. **Thứ tự ưu tiên đọc OTP theo chỉ đạo Operator:**
   - *"Kiểm tra mail đó có token thì dùng k thì đọc từ hotmail"*.
   - Tìm thấy token trong `D:/Taadaa/Hotmail/hotmail_all_60_bought.txt`, lưu vào `~/.hermes/hotmail_tokens/annapaigs47.token`.
   - Graph API lấy OTP 6 số thành công trực tiếp qua PC. CẤM mở app Outlook trên điện thoại gây xung đột foreground.
4. **Vá lỗi Samsung Keyboard Tutorial gửi BACK:**
   - Trong `social_reg_v1.py`, hàm `dismiss_samsung_keyboard_tutorial` thấy `com.sec.android.inputmethod` gửi `keyevent 4` làm văng TikTok về Launcher. Đã vá chỉ gửi BACK khi có `skipButton`.
5. **Thoát `LivePlayActivity` & Nghiệm thu Profile:**
   - Sau khi nhập OTP, TikTok nhảy vào phòng Live Stream (`com.ss.android.ugc.aweme.live.LivePlayActivity`). Gửi `keyevent 4` thoát Live, mở Profile và xác nhận nick `@annapmfdh0a` đã active.

---

## 6. Nghiệm thu Nạp Avatar Hoàn tất 100%
- Kích hoạt lại: `run_tiktok_upload_avatar.ps1 -Tik 6 -ForceAvatarMachineList "44"`.
- Báo cáo batch: `Máy 44: THÀNH CÔNG (exit=0, verified=True, avatar_status: FORCED_REPLACED_VERIFIED)`.
- Cập nhật dữ liệu: `Tik6.xlsx` row 45 cột Avatar chuyển sang `OK`, `avatar_replace_queue` trong `tiktok_tracker.db` chuyển sang `DONE`.
- Nghiệm thu trực quan: WinRT OCR xác nhận ảnh Mèo Dứa hiển thị chuẩn trên màn hình Sửa hồ sơ Máy 44.

