# Kỷ luật Dọn sạch Media khi Đổi Niche & Báo cáo Watchdog 6 Tiếng (07/10/2026)

## 1. Bài học thực tế: "Lúc thì gái lúc thì công nghệ"
- **Nguyên nhân cốt lõi:** Khi một tài khoản trong quá khứ bị trộn lẫn video của nhiều đợt tải (ví dụ: clip vẽ tranh/gái xinh trộn lẫn talkshow công nghệ 495), nội dung và avatar bị xộc xệch, mất tính nhất quán.
- **Chỉ thị của Operator:** *"Niche đang chạy k hot thì dọn luôn đi đổi qua cào niche hot"*.

## 2. Quy trình chuẩn hóa khi đổi sang Niche Hot (6 bước)
1. **Dọn sạch triệt để media cũ:** Xóa toàn bộ file `.mp4`, `.part`, `.ytdl`, `.json`, `avatar.jpg` ở cả `video goc` và `TIKTOK-videonuoinick`. Tuyệt đối không giữ lại video cũ.
2. **Xóa queue avatar cũ trong DB:** `DELETE FROM avatar_replace_queue WHERE username='...';` để ngăn watchdog bốc avatar cũ đi upload trước khi video mới sẵn sàng.
3. **Cập nhật Excel `Tik1..8.xlsx`:** Đổi `Keyword Video`, `Hashtag Pool`, đặt `Render Status` = `PENDING`, `Avatar` = `PENDING`.
4. **Cào video mới (1 FOLDER = 1 KÊNH DUY NHẤT):**
   - Chạy script: `python D:/Taadaa/Tiktok-video/scripts/download_single_channel_to_folder.py --channel "<url>" --folder <N> --min-videos 45`
   - **Lưu ý cờ:** Dùng `--channel` (CẤM dùng `--channel-url` vì script sẽ báo lỗi cú pháp).
   - Ghi nhận claim kênh vào `gaixinh_channel_claims.json`.
5. **Trích xuất Avatar từ video mới & Set Queue PENDING:**
   - Trích xuất frame đại diện cận cảnh/trung cận từ video mới tải (seek 3s-11s, không phụ đề, không banner).
   - Soi mắt qua vision đảm bảo chuẩn nét.
   - Đồng bộ vào cả 4 đầu thư mục (`video goc/<Folder Gốc>`, `video goc/<Folder Video>`, `TIKTOK-videonuoinick/<Folder Video>`).
   - Cập nhật lại `avatar_replace_queue` với trạng thái `PENDING`.
6. **Kích hoạt Render thành phẩm:** Chạy `random_batch_render.py` để render 45 clip thành phẩm 11 tầng phá băm vào `TIKTOK-videonuoinick/<Folder Video>`.

## 3. Kỷ luật Báo cáo Watchdog ("Báo 6 tiếng 1 lần thôi")
- Operator yêu cầu rõ ràng: *"Báo 6 tiếng 1 lần thôi"*.
- Cronjob `farm-render-download-watchdog` BẮT BUỘC đặt lịch `0 */6 * * *` (chạy vào 00:00, 06:00, 12:00, 18:00).
- CẤM TUYỆT ĐỐI đặt chu kỳ 1 tiếng hay spam báo cáo tiến trình đã bị hủy bỏ/tiến trình rác làm phiền Operator.
