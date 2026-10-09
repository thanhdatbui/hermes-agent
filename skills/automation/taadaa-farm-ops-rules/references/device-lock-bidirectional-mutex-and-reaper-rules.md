# Quy chuẩn Device Lock 2 Chiều, Quyền Force-stop & Safety Net 1h TTL

## 1. Sự cố Concurrency & Phân tích Nguyên nhân Cốt tử
Trong quá trình Coordinator test reg TikTok trên thiết bị, Coordinator đã gửi lệnh ADB thô (`am force-stop`, `keyevent 3`) lên máy mà không nhận thức được tiến trình `run_batch_live_2fa.py` (add 2FA TikTok) đang điều khiển máy đó.

**Hai lỗ hổng kiến trúc được bóc tách:**
1. **Lỗ hổng Bypass Lock do Cờ Opt-in:** Trong `social_reg_v1.py`, hàm acquire lock bị bọc bởi `lock_enabled = os.environ.get("DEVICE_LOCK_ENABLED", "").strip().lower() in {"1", "true", "yes"}`. Khi chạy CLI đơn lẻ bằng tay (`python social_reg_v1.py <STT> ...`), cờ này mặc định bằng `False`, khiến script chạy mà **không hề tạo file lock chuẩn `machine_<N>.lock.json`**. Hậu quả: Toàn bộ hệ thống và Coordinator tưởng máy rảnh, nhảy vào can thiệp chéo.
2. **Coordinator gọi ADB thô không kiểm tra Lock:** Coordinator dùng `subprocess.run(["adb", "-s", serial, "shell", "am", "force-stop", ...])` trực tiếp, bỏ qua việc kiểm tra xem file lock của máy có đang tồn tại và thuộc về một PID còn sống hay không.

---

## 2. Quy tắc Quyền Force-Stop khi Test Đồ
- **Câu hỏi:** *Khi test đồ có được force-stop không?*
- **Quy chuẩn:** **CÓ, VẪN CẦN THIẾT.** Thao tác `am force-stop` là hygiene dọn dẹp cơ bản để đưa app về clean state trước khi chạy test.
- **RÀNG BUỘC CỨNG (INVARIANT):** 
  - Chỉ tiến trình **ĐANG NẮM GIỮ DEVICE LOCK HỢP LỆ** trên máy đó mới có quyền gọi `am force-stop` và `input keyevent 3`.
  - Coordinator hoặc bất kỳ tiến trình ngoài lề nào **TUYỆT ĐỐI CẤM** tự ý force-stop một máy mà một PID khác đang sở hữu lock.
  - Khi bắt gặp màn hình lạ (màn hình cài đặt 2FA Authenticator, màn hình upload video, v.v.): **DỪNG LẠI NGAY (FREEZE & HANDS-OFF)**, tuyệt đối không được tự suy diễn là "treo/kẹt" rồi dọn dẹp phá hoại.

---

## 3. Kiến trúc Khóa Hai Chiều (Bidirectional Device Lock Enforcement)
1. **Xóa sổ hoàn toàn cờ bypass:**
   - Mọi script và runner (kể cả lệnh test CLI đơn lẻ) bắt buộc ép cứng `user_authorized=True` khi gọi `acquire_device_lock()`.
   - File lock `machine_<N>.lock.json` phải được ghi nhận tại `~/.codex/device-locks/`.
2. **Khóa ngay tại Entrypoint:**
   - Kiểm tra `acquire_device_lock` ngay dòng đầu tiên của hàm thực thi chính (`register()`, `login()`, `feed()`).
   - Nếu máy đang có lock của cron hay script khác: **LẬP TỨC DỪNG LẠI (SAFE-ABORT)**, không gửi bất kỳ thao tác ADB nào vào máy.
3. **Giải phóng an toàn trong `finally:`**:
   - Luôn bọc execution trong khối `try ... finally: dev_lease.release()`, đảm bảo nhả lock trong mọi tình huống (thành công, lỗi logic, hoặc exception).

---

## 4. Cơ chế Cron Tháo Lock Treo (Safety Net 3600s TTL)
- **File thực thi:** `D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py` (giám sát bởi `watch_device_locks.py`).
- **Nguyên tắc hoạt động:**
  - Định kỳ quét thư mục `~/.codex/device-locks/`.
  - **Chỉ dọn dẹp khi thỏa mãn 1 trong 2 điều kiện:**
    1. Tiến trình chủ sở hữu đã chết (`owner_process_alive(d) == False`).
    2. Tuổi của lock vượt quá ngưỡng an toàn **1 giờ (TTL = 3600 giây)**.
  - Khi reaped: Tự động di chuyển file lock vào `device-locks-reaped/` và phát lệnh ADB:
    ```bash
    am force-stop com.ss.android.ugc.trill
    am force-stop com.zhiliaoapp.musically
    input keyevent 3
    ```
- **Lưu ý:** Đây là cơ chế duy nhất được phép tự động tháo lock và reset máy về Home. Các tiến trình khác không được tự tiện tháo lock của nhau.

---

## 5. Kinh nghiệm Chọn Mail Sàn dongvanfb.net cho Quy trình Reg & Ngâm 7 Ngày
- **Loại 1 (ID 5 - Hotmail TRUSTED [GRAPH API]):**
  - **LỖI:** Refresh token bị shop bóp scope hẹp (`IMAP/POP/SMTP`), **thiếu quyền `Mail.Read`**. Tool Farm gọi Microsoft Graph API sẽ bị lỗi `Graph token invalid.` -> **CẤM DÙNG**.
- **Loại 3 (ID 57 - HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM - 350đ):**
  - **CHUẨN 100%:** Cấp full quyền Graph API (`User.Read`, `Mail.ReadWrite`, `Mail.Read`, `IMAP`, `POP`, `SMTP`). Tool Farm đọc OTP tự động từ PC mượt mà.
  - **Khớp quy trình của User:** Mail có sẵn email khôi phục `@fviainboxes.com`. Sau khi reg TikTok và ngâm 7 ngày:
    1. Đăng nhập Microsoft đổi password -> Tích chọn *"Sign me out of all devices"* để đá toàn bộ thiết bị cũ của shop.
    2. Vào *Security / Advanced Security Options* gỡ bỏ mail `@fviainboxes.com` và thêm thông tin chính chủ của user.
