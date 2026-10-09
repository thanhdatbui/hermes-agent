# Chống trùng kênh nguồn video xuyên suốt toàn bộ Folders trên Farm

## 1. Nguyên lý cốt lõi: Chống trùng nguồn (Channel-level Deduplication)
- Để đảm bảo không bao giờ có video trùng lặp giữa các folder trên farm, nguyên tắc chuẩn nhất là **chống trùng kênh nguồn (source channel/URL)**:
  - Mỗi kênh nguồn chỉ được gán độc quyền cho duy nhất 1 folder (`1 kênh <-> 1 folder`).
  - Quét và kiểm tra claim trước khi tải hoặc bốc candidate. Nếu một kênh đã được gán cho folder khác -> **SKIP NGAY LẬP TỨC**.

## 2. Cơ chế lưu vết Persistent (Claims Registry)
- File lưu vết trung tâm: `D:/Taadaa/Tiktok-video/data/gaixinh_channel_claims.json`.
- File định danh tại từng folder nguồn: `D:/video goc/<folder_num>/channel_info.json`.
- Cấu trúc bản ghi:
  ```json
  {
    "https://www.tiktok.com/@uploader": {
      "folder": "31",
      "uploader": "uploader",
      "claimed_at": "2026-09-24T14:00:00"
    }
  }
  ```

## 3. Quy tắc vận hành với Script tải (`smart_gaixinh_distributor.py` & `download_gaixinh_pipeline.py`)
- Khi khởi động: Tự động load `gaixinh_channel_claims.json` và scan các folder hiện có trong `D:/video goc/`.
- Khi cấp phát folder:
  - Bỏ qua các kênh đã nằm trong `claims` của folder khác.
  - Sau khi gán kênh cho folder mới: Gọi `claim_channel(...)` để lưu vào file JSON trung tâm và ghi `channel_info.json` vào folder.
- Khi dọn sạch folder (`--clean-old`):
  - Tự động gọi `release_claim_for_folder(claims, folder_num)` để giải phóng claim cũ, cho phép gán nguồn mới sạch sẽ.
