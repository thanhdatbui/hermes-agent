# GPM Fingerprint Uniqueness, Proxy Completion & Ordering (2026-09-03)

## 1. Backup trước mọi sửa DB
```python
import shutil, datetime
src = r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db'
dst = src.replace('profile_data.db', f'profile_data_backup_{datetime.date.today():%Y%m%d}.db')
shutil.copy2(src, dst)
```
Verify: `SELECT count(*) FROM Profiles` trước/sau phải bằng nhau (chuẩn farm: 256 rows).

## 2. Không bao giờ move thư mục profile
`Profiles.ProfilePath` map 1:1 tới thư mục `GPMLogin\profile\<ProfilePath>\`.
Move sang `_archive` để "nhẹ UI" làm hỏng link + user coi là xóa dữ liệu. Giảm tải UI bằng
`profile_page_session.dat` (`1,10,1` = trang 1, 10/trang, group All), tối đa 20/trang.

## 3. Proxy completion không clone fingerprint
Profile mini chỉ có `raw_proxy` khiến WPF treo khi pageSize > 10. Điền đủ 7 keys:
`raw_proxy`, `Proxy`, `proxy_type=http`, `proxy_host`, `proxy_port`, `proxy_user`, `proxy_pass`.
Mapping chuẩn: farm `01_Rua→16` = `test.taadaa.click:5101..5116:mobiX:TaadaaMobi#2026!`;
Admin `10008→10024` = `mirotik1.taadaa.click:10008..10024:admin@1:admin@1`;
`AMZ_Main` = proxy riêng `207.228.30.121:6174:...`.
Keys CẤM copy hàng loạt (phải unique mỗi profile): `AudioNoise`, `CanvasNoise*`,
`ClientRectNoise`, `WebGLRenderer`, `WebGLVendor`, `WebGL_UNMASKED_*`, `WebGLNoise*`,
`WebGPUVendorId/DeviceId`, `MacAddress`, `WebRTCPublicIP`.

## 4. Kiểm tra trùng fingerprint (phải rỗng)
```python
import sqlite3, json
conn = sqlite3.connect('.../profile/profile_data.db')
for r in conn.execute('SELECT Name, JsonData FROM Profiles WHERE GroupId=1'):
    jd = json.loads(r[1])
    print(r[0], jd.get('AudioNoise'), (jd.get('WebGLRenderer') or '')[:40])
```
2 profile trùng `AudioNoise` + `WebGLRenderer` = Google coi là 1 máy → văng acc.

## 5. Sắp xếp thứ tự hiển thị qua CreatedAt
```python
import datetime
base = datetime.datetime(2024, 1, 1, 10, 0, 0)
for idx, pid in enumerate(ordered_ids):  # 01_Rua→16, 10008→10024, AMZ_Main
    ts = (base + datetime.timedelta(minutes=idx*10)).strftime('%Y-%m-%d %H:%M:%S')
    cur.execute('UPDATE Profiles SET CreatedAt=? WHERE Id=?', (ts, pid))
```
Kill `GPMLogin.exe` → mở lại → bấm Reload (UI sort "Từ cũ đến mới").

## 6. Session file format
`profile_page_session.dat` = `pageIndex,pageSize,groupId` (vd `1,10,1`). Kẹt `2,500,1`
(trang không tồn tại + pageSize 500) gây xoay vô hạn → reset về `1,10,1`.
