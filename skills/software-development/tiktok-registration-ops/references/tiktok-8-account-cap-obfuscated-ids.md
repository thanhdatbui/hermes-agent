# TikTok 8-Account Cap & Obfuscated Resource-IDs (fail_04_add_account)

## Hiện tượng (Symptom)
Khi chạy batch reg TikTok hoặc thêm account, worker báo lỗi:
```
RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account', 'Thêm tài khoản khác', 'Add another account', 'add_account')
```
Thực tế trên thiết bị:
- Máy **đã đăng nhập đủ 8 tài khoản TikTok**.
- TikTok ẩn hoàn toàn nút "Thêm tài khoản" khi đạt trần 8 tài khoản.
- Code kiểm tra `_acc_count` trong bottom sheet dropdown nhưng chỉ đếm các resource-id cũ (`n72`, `lkp`), dẫn tới `_acc_count = 0` và trôi xuống ném lỗi không tìm thấy thay vì nhận diện máy đã full 8.

## Obfuscated Resource-IDs trên TikTok versions mới
Trong layout sheet chuyển đổi tài khoản (`Chuyển đổi tài khoản` / Bottom Sheet), các nút item tài khoản (`android.widget.Button`) có bounds `[0, y1][1080, y2]` mang các resource-id bị obfuscate sau:
- `n72` (cũ)
- `lkp` (cũ)
- `l9b` (v4x)
- `lpw` (v4x)
- `l_z` (v4x)
- `lrq` (v4x)
- `lli` (v4x)

## Pattern nhận diện chuẩn
Khi đếm số lượng tài khoản trong dropdown sheet:
```python
_acc_count = sum(
    1 for _n in _root.iter("node")
    if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"])
)
if _acc_count >= 8:
    log(f"   [04_add_account] Máy đã có {_acc_count} tài khoản — đạt giới hạn tối đa 8")
    keyevent(device_id, 4, wait=D_SHORT)
    keyevent(device_id, 3, wait=0.5)
    raise RuntimeError("[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok")
```

## Checklist chẩn đoán nhanh khi gặp `[04_add_account]`
1. Inspect UI XML dump tại thời điểm lỗi (`fail_04_add_account_*.xml`).
2. Kiểm tra text trong dump có tiêu đề `Chuyển đổi tài khoản` không.
3. Đếm số nút `android.widget.Button` có tọa độ full chiều rộng `[0, y][1080, y]`.
4. Nếu số item = 8, kiểm tra ngay resource-id của các item đó. Nếu xuất hiện mã obfuscate mới chưa có trong danh sách trên, bổ sung vào whitelist đếm tài khoản.
