# Niche Migration & 6h Watchdog Cadence (Operator Incident 07/10/2026)

## 1. Bối cảnh sự cố: "Lúc thì gái lúc thì công nghệ"
- **Hiện tượng:** Kênh `@ngobaoquynh29` (Máy 15, Tik 7) trong Excel (`Tik7.xlsx`) ghi niche là `Công nghệ`, nhưng thư mục nuôi `119` lại chứa lẫn lộn video vẽ tranh/nữ sinh và video talkshow/podcast công nghệ cũ.
- **Phản ứng của Operator:** *"Chứ sao lúc thì gái lúc thì công nghệ"*, sau đó ra lệnh dứt khoát: *"Niche đang chạy k hot thì dọn luôn đi đổi qua cào niche hot"*.

## 2. Quy trình 6 bước chuẩn hóa khi Đổi Niche cho tài khoản Farm
1. **Dọn sạch toàn bộ media cũ (video + avatar):**
   - Xóa 100% file `.mp4`, `.part`, `.ytdl`, `.json` và `avatar.jpg` cũ ở cả:
     - Thư mục video gốc (`D:\video goc\<Folder Gốc>`)
     - Thư mục video nuôi (`D:\TIKTOK-videonuoinick\<Folder Video>`)
     - Thư mục video gốc mapping (`D:\video goc\<Folder Video>`)
   - Tuyệt đối không giữ lại bất kỳ clip hay avatar nào của niche cũ để tránh tráo trộn content.

2. **Xóa queue avatar cũ trong Database:**
   - Chạy lệnh: `DELETE FROM avatar_replace_queue WHERE username = '<target_username>';` trong `D:\Taadaa\data\tiktok_tracker.db`.
   - **Mục đích:** Ngăn chặn cron watchdog (`post_evening_avatar_watchdog.py`) bốc file avatar cũ còn sót trên đĩa đi upload lên thiết bị trong khi video mới chưa tải xong.

3. **Cập nhật Niche trong Excel (`Tik1..8.xlsx`):**
   - Chuyển `Keyword Video` sang 1 trong 12 Niche Hot (ví dụ `Gái xinh VN`, `Douyin Biến hình`, `Thú cưng cute`, `Món ngon đường phố`...).
   - Cập nhật `Hashtag Pool` tương ứng với niche mới.
   - Set `Render Status` = `PENDING`, `Avatar` = `PENDING`.

4. **Cào video mới đúng chuẩn 1 FOLDER = 1 KÊNH DUY NHẤT & GOM VIDEO THỪA VÀO CURATED POOL:**
   - Dùng script chuẩn `download_single_channel_to_folder.py` (chú ý cờ `--channel <url>`, không dùng `--channel-url`).
   - Tải tối thiểu 40–45 video MP4 có duration chuẩn [10s, 45s] từ 1 kênh duy nhất thuộc niche hot.
   - Ghi claim kênh vào `data/gaixinh_channel_claims.json` (hoặc claims registry của niche) để tránh folder khác tải trùng kênh.
   - **GOM VIDEO DƯ VÀO BỂ GỘP ĐA KÊNH (`D:\video goc\curated_pool`) (CRITICAL OPERATOR INVARIANT):**
     * Kênh độc quyền CHỈ lấy đúng `[0 : 45]` video (`1.mp4..45.mp4`).
     * Toàn bộ video thừa còn lại từ clip thứ 46 trở đi (ví dụ tải 298 clip thì thừa 253 clip) BẮT BUỘC phải gom ngay sang `D:\video goc\curated_pool` với định dạng tên: `{channel_name}_{video_id}.mp4`.
     * Tuyệt đối không xóa bỏ hay để thất thoát video thừa; đây là nguồn nguyên liệu chất lượng cao đã được tải sẵn để cấp cho các folder tổng hợp đa kênh (`curated_mix`) trên farm mà không lo trùng lặp video với kênh độc quyền.

5. **Trích xuất Avatar đại diện từ video mới & Set Queue PENDING:**
   - Trích xuất frame cận cảnh/trung cận đại diện từ video mới tải (seek 3.0s - 11.0s, tránh banner, phụ đề, viền đen).
   - Soi mắt đọc ảnh qua Direct Vision API / `inspect_avatars.py` để đảm bảo đạt tiêu chuẩn trực quan 10/10.
   - Đồng bộ file avatar vào cả 4 đầu đường dẫn:
     - `D:\video goc\<Folder Gốc>\avatar.jpg`
     - `D:\video goc\<Folder Video>\avatar.jpg`
     - `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`
   - INSERT/UPDATE vào `avatar_replace_queue`:
     ```sql
     INSERT OR REPLACE INTO avatar_replace_queue 
     (username, may, tik, host_id, folder_video, video_goc, status, last_error, updated_at)
     VALUES (?, ?, ?, 'kibe', ?, ?, 'PENDING', NULL, datetime('now', 'localtime'));
     ```

6. **Kích hoạt Render thành phẩm:**
   - Chạy `random_batch_render.py` với cấu hình 11 tầng phá băm âm thanh và hình ảnh:
     `python D:/Taadaa/Tiktok-video/scripts/random_batch_render.py --input-dir "D:/video goc/<folder>" --output-dir "D:/TIKTOK-videonuoinick/<folder>" --preset "presets/preset_owner.json" --randomize --slot <slot_idx> --machine-id <m_idx> --run-id "..." --parallel 2`
   - Đảm bảo đủ 45 video thành phẩm trong `TIKTOK-videonuoinick\<folder>` sẵn sàng cho runner upload.

---

## 3. Kỷ luật tần suất báo cáo Watchdog ("Báo 6 tiếng 1 lần thôi")
- Operator chấn chỉnh gay gắt khi watchdog bắn báo cáo quá dày: *"Báo 6 tiếng 1 lần thôi"*, *"R có gì báo cáo ở đây"*.
- **Quy tắc cứng:**
  - Watchdog báo cáo tiến độ toàn farm (`farm-render-download-watchdog`) BẮT BUỘC cấu hình cron **đúng 6 tiếng / 1 lần**:
    `schedule = '0 */6 * * *'` (chạy vào các mốc cố định: `00:00`, `06:00`, `12:00`, `18:00`).
  - Tuyệt đối CẤM đặt chu kỳ 1 tiếng (`0 * * * *`) hay 30 phút làm spam màn hình Telegram của Operator.
  - Khi một tiến trình phụ trợ hoàn tất (như runner upload avatar cũ chạy xong sau khi đã quyết định chuyển niche), KHÔNG spam báo cáo kết quả thừa thãi làm Operator mất tập trung. Bỏ qua tiến trình cũ và báo cáo ngắn gọn trạng thái task chính.
