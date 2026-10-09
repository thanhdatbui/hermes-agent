# Device Lock & Batch Concurrency Pitfalls

Khi chạy `social_reg_v1.py <stt> --email <mail> --ss` hoặc các script con của Tiktok_Reg:
1. Script tích hợp sẵn cơ chế kiểm tra `acquire_device_lock` qua `automation-core`.
2. Nếu máy đang nằm trong hàng đợi hoặc đang thực thi bởi một batch khác (ví dụ: `tiktok-add-bao-mat-f2a` đang giữ lock với PID còn sống tại `~/.codex/device-locks/machine_<stt>.lock.json`), script sẽ tự động dừng với thông báo:
   ```text
   [device-lock] SKIP register machine <stt>: device lock active ...
   ⚠ STT <stt> đang bị khóa bởi tiến trình/cron khác -> DỪNG để đảm bảo an toàn.
   ```
3. **Quy tắc ứng xử:**
   - TUYỆT ĐỐI KHÔNG can thiệp tắt tiến trình hoặc xóa file lock thủ công khi tiến trình cha của batch kia còn đang chạy (`PID exists: True`).
   - Kiểm tra PID và file lock trước khi thực hiện chuyển đổi target machine trong file Excel `gmail_clean_v2.xlsx`.
   - Nếu tất cả các máy dự phòng đều đang có lock active, báo cáo ngay tình trạng blocker tới người dùng kèm theo PID và project đang chiếm dụng máy.
