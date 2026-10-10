# Admin Cluster Media Root Drift & Niche Reconciliation (2026-10-10)

## 1. Bối cảnh & Hiện tượng
Khi Operator gửi ảnh màn hình một tài khoản bất kỳ trên TikTok (ví dụ: `@holinh1003` - Máy 226 Tik 2 thuộc cụm Admin) và yêu cầu: *"Nick này của tao đúng k chuẩn hoá lại ava hashtag"*:
1. **Định danh trong hệ thống:** Nick thuộc cụm Admin (Máy 226, Slot Tik 2, `ce11160b5531893103`), lưu trong `admin/Tik2.xlsx` và `farm_account_info`.
2. **Lệch Niche & Hashtag:** Cột `Keyword Video` trong `Tik2.xlsx` ghi `Thư viện` (ngách cũ khó viral, đã bị cấm/loại theo kiến trúc 12 Hot Niche), hashtag toàn sách/văn học trong khi kho video liên kết (`Folder Video 202`) lại là **Douyin Nam thần / Visual Học đường**.
3. **Lệch Avatar trên App vs Kho:** Avatar trên app là ảnh selfie đội lưới tóc (wig cap vàng) cầm cọ trang điểm/cosplay (ảnh placeholder cũ từ lúc reg nick). Kho Kibe `D:\TIKTOK-videonuoinick\202\avatar.jpg` có sẵn ảnh nam thần áo len cardigan.
4. **TỬ HUYỆT HẠ TẦNG CỤM ADMIN (Root Drift):**
   - Trên máy chủ Admin (`admin-farm` 192.168.110.119), cấu hình `config-admin.yaml` chỉ định đường dẫn kho media là:
     `avatar_source_root: D:\TIKTOK-videonuoinick-admin`
     `media_source_root: D:\TIKTOK-videonuoinick-admin`
   - Cụm Admin **KHÔNG DÙNG** `D:\TIKTOK-videonuoinick` hay `D:\video goc` như trạm Kibe!
   - Thư mục `D:\TIKTOK-videonuoinick-admin\202` trên Admin từ trước chứa file `avatar.jpg` cũ (ảnh chụp đại cảnh Chùa/Phật giáo) và thiếu các video render mới từ Kibe.
   - Do đó, dù `avatar_replace_queue` trước đó có ghi `status = 'DONE'` hay Watchdog Admin có chạy, thiết bị thật trên Admin không bao giờ nhận được avatar nam thần mới nếu Kibe chưa đồng bộ sang `D:\TIKTOK-videonuoinick-admin\202`!

---

## 2. Quy trình Chuẩn hoá 4 Bước Khắc phục Triệt để

### Bước 1: Đối soát và Sửa Workbook Admin (`Tik<N>.xlsx`)
- Luôn tạo bản sao lưu trước khi sửa: `Tik<N>.xlsx.bak_<timestamp>`.
- Tìm đúng dòng của Máy mục tiêu (ví dụ Máy 226):
  - Cập nhật `Keyword Video`: chuyển sang 1 trong 12 Hot Niche (ví dụ `Douyin Nam thần`).
  - Cập nhật `Hashtag Pool`: thay toàn bộ hashtag cũ bằng bộ hashtag chuẩn viral khớp với nội dung video:
    ```text
    #douyin #traidep #namthan #xuhuong #fyp #visual #handsome #viral #tiktokvietnam #trending #boypho #aesthetic
    ```

### Bước 2: Đồng bộ Kho Media sang Máy chủ Admin (`TIKTOK-videonuoinick-admin`)
- Đồng bộ file ảnh avatar độc bản:
  ```bash
  scp "D:/TIKTOK-videonuoinick/<folder>/avatar.jpg" admin-farm:"D:/TIKTOK-videonuoinick-admin/<folder>/avatar.jpg"
  ```
- Đồng bộ video thành phẩm (nếu thư mục Admin thiếu hoặc lệch nội dung):
  ```bash
  scp -r "D:/TIKTOK-videonuoinick/<folder>" admin-farm:"D:/TIKTOK-videonuoinick-admin/"
  ```
- Kiểm tra lại MD5 hash trên Admin để bảo đảm 100% khớp với file nguồn trên Kibe.

### Bước 3: Nạp Hàng đợi Database SQLite (`tiktok_tracker.db`)
- Cập nhật SQLite trên Kibe:
  ```sql
  UPDATE avatar_replace_queue 
  SET status='PENDING', last_error=NULL, updated_at=datetime('now', 'localtime')
  WHERE username='<username>';
  ```
- Đồng bộ ngay database sang Admin:
  ```bash
  scp D:/Taadaa/data/tiktok_tracker.db admin-farm:D:/Taadaa/data/tiktok_tracker.db
  ```

### Bước 4: Tạo Ảnh Composite Đối chiếu & Kiểm chứng Vision (Gate 6)
- Dựng ảnh composite 3 panel:
  1. Panel 1: Avatar hiện tại trên app (crop từ screenshot của User).
  2. Panel 2: Avatar mới chuẩn hóa (kích thước 512x512).
  3. Panel 3: Giả lập khung tròn TikTok (circular mask có viền tròn).
- Gọi Vision API soi mắt kiểm tra (đọc rõ 3 panel, text không bị che, không lỗi hiển thị) trước khi gửi qua thẻ `MEDIA:`.
