# Remote Admin Cluster (M201-M280) Support for Pin Top Videos & Automation Tools

## 1. Bản chất sự cố phát hiện trong session
- Script `pin_top_videos.py` ban đầu chỉ thiết kế cho cụm local Kibe (`localhost:5037`).
- Khi chạy cho các máy thuộc cụm Admin (`machine >= 200` hoặc `cluster == "admin"`), script bị timeout/kẹt vì:
  1. `execute_adb_cmd` thiếu flag kết nối remote daemon: `-H 192.168.110.119 -P 5037`.
  2. Khởi tạo `AdbClient` không truyền `host="192.168.110.119"` và `port=5037`, dẫn đến client mặc định kết nối ADB daemon local và báo lỗi `device not found`.
  3. `ProfileAdapter` trong script tạo lại `AdbClient` mới nhưng không kế thừa thông tin host/port của cụm Admin.

## 2. Giải pháp chuẩn hóa đa cụm (Dual Cluster Pattern)
1. **Kiểm tra Cluster O(1) qua Farm DB:**
   ```python
   from farm_db import get_machine_by_serial
   m_info = get_machine_by_serial(serial)
   is_admin = m_info.get("cluster") == "admin" or (machine is not None and machine >= 200)
   ```
2. **Định tuyến ADB Command:**
   ```python
   ADMIN_REMOTE_HOST = "192.168.110.119"
   ADMIN_REMOTE_PORT = 5037

   if is_admin:
       cmd = [ADB_BIN, "-H", ADMIN_REMOTE_HOST, "-P", str(ADMIN_REMOTE_PORT), "-s", serial] + args
   else:
       cmd = [ADB_BIN, "-s", serial] + args
   ```
3. **Định tuyến AdbClient cho ATX Session:**
   ```python
   if is_admin:
       dev = AdbClient(serial=serial, adb_path=ADB_BIN, host=ADMIN_REMOTE_HOST, port=ADMIN_REMOTE_PORT)
   else:
       dev = AdbClient(serial=serial, adb_path=ADB_BIN)
   ```

## 3. Bài học về phản hồi User
- Khi User chất vấn về việc chuẩn hoá kênh nhưng chưa ghim clip view cao, không được suy diễn phân trần dài dòng về mốc thời gian quá khứ ("clip này mới cắn đề xuất"). 
- Bắt buộc vào thẳng hành động: xác nhận hiện trạng thực tế trên thiết bị và tiến hành ghim ngay clip top view theo chỉ đạo.
