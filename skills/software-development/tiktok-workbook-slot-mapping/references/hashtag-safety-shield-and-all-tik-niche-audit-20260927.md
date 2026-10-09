# Hashtag Safety Shield & All-Tik Niche Audit (2026-09-27)

## 1. Sự cố Lệch Hashtag Toàn Farm (Niche Desync)
- **Triệu chứng**:
  - Video thực tế đăng lên TikTok bị gán hashtag sai chủ đề hoàn toàn (VD: Kênh gái xinh/selfie `@hiencao179` gắn hashtag `#game #gamingvietnam`, clip Tin 3 phút phóng sự xã hội `@chungan981` gắn `#nhacvietnam #singing #amnhac`).
  - Nghiêm trọng hơn: 167 folder bị kẹt nhãn `pending` trong `state.db` khiến workbook sinh hashtag rác `#pending #pendingvietnam #pendingmoingay`.
- **Nguyên nhân gốc rễ**:
  1. **Lệch mapping khởi tạo**: Khi nạp `state.db`, các folder tải về bị map máy móc 1:1 theo số thứ tự dòng của `niches_pool.txt` (Folder 33 = dòng 33 "Gym" dù tải kênh *Xuân Hinh Official*, Folder 49 = dòng 49 "Game" dù tải kênh *Yoga Phương Thùy*, Folder 92 = dòng 92 "Mẹ và bé" dù tải *Otofun*).
  2. **Engine sinh hashtag cũ**: Bốc ngẫu nhiên 3-5 hashtag từ cột `Hashtag Pool` trong workbook. Khi pool chứa toàn tag niche bị sai, toàn bộ 3-5 hashtag trong bài đăng đều bị sai nghiêm trọng.

## 2. Lớp Khiên Bảo Vệ Hashtag (Hashtag Safety Shield Engine)
Cập nhật trong `D:\Taadaa\Tiktok-video\scripts\tiktok_workflow\hashtag_selector.py`:
- **Số lượng**: Giữ nguyên phân phối tự nhiên 3-5 tag/video (`HASHTAG_COUNT_WEIGHTS = {3: 15, 4: 55, 5: 30}`).
- **Cơ cấu phân bổ an toàn**:
  - **2 đến 4 hashtag viral quốc dân**: Bốc ngẫu nhiên từ `COMMON_VIRAL_HASHTAGS`:
    `["#fyp", "#xuhuong", "#videohay", "#viral", "#trending", "#tiktokvietnam", "#moingay", "#hay"]`
  - **Tối đa DUY NHẤT 1 hashtag Niche/Keyword**: Chỉ bốc tối đa 1 tag ngách từ `keyword_video` hoặc `Hashtag Pool`. Nếu không có niche tag hợp lệ, điền 100% bằng tag viral.
  - **Shuffle ngẫu nhiên**: Xáo trộn thứ tự các tag để niche tag không luôn nằm cố định ở đầu/cuối.
- **Lợi ích**: Kể cả khi folder nguồn có bị lệch niche trong tương lai, bài đăng chỉ dính tối đa 1 tag ngách, 3-4 tag còn lại kéo ngữ cảnh chung, thuật toán TikTok 2026 (AI đọc visual/audio) vẫn phân phối chuẩn.
- **Unit test bảo chứng**: `D:\Taadaa\Tiktok-video\tests\test_hashtag_selector.py` kiểm tra 100 lần chọn ngẫu nhiên, bảo đảm không trùng lặp, 3-5 tag, tối đa 1 niche tag.

## 3. Quy trình Đối Soát & Chuẩn Hóa Niche Toàn Diện (All-Tik 640 Accounts)
1. **Cứu dữ liệu Pending từ `state-real-1-tiktok-final.db`**:
   - `state-real-1-tiktok-final.db` lưu trữ nguồn tải gốc của 166 folder bị kẹt `pending` trong `state.db`.
   - Copy niche và channel chuẩn từ `final.db` sang `D:\CodexRuntime\tiktok-video\state.db`.
2. **Map Niche từ Metadata Kênh Thật (`uploader` / `source_channel`)**:
   - Truy vấn bảng `videos` để lấy tên kênh thật của các folder (VD: *Xuân Hinh* -> `haihuoc`, *Mê Xe/Otofun* -> `oto`, *nhaTO/Long Thành* -> `noithat`, *Tin 3 Phút/VTC/VTV24/Thanh Niên* -> `cauchuyen`/`cuocsong`, *Yoga Phương Thùy* -> `yoga`).
   - Cập nhật cột `niche` chuẩn trong bảng `folders` của `state.db`.
3. **Đồng bộ hàng loạt sang 8 file Tik (`Tik1.xlsx` .. `Tik8.xlsx`)**:
   - Chạy `python C:\Users\Kibe\AppData\Local\hermes\scripts\sync_all_tik_keywords.py`.
   - Script tự động đọc `state.db`, sinh `Hashtag Pool` chuẩn và dùng `atomic_workbook_update` (kèm file backup `.bak`) để ghi vào cả sheet `TaiKhoan` và `Hashtag theo Folder`.
4. **Tiêu chuẩn nghiệm thu 100% Farm**:
   - Quét toàn bộ 640 hàng của 8 file `Tik*.xlsx`: **0 ô rỗng**, **0 ô pending**, **100% có Keyword Video & Hashtag Pool hợp lệ**.
