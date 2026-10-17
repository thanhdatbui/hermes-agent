# Header Normalization Consumer Drift & Slot Scrambling

Xem chi tiết tại: `references/header-normalization-consumer-drift-and-slot-scrambling-20261017.md` trong skill `automation-core-consumer`.
Quy tắc:
1. Đổi header trên file Excel bắt buộc rà soát toàn bộ các file consumer đọc nó (`upload_preflight.py`, `sync-safe-workbook.py`).
2. Danh sách header alias bắt buộc mở rộng đủ các biến thể cũ và mới.
3. Cấm fallback ngầm điền thứ tự dòng vật lý khi không tìm thấy cột folder; bắt buộc fail-closed.
