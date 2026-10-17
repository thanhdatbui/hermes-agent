# Zero-Permission Avatar Pipeline & TikTok Tracker DB Path Priority

## 1. Zero-Permission Invariant: Cấm Hỏi "Bạn Có Muốn Tạo Ava Không"
- **User Frustration Signal:** Khi user gửi ảnh profile TikTok yêu cầu "Chuẩn hoá acc này" hoặc ảnh chụp kênh, user phản ứng gay gắt nếu Agent chỉ mô tả hoặc hỏi lại: *"Tạo ava đi chứ hỏi chi v"*.
- **Quy tắc thực thi:**
  - `Đổi ava tự làm cấm hỏi`: Không bao giờ dừng lại ở bước mô tả kênh rồi hỏi người dùng *"Bạn có muốn tôi trích xuất phương án avatar không?"*.
  - BẮT BUỘC tự động chạy ngay quy trình trích xuất $O(1)$ từ video gốc ($F_{src}$), sinh 2 phương án avatar vuông $512 \times 512$ (đầy đủ đầu, tóc, cằm, ngũ quan trong circular mask TikTok), ghép ảnh so sánh `comparison_preview.jpg` kèm `MEDIA:`, và đưa thẳng 2 phương án cho user chọn số (`1` hoặc `2`).

## 2. TikTok Tracker DB Path Resolution Priority
- **Hiện tượng bẫy (Empty DB Trap):**
  - Tại thư mục gốc `D:/Taadaa/tiktok_tracker.db`, file này có thể tồn tại nhưng là database rỗng (0 tables).
  - Database thực tế chứa các bảng quan trọng (`avatar_replace_queue`, `account_mapping`, `farm_account_info`) nằm tại:
    `D:/Taadaa/data/tiktok_tracker.db`
- **Thứ tự ưu tiên phân giải đường dẫn DB bắt buộc:**
  ```python
  import os, sqlite3

  def get_tracker_db_path():
      candidates = [
          "D:/Taadaa/data/tiktok_tracker.db",
          "D:/Taadaa/Tiktok-video/tiktok_tracker.db",
          "D:/Taadaa/tiktok_tracker.db",
      ]
      for p in candidates:
          if os.path.exists(p):
              # Verify that table exists before selecting
              try:
                  conn = sqlite3.connect(p)
                  cur = conn.cursor()
                  cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='avatar_replace_queue'")
                  if cur.fetchone():
                      conn.close()
                      return p
                  conn.close()
              except Exception:
                  pass
      return candidates[0]
  ```
- **Hậu quả nếu viết sai thứ tự:** Gặp lỗi `sqlite3.OperationalError: no such table: avatar_replace_queue` làm crash worker hoặc tiến trình đồng bộ hàng loạt.
