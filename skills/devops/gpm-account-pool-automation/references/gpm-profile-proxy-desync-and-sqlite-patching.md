# Bẫy Lệch Proxy Trong Profile GPM Khi Đổi Tên / Chuẩn Hóa Profile (2026-10-05)

## 1. Hiện Tượng & Nguyên Nhân Gốc (Root Cause)
- **Hiện tượng:** Profile trên giao diện GPMLogin hiển thị tên theo chuẩn máy S7 (ví dụ `M13 - 5115 - brittanysbarneskn2xa@gmail.com`), nhưng khi mở profile, proxy thực tế chạy bên dưới lại là proxy khác (ví dụ `mirotik1.taadaa.click:10021` của Admin Pool).
- **Nguyên nhân kỹ thuật:**
  1. Trong cơ sở dữ liệu GPMLogin (`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`), bảng `Profiles` lưu tên hiển thị tại cột `Name`, nhưng toàn bộ cấu hình kết nối trình duyệt (bao gồm `Proxy`, `UserAgent`, `JsonData.Name`) lại nằm trong chuỗi JSON ở cột `JsonData`.
  2. Bảng `Profiles` **KHÔNG có cột `RawProxy`** riêng biệt.
  3. Khi agent chuẩn hóa tên profile theo quy chuẩn `M<máy> - <port> - <email>`, nếu chỉ chạy lệnh SQL cập nhật tên:
     ```sql
     UPDATE Profiles SET Name = ? WHERE Id = ?
     ```
     thì chỉ có **vỏ ngoài** (tên hiển thị) thay đổi. **Ruột bên trong** (`JsonData['Proxy']`) vẫn giữ nguyên proxy cũ (từ thời profile được tạo ban đầu, ví dụ từ đợt chạy Admin Pool `10021` hoặc gán nhầm port).
  4. Hậu quả: Khi automation hoặc user mở profile, Chrome kết nối theo `JsonData['Proxy']` thay vì port ghi trên tên profile, làm sai lệch luồng định tuyến proxy của dàn máy S7.

---

## 2. Quy Tắc Bắt Buộc Khi Sửa Tên Hoặc Remap Profile GPM
1. **CẤM TUYỆT ĐỐI chỉ đổi cột `Name`**: Khi cập nhật profile theo máy hoặc port mới, BẮT BUỘC phải đồng bộ cả trường `Proxy` và `Name` bên trong `JsonData` hoặc qua GPM API v3.
2. **Cách 1: Cập nhật qua GPM Local API v3 (Port 19995 - KHUYÊN DÙNG khi GPMLogin đang mở)**:
   API `POST /api/v3/profiles/update/{profile_id}` cập nhật trực tiếp cả cấu hình in-memory và SQLite:
   ```python
   import requests

   pid = "<profile_uuid>"
   payload = {
       "name": f"M{mid:02d} - {expected_port} - {email}",
       "raw_proxy": f"test.taadaa.click:{expected_port}:mobi{port_idx}:TaadaaMobi#2026!"
   }
   res = requests.post(f"http://127.0.0.1:19995/api/v3/profiles/update/{pid}", json=payload, timeout=10)
   # res.json() -> {"success": true, "data": {}, "message": "OK"}
   ```
   *Lưu ý:* Sau khi gọi API, trên giao diện WPF của GPMLogin chỉ cần nhấn Refresh (`⟳`) hoặc Enter lại ô tìm kiếm để bảng dữ liệu UI nạp lại proxy mới.

3. **Cách 2: Cập nhật chuẩn O(1) trực tiếp qua SQLite**:
   ```python
   import sqlite3, json, shutil

   db_path = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db"
   shutil.copyfile(db_path, db_path + ".bak")

   conn = sqlite3.connect(db_path)
   c = conn.cursor()

   c.execute("SELECT Id, Name, JsonData FROM Profiles WHERE Id = ?", (profile_id,))
   row = c.fetchone()
   if row:
       pid, current_name, js_str = row
       data = json.loads(js_str)
       
       # Cập nhật cả Name hiển thị và trường bên trong JsonData
       new_name = f"M{mid:02d} - {expected_port} - {email}"
       new_proxy = f"test.taadaa.click:{expected_port}:mobi{port_idx}:TaadaaMobi#2026!" # hoặc proxy quy hoạch tương ứng
       
       data["Name"] = new_name
       data["Proxy"] = new_proxy
       
       c.execute(
           "UPDATE Profiles SET Name = ?, JsonData = ?, UpdatedAt = datetime('now', 'localtime') WHERE Id = ?",
           (new_name, json.dumps(data, ensure_ascii=False), pid)
       )
       conn.commit()
   conn.close()
   ```

4. **Lệnh Audit Đối Soát Tên vs Proxy Live**:
   Trước khi chạy bất kỳ pipeline GPM/OAuth nào, luôn chạy audit nhanh kiểm tra độ khớp giữa port trong `Name` và port trong `JsonData.Proxy`:
   - Nếu `Name` có dạng `M<mid> - <port>` mà port trong `JsonData.Proxy` khác `<port>`: Phải alert và cập nhật `JsonData.Proxy` ngay lập tức, không để profile chạy lệch proxy.

---

## 5. Quy Trình Đối Soát Mắt Xích OmniRoute (`storage.sqlite`)
Khi kiểm tra tài khoản đã gán đúng proxy trên OmniRoute (port 20129) hay chưa, đối soát 3 bảng trong `C:\Users\Kibe\.omniroute\storage.sqlite`:
1. **Lấy Connection ID**:
   ```sql
   SELECT id, name, email, is_active FROM provider_connections WHERE lower(email) = '<target_email>';
   ```
2. **Kiểm tra Proxy được gán (`proxy_assignments` ↔ `proxy_registry`)**:
   ```sql
   SELECT pa.id, pa.scope_id, pr.name, pr.host, pr.port, pr.username
   FROM proxy_assignments pa
   JOIN proxy_registry pr ON pa.proxy_id = pr.id
   WHERE pa.scope_id = '<connection_id>';
   ```
   *Kết quả hợp lệ:* `pr.port` phải khớp chính xác với cổng quy hoạch của máy S7 (ví dụ Máy 13 $\rightarrow$ port `5115`, user `mobi15`).
3. **Kiểm chứng Egress IP thực tế từ Request Logs (`proxy_logs`)**:
   ```sql
   SELECT id, timestamp, status, proxy_host, proxy_port, egress_ip
   FROM proxy_logs
   WHERE connection_id = '<connection_id>'
   ORDER BY timestamp DESC LIMIT 5;
   ```
   Nếu `proxy_port` và `egress_ip` khớp đúng line mạng Viettel/PPPoE của máy đó, khẳng định 100% OmniRoute đã định tuyến qua đúng proxy. Cả 3 mắt xích **GPM Profile ↔ S7 Singbox ↔ OmniRoute** phải đồng nhất trên cùng một cổng upstream.
