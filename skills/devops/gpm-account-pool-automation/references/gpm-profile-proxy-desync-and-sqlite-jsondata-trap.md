# Bẫy Lệch Proxy Trong GPMLogin: Tên Profile Đổi Nhưng JsonData.Proxy Không Đổi (2026-10-05)

## 1. Hiện tượng & Bản chất sự cố
- **Hiện tượng**: Trên bảng điều khiển GPMLogin, tên profile hiển thị theo chuẩn máy/port farm: `M13 - 5115 - <email>`, nhưng cột Proxy hoặc khi chạy Chrome thực tế lại kết nối qua đường khác (ví dụ `mirotik1.taadaa.click:10021:admin@1:admin@1`).
- **Nguyên nhân kỹ thuật (Root Cause)**:
  - Trong cơ sở dữ liệu GPMLogin SQLite (`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`), bảng `Profiles` có hai vị trí lưu thông tin:
    1. Cột `Name`: Chỉ là nhãn hiển thị bên ngoài bảng giao diện.
    2. Cột `JsonData`: Là chuỗi JSON cấu hình phần cứng và mạng thực tế mà trình duyệt Chrome nạp khi khởi chạy (`"Proxy": "...", "Name": "..."`).
  - Khi script hoặc kỹ thuật viên chạy lệnh cập nhật tên profile:
    `UPDATE Profiles SET Name = ? WHERE Id = ?`
    chỉ có nhãn hiển thị ngoài bảng thay đổi. Cấu hình proxy thực thi nằm trong `JsonData['Proxy']` vẫn giữ nguyên giá trị cũ.
  - Hậu quả: Profile mang tên Máy 13 / port 5115 nhưng thực tế chạy qua proxy của máy khác (ví dụ cổng MikroTik PPPoE 10021), gây ô nhiễm dải IP và lệch hoàn toàn với quy hoạch farm (`PROXYgandienthoai.xlsx` và `singbox_config.json`).

## 2. Quy trình kiểm tra O(1) & Phát hiện lệch
Truy vấn SQLite để so sánh giữa tên hiển thị và cấu hình proxy thực:
```python
import sqlite3, json

db_path = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT Id, Name, JsonData FROM Profiles WHERE lower(Name) LIKE '%brittany%'")
for pid, name, json_str in cur.fetchall():
    data = json.loads(json_str)
    print(f"ID: {pid}")
    print(f"  UI Name  : {name}")
    print(f"  JSON Name: {data.get('Name')}")
    print(f"  Proxy    : {data.get('Proxy')}")
conn.close()
```

## 3. Quy chuẩn đồng bộ & Fix an toàn
Khi remap hoặc đổi tên profile GPM theo máy và port, **BẮT BUỘC** cập nhật đồng bộ cả `Name` và `JsonData`:
```python
import sqlite3, json, shutil

db_path = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db"
shutil.copyfile(db_path, db_path + ".bak")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Lấy profile cần sửa
cur.execute("SELECT Id, JsonData FROM Profiles WHERE Id = ?", (prof_id,))
row = cur.fetchone()
if row:
    pid, json_str = row
    data = json.loads(json_str)
    
    new_name = "M13 - 5115 - brittanysbarneskn2xa@gmail.com"
    new_proxy = "test.taadaa.click:5115:mobi15:TaadaaMobi#2026!"
    
    data["Name"] = new_name
    data["Proxy"] = new_proxy
    
    cur.execute(
        "UPDATE Profiles SET Name = ?, JsonData = ?, UpdatedAt = datetime('now', 'localtime') WHERE Id = ?",
        (new_name, json.dumps(data, ensure_ascii=False), pid)
    )
    conn.commit()

conn.close()
```
