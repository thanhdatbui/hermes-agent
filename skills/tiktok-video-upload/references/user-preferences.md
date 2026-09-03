# User Preferences - Kibe

## Báo cáo format
- Ngắn gọn, tiếng Việt, không emoji
- Format: Mục đích → Kết quả → Blocker
- Không kể tiến độ (progress narration)
- Báo cáo batch/cron: chỉ máy Success và máy Fail (kèm mã lỗi nếu có)
- Cấm spam từng dòng per-machine [OK]
- Reviewer REJECT phải sửa tiếp đến APPROVED mới push

## Format báo cáo chi tiết
Mục đích: [mô tả ngắn what đang chạy]
Kết quả: [kết quả thực tế, có error code k]
Blocker: [ lý do blocker k hoặc None]

## Ví dụ
Mục đích → Kết quả → Blocker
Chạy batch Tik2: 46/55 verified THÀNH CÔNG; 9 failed trên NON-avatar causes