# Điều tra & Khắc phục Lỗi Trùng Kênh Nguồn (Cross-Folder Source Channel Collision)

## 1. Bối cảnh & Hiện tượng (2026-09-17)
- User phát hiện tài khoản trên thiết bị (ví dụ nick Máy 1 `duongkien1202`) có nội dung video và avatar giống hệt một kênh khác trên farm (kênh "Lớp Toán Thầy Hiếu Live").
- Mặc dù hệ thống đã có cờ `--max-folders-per-channel 1` (mặc định = 1) để ngăn một kênh nguồn bị gán cho nhiều folder, nhưng qua kiểm tra thực tế trên `C:\CodexRuntime\tiktok-video\state.db`, phát hiện có tới **32 kênh nguồn** bị tải trùng vào **65 folder**.

## 2. Nguyên nhân cốt lõi (Root Cause)
Khi soi mã nguồn `D:\Taadaa\Tiktok-video\scripts\download_by_niche.py`:
1. **Lỗ hổng 1: `eligible_sources` chỉ đếm bảng `folders` mà bỏ qua bảng `videos`**:
   - Code cũ:
     ```python
     used = conn.execute(
         f"SELECT COUNT(*) AS n FROM folders WHERE source_channel=? AND status IN ({usage_statuses})",
         (source.url,),
     ).fetchone()["n"]
     if used >= args.max_folders_per_channel:
         continue
     ```
   - Thực tế một Folder có thể tải video từ nhiều kênh bổ trợ (khi kênh chính không đủ candidate). Các video đó được ghi vào bảng `videos (folder, source_channel, status='downloaded')`.
   - Bảng `folders` không ghi nhận các kênh bổ trợ này, nên khi một folder khác chạy sau, nó query bảng `folders` thấy `used == 0` và tiếp tục bốc lại kênh đó.
2. **Lỗ hổng 2: Hàng loạt Folder có `source_channel IS NULL` trong bảng `folders`**:
   - Trong quá khứ (đặc biệt dải folder 1..80), khi folder hoàn thành, trường `folders.source_channel` bị để `NULL` dù bảng `videos` đã lưu đầy đủ danh sách video tải về từ kênh đó.
   - Khi đó câu lệnh `WHERE source_channel=?` trả về 0, bypass hoàn toàn gate chặn trùng kênh.

## 3. Quy tắc khắc phục chuẩn (Invariant Rule)
1. **Khóa chặt Gate SQL ở cả 2 bảng**:
   Câu lệnh kiểm tra tính hợp lệ của nguồn trong `eligible_sources` BẮT BUỘC phải đếm trên tập hợp hợp nhất (UNION) giữa bảng `folders` và bảng `videos`:
   ```sql
   SELECT COUNT(DISTINCT folder) AS n FROM (
       SELECT folder_num AS folder FROM folders WHERE lower(source_channel) = lower(?) AND status IN ('complete','complete_partial')
       UNION
       SELECT folder FROM videos WHERE lower(source_channel) = lower(?) AND status = 'downloaded' AND folder IS NOT NULL
   )
   ```
2. **Không phân bổ kênh nguồn đã dùng cho bất kỳ folder nào khác**:
   Khi `n >= args.max_folders_per_channel` (mặc định 1), nguồn kênh BẮT BUỘC bị loại khỏi `eligible_sources`.
