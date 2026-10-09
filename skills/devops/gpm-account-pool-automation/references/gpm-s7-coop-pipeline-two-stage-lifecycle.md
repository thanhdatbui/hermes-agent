# Tách biệt 2 Giai đoạn: Lifecycle Sync GPM vs OAUTH S7 Pipeline

Khi tự động hóa đăng nhập Gmail lên GPMLogin phối hợp với dàn điện thoại Samsung S7 Farm, bắt buộc phải tách biệt nghiêm ngặt 2 giai đoạn:

---

## 1. GIAI ĐOẠN 1: ĐỒNG BỘ VÒNG ĐỜI PROFILE GPM (LIFECYCLE SYNC)
- **Phạm vi tác động:** Chỉ giữa Master Excel (`master_gmail_manager.xlsx`) và GPMLogin Local API/DB trên PC.
- **Tác vụ:**
  + **Dọn dẹp:** Tự động phát hiện các tài khoản trạng thái `DIE`, `BAN`, `SUSPENDED` để xóa bỏ profile tương ứng khỏi GPM qua API (`/profiles/delete/{id}?mode=2`).
  + **Sinh mới:** Quét các tài khoản `LIVE` chưa có profile trong GPM DB, đọc thông tin Proxy từ Excel, gọi API tạo profile (`/profiles/create`).
- **Quy tắc bất biến (Farm Safety Invariant):**
  + **TUYỆT ĐỐI KHÔNG ĐÒI HỎI MÁY S7 ONLINE ADB Ở BƯỚC NÀY.**
  + Việc tạo profile rỗng và gán proxy trên PC hoàn toàn độc lập với thiết bị thật. Không được để việc máy tắt màn hình, sleep, hoặc rớt ADB tạm thời làm nghẽn việc chuẩn bị profile GPM.

---

## 2. GIAI ĐOẠN 2: THỰC THI ĐĂNG NHẬP (OAUTH S7 CO-OP PIPELINE)
- **Phạm vi tác động:** Phối hợp giữa Trình duyệt GPMLogin trên PC và Thiết bị S7 Farm qua ADB.
- **Tác vụ:** Chạy script pipeline (`run_oauth_s7_pipeline.py`) để nhập thông tin, bắt mã xác minh (Google Prompt, mã bảo mật 10 số OOTP trong Google Play Services, hoặc duyệt OTP).
- **Quy tắc phối hợp bắt buộc (Co-op Gate):**
  + **BẮT BUỘC KIỂM TRA MÁY TƯƠNG ỨNG (`mid`) PHẢI ONLINE ADB VÀ RẢNH (IDLE).**
  + Nếu máy offline ADB hoặc đang bận nuôi feed/upload: **BỎ QUA NGAY**, không được cố chấp mở profile trình duyệt để tránh treo checkpoint trên GPM khi không có thiết bị thật phối hợp duyệt mã.

---

## 3. CẢNH BÁO BẪY TÍNH TOÁN BỘ ĐẾM PROXY (PROXY LIMIT GUARD)
- **Pitfall:** Nếu đặt biến đếm sử dụng proxy (`proxy_count[port] += 1`) ngay bên trong vòng lặp duyệt lọc candidates, biến này sẽ tăng khống cho tất cả candidates và được lưu vào state file. Ở các lần tick sau, toàn bộ các cổng proxy sẽ bị coi là đã chạm trần (`MAX_LOGINS_PER_PROXY`) và bị khóa cứng toàn bộ farm dù thực tế chưa hề chạy!
- **Giải pháp chuẩn:**
  + Sử dụng `current_run_proxy_count = dict(proxy_count)` cục bộ chỉ để giới hạn gom batch của lần tick hiện tại.
  + **CHỈ ĐƯỢC TĂNG** bộ đếm bền vững khi worker thực sự hoàn tất hoặc bắt đầu lượt chạy đăng nhập thực tế (`res = fut.result()`).
