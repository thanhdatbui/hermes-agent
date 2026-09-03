# Verify bài đăng đã lên profile — 3 nguồn độc lập (post-verification)

Dùng khi workflow báo SUCCESS nhưng cần bằng chứng độc lập video đã lên
(hoặc nghi ngờ VERIFY_POST scan không đủ — scan nội bộ chỉ đếm tile trong
viewport, dễ baseline=current).

## Quy trình (máy 74 ví dụ, TikTok 46.3.3 Samsung)

1. **Report JSON** — đọc run mới nhất
   `D:\CodexRuntime\tiktok-video\runs\run_<id>\report.json`:
   - `post_submission_state == ACCEPTED` (+ có `post_tapped_at` /
     `post_submission_accepted_at`) — bằng chứng TikTok NHẬN đăng, mạnh hơn
     `post_verified` đơn thuần.
   - `status == SUCCESS`, `post_verified == True`, `media_fingerprint_status`
     verified sau Post, `video_number` khớp.
2. **Workbook** — `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` sheet TaiKhoan,
   cột `Video Đã Đăng` theo `Máy` phải khớp `video_number`.
3. **Profile thật (proof cuối)** — không tin report một mình:
   ```bash
   ADB="C:/Program Files (x86)/xiaowei/tools/adb.exe"
   "$ADB" -s <serial> shell am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.main.MainActivity
   sleep 14
   "$ADB" -s <serial> shell input tap 972 1883   # tab Hồ sơ (KHÔNG phải nút Quay giữa!)
   sleep 7
   "$ADB" -s <serial> exec-out screencap -p > profile.png
   "$ADB" -s <serial> shell uiautomator dump /sdcard/ui.xml && exec-out cat
   ```
   - PITFALL: tap (540,1840) giữa = nút **Quay** → mở camera, không phải
     profile. Tab Hồ sơ ở (972,1883); xác nhận bằng UI dump có
     `Hồ sơ` (content-desc) + `@username`.
   - Đếm tile video: ImageView `resource-id=...:id/cover` với bounds
     `x2-x1>300 and y2-y1>300` (grid 3 cột, ~360px/tile). Tile MỚI phải xuất
     hiện ở đầu grid (view count nhỏ, thumbnail khác 5-6 tile cũ).
   - Vision model có thể lỗi auth (401) — fallback: đếm cover ImageView từ UI
     dump (regex) + xem ảnh thủ công.

## Nguyên tắc

- Report SUCCESS + workbook đã ghi + profile có tile mới = khớp 3 nguồn → chốt.
- Scan tile nội bộ workflow (`[PROFILE_GRID] Unique video tiles: N (baseline=N)`)
  chỉ chứng minh viewport scan, KHÔNG tự nó chứng minh video mới — luôn cần
  profile proof thủ công khi nghi ngờ.
- Sau post, workflow tự xóa video remote khỏi máy (fingerprint verified sau
  Post) — không tìm file push cũ làm bằng chứng.
