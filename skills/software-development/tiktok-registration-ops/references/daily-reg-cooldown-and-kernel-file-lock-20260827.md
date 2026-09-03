# Quy Tắc Cooldown 1 Ngày, Check-and-Reserve & Kernel File Lock (2026-08-27)

## 1. Cơ Chế Check-and-Reserve & Invariant "1 Máy / 1 Lần Reg / Ngày"
- **Mục đích:** Đảm bảo mỗi máy vật lý chỉ được đăng ký TikTok thành công tối đa 1 lần trong ngày, và không bao giờ có 2 worker đồng thời cùng chạy trên cùng 1 STT.
- **Workflow:**
  1. `reserve_machine_reg_slot(stt, serial)`: Kiểm tra trạng thái máy trong `reg_daily_cooldowns.json`. Nếu máy đang rảnh, đặt trạng thái `in_progress` kèm một `token` UUID độc nhất và trả về token này. Nếu máy đang cooldown, đang in_progress hôm nay, hoặc file bị lỗi, hàm trả về `None` (chặn chạy).
  2. Bọc thân hàm đăng ký trong `try ... finally`:
     - **Nếu SUCCESS:** Gọi `record_machine_reg_success(stt, serial)` ➔ Chuyển trạng thái sang `success`, ghi nhận `cooldown_until = today + 1 day`. Cooldown này tồn tại đến 00:00 ngày hôm sau.
     - **Nếu FAILED / CANCEL / EXCEPTION:** Khối `finally` tự động gọi `release_machine_reg_reservation(stt, token=res_token)` ➔ Giải phóng reservation để cho phép retry sau đó.
  3. **Khóa chống race release:** `release_machine_reg_reservation` bắt buộc phải truyền đúng `token` UUID đã cấp. Bất kỳ lệnh gọi nào với token sai, rỗng hoặc `None` đều bị từ chối, ngăn chặn việc process cũ xóa nhầm reservation của process mới.
  4. **Fail-Closed tuyệt đối:** Nếu file `reg_daily_cooldowns.json` bị corrupt, JSON hỏng hoặc schema sai:
     - `is_machine_reg_cooldown_active()` trả về `True` (chặn).
     - `reserve_machine_reg_slot()` trả về `None` (từ chối cấp slot).
     - `record_machine_reg_success()` raise `RuntimeError` (từ chối ghi đè, bảo vệ cooldown của các máy thành công trước đó).

## 2. Kernel File Locking & Phòng Ngừa Lỗi EOF trên Windows
- **Vấn đề:** Khi nhiều worker chạy song song (đa luồng / đa tiến trình), thao tác Read-Modify-Write trên file JSON chung dễ bị race condition gây ghi đè mất bản ghi (lost update).
- **Giải pháp `_cooldown_file_lock`:**
  - Kết hợp `threading.Lock` (chống race giữa các thread cùng tiến trình) và Kernel OS Lock (chống race giữa các process độc lập).
  - **Trên Windows:** Dùng `msvcrt.locking(fileno, msvcrt.LK_NBLCK, 1)`.
  - **Trên POSIX/Linux:** Dùng `fcntl.flock(fileno, fcntl.LOCK_EX | fcntl.LOCK_NB)`.
  - **Windows EOF Pitfall:** `msvcrt.locking` trên Windows không thể khóa byte vượt quá độ dài file. Nếu file `.flock` rỗng (0 bytes), lệnh lock sẽ thất bại liên tục và dẫn đến timeout 30s. Do đó, khi tạo file lock, **BẮT BUỘC ghi sẵn 1 byte (`b"0"`)** trước khi thực hiện `msvcrt.locking`.
  - **Atomic Replacement:** Mọi thao tác ghi JSON phải ghi ra file tạm kèm UUID (`path.with_suffix(".<uuid>.tmp")`) rồi gọi `os.replace` để tránh file bị rỗng/hỏng nếu tiến trình bị kill giữa chừng.

## 3. Cấm Pause Cron Khi Vận Hành Thủ Công
- **Quy tắc bất biến:** TUYỆT ĐỐI CẤM dùng lệnh pause/tắt cron job của farm khi chạy tay, test hoặc recovery.
- **Cơ chế tự né:** Tất cả cron định kỳ (feed, nuôi acc, reg đêm) và runner đều tự động đọc `device_lock` qua `filter_unlocked_targets`. Máy nào có lock bận thì cron tự động bỏ qua (skip) và chạy các máy rảnh còn lại.
- **Hậu quả nếu pause cron:** Làm tê liệt cron `reap-dead-owner-locks` (script tự động dọn dẹp lock quá hạn TTL 2h và đưa máy về Home) và các watchdog giám sát an toàn của hệ thống.

## 4. Định Dạng Báo Cáo Trên Telegram Cho Thiết Bị Di Động
- **Sự cố:** Chia bảng 2 cột song song (cột trái M01..M34, cột phải M35..M76) để bảng ngắn bớt sẽ làm người dùng xem trên điện thoại nhìn thấy dòng của M33 ngang hàng M76, dẫn đến hiểu nhầm 1 máy đăng ký 2 email.
- **Quy tắc:** Mọi báo cáo danh sách máy / trạng thái tài khoản gửi qua Telegram phải dùng danh sách tuyến tính (1 cột / linear) hoặc nhóm theo cụm rõ ràng, không ghép 2 cột song song.
