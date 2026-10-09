# GPM Login v4.3.x: WPF DataGrid Pagination Lag & Schema Uniformity

## Triệu chứng & Bối cảnh
- Trên giao diện GPM Login v4.3.x (WPF / .NET Windows), khi cài đặt số profile hiển thị trên mỗi trang (`Số profile trên mỗi trang`):
  - Để `10` hoặc `50` kết quả: Load bình thường, mượt mà.
  - Chuyển sang `100` hoặc `200` kết quả (hoặc chuyển sang trang 2 ở mức 50): Giao diện xuất hiện vòng xoay xanh (loading spinner) vô tận, bảng bị đơ cứng, không thao tác được.

## Nguyên nhân gốc rễ (Root Cause)
GPM Login UI sử dụng WPF `DataGrid` binding trực tiếp dữ liệu từ bảng `Profiles` trong `profile_data.db`:
1. **Binding Expression Exceptions trong WPF Dispatcher Thread:**
   - Các profile tạo chuẩn từ trước có đầy đủ **124 keys** (hoặc 130 keys) trong trường `JsonData` (bao gồm `UserAgent`, `AudioNoise`, `CanvasNoiseToken`, `WebGLRenderer`, `MacAddress`, `ScreenWidth`...).
   - Khi tạo profile thủ công hoặc tạo tắt bằng code trực tiếp vào SQLite mà chỉ điền JSON tối giản 2 keys (`{"Name": "...", "Proxy": "..."}`), WPF DataGrid khi cuộn tới các hàng này sẽ cố gắng bind các cột hiển thị (`BrowserCore`, `OS`, `Fingerprint icons`, `Proxy status`...).
   - Thiếu các thuộc tính binding gây ra hàng loạt ngoại lệ `BindingExpression / MissingMemberException` ngầm trên luồng UI của WPF, làm tê liệt UI Dispatcher và khiến loading spinner xoay mãi mãi.
2. **Tại sao 50 kết quả lại không lag còn 100 kết quả bị lag?**
   - Ví dụ Group có 82 profiles: 50 profile đầu tiên (từ `#1` đến `#50`) đều là profile cũ có đầy đủ 124 keys $\rightarrow$ Page size = 50 chỉ render 50 profile đầu nên trơn tru.
   - Khi chọn Page size = 100, WPF buộc phải render toàn bộ 82 profiles (bao gồm các profiles mới ở cuối `#79..#82` chỉ có 2 keys) $\rightarrow$ Ngay lập tức kích hoạt lỗi binding trên luồng UI.

## Quy tắc bắt buộc khi tạo Profile GPM bằng SQLite trực tiếp
Tuyệt đối **CẤM** chỉ insert JSON tối giản 2-3 keys vào cột `JsonData`. Khi tạo profile mới trực tiếp qua SQLite mà không qua GPM App/API v3:
1. **Donor Template 124 keys:**
   - Lấy `JsonData` từ một profile mẫu hợp lệ (124 keys) làm template.
2. **Randomize Fingerprint độc lập:**
   - Cập nhật `Name` theo chuẩn `M<máy> - <port> - <email>`.
   - Cập nhật `Proxy` tương ứng theo máy/port.
   - BẮT BUỘC sinh mới ngẫu nhiên `MacAddress` (`'-'.join([f'{random.randint(0, 255):02X}' for _ in range(6)])`).
   - BẮT BUỘC sinh mới ngẫu nhiên `AudioNoise` (`round(random.uniform(-5.0, 5.0), 15)`).
   - Kiểm tra đảm bảo không trùng `MacAddress` và `AudioNoise` với bất kỳ profile nào khác trong database để tránh bị Google/OpenAI nhận diện cùng thiết bị ảo (Virtual Machine clone).

## Script Python chuẩn hóa & Fix nhanh (Hotfix Script)
```python
import sqlite3, json, random, copy

conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db')
c = conn.cursor()

# 1. Lấy donor JSON mẫu 124 keys
c.execute("SELECT JsonData FROM Profiles WHERE length(JsonData) > 3000 AND GroupId = 1 LIMIT 1")
donor_json = json.loads(c.fetchone()[0])

# 2. Thu thập MAC & AudioNoise hiện có để chống trùng lặp
c.execute("SELECT JsonData FROM Profiles WHERE JsonData IS NOT NULL")
all_macs = set()
all_audio = set()
for r in c.fetchall():
    try:
        d = json.loads(r[0])
        if 'MacAddress' in d: all_macs.add(d['MacAddress'])
        if 'AudioNoise' in d: all_audio.add(str(d['AudioNoise']))
    except: pass

def get_unique_mac():
    while True:
        mac = '-'.join([f'{random.randint(0, 255):02X}' for _ in range(6)])
        if mac not in all_macs:
            all_macs.add(mac)
            return mac

def get_unique_audio():
    while True:
        an = round(random.uniform(-5.0, 5.0), 15)
        if str(an) not in all_audio:
            all_audio.add(str(an))
            return an

# 3. Quét các profile thiếu keys trong Group 1 và đồng bộ
c.execute("SELECT Id, Name, JsonData FROM Profiles WHERE GroupId = 1")
for pid, name, jstr in c.fetchall():
    d = json.loads(jstr) if jstr else {}
    if len(d.keys()) < 100:
        proxy_val = d.get('Proxy', '')
        new_d = copy.deepcopy(donor_json)
        new_d['Name'] = name
        if proxy_val:
            new_d['Proxy'] = proxy_val
        new_d['MacAddress'] = get_unique_mac()
        new_d['AudioNoise'] = get_unique_audio()
        c.execute("UPDATE Profiles SET JsonData = ? WHERE Id = ?", (json.dumps(new_d, ensure_ascii=False), pid))
        print(f"Đã chuẩn hóa 124 keys cho: {name}")

conn.commit()
conn.close()
```
