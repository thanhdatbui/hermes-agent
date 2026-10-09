# Case REG: Bẫy Widget "Bạn đang nghĩ gì..." (q3t) & Launch Retry cho TikTok Clean Launch

## 1. Bẫy Widget "Bạn đang nghĩ gì..." (rid: q3t) & Màn hình Camera/Tạo Video
- **Hiện tượng lỗi:** `[03_dropdown] Khong mo duoc account dropdown` (Máy 266).
- **Cơ chế lỗi cốt lõi:**
  1. Trong `_try_open_account_dropdown_once` (Pass 4), selector quét các node có `text and not text.startswith("@") and y2 <= 610`. Trên profile TikTok mới, widget đăng tin/story có placeholder `"Bạn đang nghĩ gì..."` mang resource-id `com.ss.android.ugc.trill:id/q3t` tại `bounds=[156,150][924,262]` (`cy~206`).
  2. Do chưa lọc text này và rid `q3t`, bot nhận diện nhầm đây là display name của tài khoản và tap vào `(540, 206)`.
  3. Cú tap này lập tức bung màn hình **Camera / Tạo video / Story** (chứa tabs "TẠO", "ĐĂNG", "LIVE", nút "Video mới" `zgc`/`zge`).
  4. Tại màn hình này, `_wait_account_dropdown_open` thất bại. Khi bot gọi tiếp fallback `_open_account_dropdown_via_settings`, cú tap mù `(1005, 150)` (Menu hồ sơ) lại bấm trúng nút "Video mới" `[717,108][1044,192]` nằm trong màn hình tạo video.
- **Giải pháp:**
  - Trong `_try_open_account_dropdown_once` Pass 4: Bổ sung `"q3t"` vào danh sách rid cấm và thêm `"bạn đang nghĩ gì"`, `"ban dang nghi gi"`, `"what's on your mind"` vào danh sách text bị bỏ qua.
  - Trong `dismiss_profile_overlays`: Bổ sung bộ lọc đóng màn hình Camera / Tạo video khi thấy các dấu hiệu (`"video moi"`, `"bai hat lan truyen"`, `"mau tho bay mau"`, `"dang"` + `"tao"` + `"live"`, hoặc resource-id `h7l`) -> tap nút "Đóng" (`h7l` hoặc bounds `[18,84][150,216]` hoặc keyevent BACK).

## 2. Launch Retry cho `[01_open] TikTok not foreground after clean launch`
- **Hiện tượng lỗi:** Máy 255 chết cứng ở `[01_open] TikTok not foreground after clean launch`.
- **Cơ chế lỗi cốt lõi:**
  - `open_app()` chỉ gọi `_launch_tiktok` một lần ban đầu, sau đó bước vào vòng lặp 45s. Vòng lặp này chỉ retry khi gặp Play Store hoặc uiautomator.
  - Nếu TikTok cold-start bị crash, đơ, kẹt Samsung Keyguard hoặc Launcher (`com.sec.android.app.launcher`) giữ foreground, bot chỉ sleep chờ cạn 45s rồi ném exception `RuntimeError`.
- **Giải pháp:**
  - Thêm cơ chế `launch_retry` sau 12s chờ: Kiểm tra nếu thấy popup crash ("TikTok đã dừng lại", "Đóng ứng dụng") thì dismiss; nếu Keyguard thì unlock; nếu Launcher vẫn ở foreground thì `am force-stop`, bấm HOME và retry `_launch_tiktok` 1 lần.
