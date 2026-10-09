# Xử lý Lỗi 'focused package unavailable' & Dumpsys Window Focus trong TikTok Feed Session

## 1. Hiện tượng và Nguyên nhân gốc rễ
Khi chạy feed session trên farm máy Android (đặc biệt các dòng Samsung như Máy 15):
- `observe.py` gọi `get_focused_activity()` để xác định package/activity đang hiển thị trên màn hình.
- Trong nhiều thời điểm (chuyển tab, transition animation, popup nổi), `mCurrentFocus` có thể bị `null`.
- Lệnh query `dumpsys window` toàn phần hoặc `dumpsys window | grep ...` qua `sh -c` mất nhiều thời gian (>5.0s) dẫn tới timeout ADB.
- `dumpsys window displays` không chứa trường `mCurrentFocus` / `mFocusedApp`.
- `FOCUS_RE` không bóc tách được định dạng lồng phức tạp của `mFocusedApp` trên Samsung:
  `mFocusedApp=AppWindowToken{... token=Token{... ActivityRecord{... u0 com.ss.android.ugc.trill/...}}}`
- Khi `get_focused_activity()` trả về `{"package": None, "activity": None}`, hàm `safety_check()` trong `safety.py` lập tức trả về `SAFETY_FAILED` với lỗi `focused package unavailable`, làm đứt phiên chạy dù màn hình thiết bị vẫn đang mở TikTok hợp lệ.

---

## 2. Quy tắc tối ưu truy vấn Focused Activity (`observe.py`)
1. **Lựa chọn lệnh ADB Dumpsys tối ưu:**
   - **TRÁNH:** Chạy toàn bộ `dumpsys window` hoặc chạy piped command `dumpsys window | grep ...` (dễ timeout và nghẽn tiến trình adb.exe trên Windows).
   - **TRÁNH:** Phụ thuộc vào `dumpsys window displays` để tìm focus name vì nó chỉ dump display stack mà không có `mCurrentFocus`.
   - **ƯU TIÊN:** Dùng `dumpsys window windows` (hoàn thành trong ~0.15s) — lệnh này chứa đầy đủ `mCurrentFocus` và `mFocusedApp`.
   - **FALLBACK:** Dùng `dumpsys activity activities` (chứa `mResumedActivity`) và `dumpsys activity recents`.

2. **Định dạng Regex bóc tách `mCurrentFocus` & `mFocusedApp`:**
   ```python
   CURRENT_FOCUS_RE = re.compile(
       r"mCurrentFocus[^\n=]*=\s*(?:Window\{[^\n}]*?\s+)?([A-Za-z0-9_.]+)/([A-Za-z0-9_.$/]+)"
   )
   FOCUSED_APP_RE = re.compile(
       r"mFocusedApp[^\n=]*=\s*(?:AppWindowToken\{|Token\{|ActivityRecord\{)?[^\n}]*?\s+([A-Za-z0-9_.]+)/([A-Za-z0-9_.$/]+)"
   )
   ```

---

## 3. Quy tắc Defense-in-Depth trong `safety_check` (`safety.py`)
Khi `focus_pkg` là `None` hoặc chuỗi rỗng, không được fail ngay lập tức nếu có các bằng chứng thứ cấp xác thực ứng dụng vẫn ở TikTok:
1. **Bằng chứng từ Activity:** Nếu `focus_act` chứa tên package TikTok (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`) hoặc activity thuộc TikTok (`SplashActivity`, `MainActivity`), gán `focus_pkg = expected`.
2. **Bằng chứng từ UI XML dump:** Nếu `raw_xml` đã capture được chứa package TikTok hoặc các id/resource/text đặc trưng của TikTok (`com.ss.android.ugc.trill:id/`, `root_view`, `main_layout`, `viewpager`), gán `focus_pkg = expected`.
3. **Bằng chứng từ màn hình đã nhận diện:** Nếu `detected_screen` là known TikTok screen (`home`, `feed`, `friends`, `for-you`, `profile`, `popup`), gán `focus_pkg = expected`.
4. Chỉ fail `focused package unavailable` khi hoàn toàn không có bất kỳ bằng chứng XML hoặc Activity nào cho thấy TikTok đang chạy ở foreground.

---

## 4. Lệnh Canary Test & Chụp ảnh nghiệm thu chuẩn
Sau khi patch code:
1. Chạy Canary Test trên máy mục tiêu (ví dụ Máy 15):
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 15 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
   ```
2. Chụp ảnh màn hình nghiệm thu:
   ```bash
   adb -s <serial> exec-out screencap -p > D:/Taadaa/m<N>_after.png
   ```
   (Nếu biến môi trường adb chưa có trong PATH của shell, dùng đường dẫn tuyệt đối: `"C:\Program Files (x86)\xiaowei\tools\adb.exe"`).
