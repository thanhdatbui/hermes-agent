# GPM Profile Lifecycle & Preservation Policy

## 1. Nguyên Tắc Cốt Lõi: KHÔNG XÓA Profile GPM Khi Gmail DIE
- **Bối cảnh:** Trong file `sync_gpm_lifecycle.py`, trước đây có logic quét danh sách Gmail có status `DIE`, `BAN`, `SUSPENDED` từ Master Excel và gọi API xóa profile GPM (`/profiles/delete/{pid}?mode=2`).
- **Rủi ro lớn:** Rất nhiều profile GPM chứa session đăng nhập active của OpenAI, ChatGPT, Codex đã được verify số điện thoại hoặc nạp token/cookies có giá trị, ngay cả khi Gmail gốc bị tạm khóa/DIE. Nếu tự động xóa profile GPM, toàn bộ dữ liệu session trình duyệt sẽ mất vĩnh viễn không thể khôi phục.
- **Quy tắc chuẩn hóa:**
  1. **Tuyệt đối KHÔNG gọi API xóa profile GPM tự động** dựa trên trạng thái DIE của Gmail trong master sheet.
  2. Vẫn **duy trì việc đọc `profile_data.db` (SQLite)** để lấy `existing_gpm_emails`. Mục đích: kiểm tra đối chiếu để không tạo trùng profile cho các Gmail LIVE mới.
  3. Biến `deleted_count` giữ cố định là `0` và ghi log cảnh báo/thông báo bỏ qua bước xóa để bảo vệ session.
  4. Cơ chế dọn dẹp DIE chỉ áp dụng cuốn chiếu trên **thiết bị phần cứng S7 (Android physical devices)** qua `remove_account_adb` trong khung giờ sáng có non-blocking lock, tách biệt hoàn toàn khỏi browser profile trên PC.

## 2. Vị trí các script liên quan
- Repo source: `D:\Taadaa\GPM auto\scripts\sync_gpm_lifecycle.py`
- Hermes production script: `C:\Users\Kibe\AppData\Local\hermes\scripts\sync_gpm_lifecycle.py`
- Khi chỉnh sửa bất kỳ logic nào trong `sync_gpm_lifecycle.py`, phải chạy test suite (`python -m pytest tests/`) để đảm bảo không gãy test và luôn đồng bộ sang thư mục `hermes\scripts`.
