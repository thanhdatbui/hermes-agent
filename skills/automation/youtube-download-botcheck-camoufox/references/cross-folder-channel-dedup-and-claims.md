# Cross-Folder Channel Deduplication & Persistent Claims (GaiXinh Pipelines)

## Bối cảnh & Mục tiêu
Trong hệ thống `D:/Taadaa/Tiktok-video`, các pipeline phân phối và tải video như `smart_gaixinh_distributor.py` và `download_gaixinh_pipeline.py` phụ trách quét nguồn từ `data/source_manifest_gaixinh.jsonl` và phân bổ vào các folder số tại `D:/video goc/<folder_num>`.
Nếu không có cơ chế quản lý claims tập trung (centralized persistent registry), các đợt chạy độc lập hoặc các folder xử lý tuần tự có thể cấp trùng kênh nguồn giữa các folder khác nhau, vi phạm nguyên tắc bất biến: **1 kênh duy nhất không được phân bổ lặp lại trên nhiều folder khác nhau**.

## Kiến trúc Claims 2 Tầng (Central Registry & Folder Descriptors)

### 1. Central Registry: `data/gaixinh_channel_claims.json`
Lưu trữ trạng thái claim tập trung của toàn bộ các kênh gái xinh đã phân bổ:
```json
{
  "claims": {
    "https://www.tiktok.com/@hoaa.hanassii": {
      "folder": "31",
      "uploader": "hoaa.hanassii",
      "claimed_at": "2026-09-24T12:00:00"
    },
    "https://www.tiktok.com/@gi.xinh.y46": {
      "folder": "63",
      "uploader": "gi.xinh.y46",
      "claimed_at": "2026-09-24T12:00:00"
    },
    "https://www.tiktok.com/@gaixinh_moingay2026": {
      "folder": "79",
      "uploader": "gaixinh_moingay2026",
      "claimed_at": "2026-09-24T12:00:00"
    },
    "https://www.tiktok.com/@gaixinhday.ne": {
      "folder": "95",
      "uploader": "gaixinhday.ne",
      "claimed_at": "2026-09-24T12:00:00"
    }
  }
}
```

### 2. Folder Descriptor: `D:/video goc/<folder_num>/channel_info.json`
Mỗi output folder khi được gán kênh sẽ có file định danh tại chỗ:
```json
{
  "folder": "63",
  "channel_url": "https://www.tiktok.com/@gi.xinh.y46",
  "uploader": "gi.xinh.y46",
  "assigned_at": "2026-09-24T12:00:00"
}
```

## Nguyên tắc Hoạt động & Fallback

1. **Chuẩn hóa URL Kênh (Channel Normalization)**:
   - Strip trailing slashes, chuyển lowercase phần domain/path, bỏ query parameters trước khi so sánh hoặc lưu key claim:
     `normalize_channel_url("https://www.tiktok.com/@user/") -> "https://www.tiktok.com/@user"`.
2. **Kiểm tra Claim trước khi gán (Pre-assignment Gate)**:
   - Khi `smart_gaixinh_distributor.py` phân loại Exclusive/Curated hoặc `download_gaixinh_pipeline.py` duyệt manifest:
     - Bỏ qua bất kỳ kênh nào đã được claim bởi folder khác (`claimed_folder != current_folder`).
     - Cho phép giữ lại nếu chính folder hiện tại đang claim kênh đó (idempotent re-run).
3. **Giải phóng Claim khi `--clean-old`**:
   - Khi gọi `--clean-old` cho `<folder_num>`, hàm dọn dẹp BẮT BUỘC:
     - Xóa các claims trong `gaixinh_channel_claims.json` thuộc về `<folder_num>`.
     - Xóa `channel_info.json` trong thư mục đích cùng toàn bộ video cũ.
4. **Tự động Reconciliation khi khởi động**:
   - Quét các thư mục hiện có trong `output_root`: nếu tìm thấy `channel_info.json`, tự động đồng bộ (backfill) vào `gaixinh_channel_claims.json` nếu chưa có.

## Kỷ luật Tool Call Budget & Tránh Analysis Paralysis
- Khi debug hoặc bổ sung tính năng deduplication trên các script lớn (>500 lines):
  - **CẤM** phân trang đọc tuần tự toàn bộ file từ dòng 1 đến hết bằng `read_file` gây cạn kiệt tool budget (max 15-20 calls).
  - Sử dụng `search_files` nhắm trúng các hàm quan trọng (`parse_args`, `load_manifest`, `run_pipeline`, `fill_folder_with_videos`).
  - Viết module dùng chung `scripts/gaixinh_claims.py` hoặc helper functions độc lập và phủ kiểm thử bằng pytest/unittest tập trung (`tests/test_gaixinh_channel_dedup.py`).
