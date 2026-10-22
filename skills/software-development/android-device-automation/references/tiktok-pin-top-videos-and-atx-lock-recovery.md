# Vận hành Ghim Video TikTok & Khắc phục Treo Device Lock / ATX Dump

## 1. Cơ chế Tự động Quét và Ghim Top Video (`pin_top_videos.py`)
Tool `D:/Taadaa/tools/pin_top_videos.py` là canonical tool để quản lý ghim video top view trên TikTok Profile:
- **Tự động bóc tách và sắp xếp:** Quét toàn bộ video tiles từ UI XML màn hình Profile, nhận diện định dạng số lượt xem (`17,8K`, `8.853`, `1.2M`, `4.544`), tự động sort giảm dần theo views (`reverse=True`).
- **Cơ chế Auto-Swap:** Khi profile đã đạt số lượng ghim tối đa (`--max-pins 3`), script tự so sánh candidate chưa ghim có view cao nhất với video đang ghim có view thấp nhất. Nếu video mới có view cao hơn, script tự động bỏ ghim clip thấp và ghim clip mới lên đầu.
- **Lệnh chuẩn kiểm tra & thực thi:**
  ```bash
  # Quét kiểm tra trước (dry-run)
  python D:/Taadaa/tools/pin_top_videos.py --machine <N> --account <username> --min-views 1000 --dry-run

  # Thực thi ghim video
  python D:/Taadaa/tools/pin_top_videos.py --machine <N> --account <username> --min-views 1000 --max-pins 3
  ```

---

## 2. Xử lý Hiện Trường Treo Lock & Lỗi ATX UI Dump Trả Về Rỗng (`status: empty`)

### Hiện tượng
Khi chạy `pin_top_videos.py` hoặc các thao tác cần đọc UI XML trên thiết bị:
- Lệnh bị timeout sau 45s-60s hoặc báo lỗi:
  `UI_DUMP_INVALID: adapter returned non-XML UI state` / `dump_profile_ui_atx ... status: empty`
- Hoặc kẹt ở bước xin lock thiết bị: `lock_acquire_start` mà không `lock_acquired`.

### Nguyên nhân cốt lõi
1. **Device Lock tồn dư / deadlock:** Phiên làm việc trước đó hoặc tiến trình nền bị ngắt đột ngột để lại lock active hoặc timeout treo.
2. **Thiết bị ngủ sâu (Screen OFF / Dozing):** Khi màn hình tắt, uiautomator và ATX daemon không bắt được hierarchy hiển thị.
3. **`atx-agent` (port 7912) trên thiết bị bị crash / chưa khởi động nền.**

### Quy trình Khắc phục Hiện trường Chuẩn (O(1))
TUYỆT ĐỐI KHÔNG dùng adb input tap/keyevent can thiệp tay trần (vi phạm Hard Gate Farm Safety). Thực hiện đúng 2 bước phục hồi chuẩn:

1. **Giải phóng lock tồn dư an toàn bằng cờ `--force-preempt`:**
   ```bash
   python D:/Taadaa/tools/with_device_lock.py --machine <N> --force-preempt -- echo "lock_cleared"
   ```

2. **Khởi động lại dịch vụ ATX daemon chạy nền qua wrapper lock:**
   ```bash
   python D:/Taadaa/tools/with_device_lock.py --machine <N> --force-preempt -- adb -s <serial> shell "/data/local/tmp/atx-agent server -d"
   ```
   *Lưu ý:* Cần đảm bảo `atx-agent listening on :7912` trước khi gọi lại script tương tác UI.
