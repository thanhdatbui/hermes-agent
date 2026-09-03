# TikTok cache-clear policy & launcher-widget tapping (2026-08-10, user-chốt)

## Cache-clear rules (bắt buộc, user quyết định)

- **CẤM `pm clear` (và `pm clear --cache-only` nếu app không cho)**: nó xóa app data → văng tài khoản (mất login state/token). Tuyệt đối không dùng ở farm này.
- **`reboot` KHÔNG clear cache** — chỉ clear RAM; login state/cache app vẫn giữ nguyên. Reboot an toàn cho account.
- **Cách clear cache an toàn duy nhất = tap qua UI trong app TikTok**: Settings → (Cài đặt và quyền riêng tư) → Dung lượng / "Giải phóng dung lượng" → nút **"Xóa"** cạnh "Bộ nhớ đệm" (vd 305MB). Màn hình ghi rõ "sẽ không ảnh hưởng đến trải nghiệm TikTok" = KHÔNG văng acc. Mục "Tải về" (effects/filters/offline video) xóa được nhưng không cần thiết.
- Tần suất (user chốt 08-10): clear cache **1 lần/ngày SAU block cuối (02:00)** — KHÔNG clear giữa các phiên (cache phục vụ chính các phiên, đỡ tải lại dữ liệu), không clear trước block 1. Script đã commit vào **automation-core** `scripts/clear-tiktok-cache.py` (commit `68b5690`, master 08-10); consumer chỉ giữ bản copy `python_runner/scripts/clear-tiktok-cache.py`.

## Cơ chế mở thẳng màn hình Giải phóng dung lượng (Deep Link - Primary)

- **Mở trực tiếp bằng Deep Link nội bộ (Không cần widget Home):**
  ```bash
  adb shell am start -a android.intent.action.VIEW -d "snssdk1180://clean_cache" com.ss.android.ugc.trill
  ```
  *(Với app bản quốc tế / musically: dùng scheme `snssdk1233://clean_cache`).*
- **Ưu điểm:**
  1. Hoạt động trên 100% các máy mà không bắt buộc phải tạo/kéo widget ra màn hình Home thủ công.
  2. Không phụ thuộc vào tọa độ `(810, 260)` hay độ phân giải màn hình.
  3. Mở thẳng `TikTokHostActivity` tại màn hình "Giải phóng dung lượng" an toàn, không lo Permission Denial.

## Launcher widget / shortcut "Xóa bộ nhớ đệm" trên home (Fallback)

- User có widget do **chính app TikTok tạo** (SmallAppWidgetProvider — check qua `dumpsys package com.ss.android.ugc.trill | grep -i AppWidget`), đặt trên home, bấm vào mở thẳng màn Giải phóng dung lượng.
- **Widget launcher KHÔNG hiện trong uiautomator dump** (không phải accessibility node) và **không mở được bằng `am start -n ...TikTokHostActivity`** (SecurityException: not exported). Nhưng **tap tọa độ qua ADB được**: `input tap x y` → màn Giải phóng dung lượng mở ra → dump UI tìm nút text="Xóa" → tap → recapture verify dung lượng giảm.
- Để tìm widget: chụp `screencap` + vision_analyze xác định tọa độ icon; đừng chỉ dựa vào UI dump.

## Verified flow (M5 & M21, RESOLVED)

Quy trình chuẩn dọn cache an toàn:
1. Gửi intent deep link: `am start -a android.intent.action.VIEW -d "snssdk1180://clean_cache" com.ss.android.ugc.trill` (nếu không mở thì fallback tap widget `(810, 260)`).
2. Dump UI (ATX-agent TCP 7912 primary) → node content-desc chứa "Bộ nhớ đệm" bounds `[24,807][1056,1134]`; nút text="Xóa" trong row đó `[811,872][894,923]` → tap tâm `(852,897)`.
3. Dialog "Xóa bộ nhớ đệm?": "Xóa" `[541,1024][960,1167]` / "Hủy" `[120,1024][539,1167]` → tap Xóa `(750,1095)`.
4. Verify: `Bộ nhớ đệm: 0,0MB`. Focus vẫn TikTokHostActivity = không văng acc.
5. `KEYCODE_HOME`.

Script: `python_runner/scripts/clear-tiktok-cache.py` / `cron_clear_tiktok_cache.py`.

## Cron job tự động dọn cache cuối ngày (04:00)
- Cron job `end-of-day-clear-tiktok-cache` (`cron_clear_tiktok_cache.py`) chạy lúc **04:00 AM** hàng ngày.
- **Khung giờ an toàn:** Tách biệt với chuỗi Reg ban đêm (00:00 - 03:00) và chu kỳ lướt feed sáng (06:00).
- **Chạy đa luồng (Concurrent workers=10):** Tuyệt đối KHÔNG chạy tuần tự (sequential) 80 máy vì sẽ dính timeout 3600s của cron runner. Chạy đa luồng hoàn tất toàn bộ 80 máy trong 2-3 phút.
- **Bất biến sau khi dọn cache (Cleanup & Orientation Guarantee):**
  - Mọi máy sau khi dọn cache (thành công hay timeout/fail) BẮT BUỘC phải qua khối `finally` để:
    1. `am force-stop com.ss.android.ugc.trill` (đóng hoàn toàn TikTok).
    2. `input keyevent KEYCODE_HOME` (trả về màn hình Home).
    3. `settings put system accelerometer_rotation 0` và `user_rotation 0` (khóa cứng hướng màn hình dọc portrait, tránh tình trạng app làm xoay ngang màn hình).
- Invariant bất biến: **CẤM `pm clear`**.

Bài học khi UI không khớp ảnh user gửi: (a) dump không thấy widget ≠ máy không có widget — LUÔN screencap + nhìn bằng mắt/vision trước khi kết luận; (b) home layout có thể đổi giữa các lần capture — chụp lại màn hiện tại, không đối chiếu layout cũ; (c) xác minh máy/serial: workbook `TaiKhoan` → `adb devices` → đối chiếu giờ/model/mCurrentFocus với phần mềm xiaowei (user: "Đừng ns m dò sai series") — serial tra từ workbook, không đoán; (d) đừng tap bừa trên 80 máy khi chưa verify.
