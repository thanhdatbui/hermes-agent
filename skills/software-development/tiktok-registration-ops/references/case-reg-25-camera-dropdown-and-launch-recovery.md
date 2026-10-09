# Case REG-25: Account Dropdown Trapped by Story/Camera Widget & Clean Launch Recovery

## 1. Bẫy Widget "Bạn đang nghĩ gì..." (rid `q3t`) trên Profile
- **Hiện tượng:** Trong `_try_open_account_dropdown_once` (Pass 4 tìm header text để mở switcher), node placeholder "Bạn đang nghĩ gì..." (resource-id `com.ss.android.ugc.trill:id/q3t`, cy~206) không có tiền tố `@` nên dễ bị nhận diện nhầm là tên hiển thị (display-name).
- **Hậu quả:** Bot tap vào `(540, 206)`, làm bung ra màn hình Camera / Tạo video / Đăng Story (`TẠO`, `ĐĂNG`, `LIVE`, `Video mới`).
- **Kẹt liên hoàn:** Hàm `dismiss_profile_overlays` nếu thiếu bộ lọc đóng Camera screen thì bot sẽ kẹt vĩnh viễn ở đây. Luồng fallback qua Settings `_open_account_dropdown_via_settings` tap mù vào `(1005, 150)` trúng ngay nút "Video mới" ở góc trên thay vì Menu 3 gạch của Profile, dẫn đến fail toàn tập `[03_dropdown] Khong mo duoc account dropdown`.
- **Khắc phục:**
  1. Thêm `q3t` và blacklist text: `"bạn đang nghĩ gì"`, `"ban dang nghi gi"`, `"what's on your mind"` trong Pass 4.
  2. Bổ sung trong `dismiss_profile_overlays` handler nhận diện Camera/Create screen (`"video moi"`, `"bai hat lan truyen"`, `"mau tho bay mau"`, `"dang"`, `"tao"`, `"live"`, hoặc rid `"h7l"`). Tự động tap nút **Đóng** (`h7l` / `(84, 150)` / `keyevent 4`) để phục hồi về Profile chính.

## 2. Recovery Vòng Lặp `open_app()` Khi TikTok Chưa Foreground (Máy 255)
- **Hiện tượng:** Vòng lặp 45s chờ TikTok load chỉ bắt Play Store và uiautomator. Nếu TikTok cold-start crash, hiện dialog ANR / crash hệ thống ("TikTok đã dừng lại" / "Đóng ứng dụng") hoặc Launcher giữ foreground sau 12s, bot không hề retry launch hay dismiss crash dialog mà chờ cạn 45s rồi throw `[01_open] TikTok not foreground after clean launch`.
- **Khắc phục:**
  1. Thêm bộ phát hiện crash dialog ("Đóng ứng dụng", "Close app", "OK") và dismiss.
  2. Nếu sau 12s TikTok vẫn chưa foreground hoặc Launcher (`com.sec.android.app.launcher`) chiếm màn hình: tự động `am force-stop`, HOME và retry `_launch_tiktok()` một lần (`launch_retry = True`).

## 3. Kỷ Luật Terminal Tránh Timeout Trên Repo Lớn (Anti-Hang)
- Thư mục `screenshots_social/` và file log `social_reg_log.txt` (hàng trăm MB, hàng chục nghìn file) sẽ gây timeout 180s nếu dùng:
  - `git log` không có `--no-pager`.
  - Shell globbing diện rộng (`ls screenshots_social/*255*`).
  - `tail -n 20000` trên file lớn đang bị lock bởi background process.
- **Giải pháp:**
  - Luôn dùng `git --no-pager log -n <N>`.
  - Đọc file log lớn bằng Python seek từ cuối file (`f.seek(max(0, size - 500000))`).
  - Kiểm tra file cụ thể thay vì quét diện rộng.
