# Canary Login Pipeline & Post-Login State Reconciliation

Quy trình chuẩn cho việc chạy test đăng nhập canary (Canary Login) qua `run_oauth_s7_pipeline.py`, thu thập bằng chứng screenshot và đồng bộ state hệ thống.

---

## 1. Pre-flight Checks
- **GPMLogin API (port 19995)**:
  Kiểm tra `http://127.0.0.1:19995/api/v3/profiles` trả về HTTP 200 trước khi chạy pipeline.
- **Active Profile Database Path**:
  Đường dẫn SQLite database GPMLogin chính xác:
  `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`
  *(Tránh nhầm lẫn với các file template trong `app_data\empty_data` hoặc bản backup)*.

---

## 2. Lệnh thực thi Canary Login
Ghi lại timestamp bắt đầu (`start_time = time.time()`), sau đó chạy:
```bash
python "D:/Taadaa/GPM auto/scripts/run_oauth_s7_pipeline.py" <email>
```
*Lưu ý: Đặt timeout đủ lớn (240s - 300s) vì quá trình bao gồm mở browser CDP, điều khiển điện thoại S7 qua ADB để xác nhận prompt/PIN.*

---

## 3. Thu thập Screenshot Evidence
Toàn bộ ảnh chụp debug trong quá trình tự động hóa được lưu tại:
- Thư mục: `D:/Taadaa/GPM auto/debug_screenshots/`
- Tiêu chí lọc: Các file ảnh có `mtime >= start_time`.
- Định dạng xuất báo cáo cho Coordinator / User:
  `MEDIA:<đường_dẫn_tuyệt_đối_của_ảnh>`

---

## 4. Post-Login State Reconciliation (Khi SUCCESS)
Khi kết quả trả về `SUCCESS`:

1. **Cập nhật Cron Nurture State**:
   - File: `D:/Taadaa/runtime/kibe/cron-state/gpm_gmail_nurture_state.json`
   - Cập nhật entry của `<email>`:
     ```json
     "status": "LOGIN_RECOVERED"
     ```

2. **Cập nhật Nhóm Profile trong GPMLogin DB**:
   - Database: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`
   - Thực thi SQL:
     ```sql
     UPDATE Profiles SET GroupId = 10 WHERE Name LIKE '%<email>%';
     ```
     *(GroupId 10 là nhóm tài khoản đã login thành công / sẵn sàng nuôi / khai thác)*.
