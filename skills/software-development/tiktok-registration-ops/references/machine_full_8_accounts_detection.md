# Phát hiện trần 8 tài khoản TikTok (MACHINE_FULL_8_ACCOUNTS)

## Bối cảnh & Triệu chứng
- Khi TikTok trên Android đạt trần 8 tài khoản được lưu trong app client, mở account dropdown bottom sheet (bước `tap_add_account`) sẽ **không còn nút "Thêm tài khoản"** (`Add account` / `Thêm tài khoản khác`).
- Nếu script tiếp tục tìm text/id nút "Thêm tài khoản", sau 3 attempts sẽ fail với timeout generic hoặc chụp XML báo lỗi tìm nút mà không biết nguyên nhân thật sự là thiết bị đã đầy slot tài khoản.

## Cơ chế nhận diện qua XML & Resource-IDs
- Trong bottom sheet danh sách tài khoản, mỗi tài khoản hiện tại được render thành 1 item node.
- TikTok liên tục thay đổi tên obfuscated `resource-id` qua các phiên bản cập nhật. Các prefix/suffix id được xác nhận cho account item node gồm:
  - `n72` (bản cũ)
  - `lkp` (bản cũ)
  - `l9b` (bản mới)
  - `lpw` (bản mới)
  - `l_z` (bản mới)
  - `lrq` (bản mới)
  - `lli` (bản mới)

### Logic kiểm tra chuẩn trong `social_reg_v1.py`
```python
import xml.etree.ElementTree as _ET
_xml = get_ui_xml(device_id)
_root = _ET.fromstring(_xml)
_acc_count = sum(
    1 for _n in _root.iter("node")
    if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"])
)
if _acc_count >= 8:
    log(f"   [04_add_account] Máy đã có {_acc_count} tài khoản — đạt giới hạn tối đa 8")
    keyevent(device_id, 4, wait=D_SHORT)  # dismiss dropdown
    keyevent(device_id, 3, wait=0.5)      # go home
    raise RuntimeError("[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok")
```

## Xử lý khi gặp lỗi
1. Script đóng dropdown bằng `keyevent 4` (Back) và về home bằng `keyevent 3` (Home) để không treo UI máy ở sheet tài khoản.
2. Raise lỗi định danh rõ `MACHINE_FULL_8_ACCOUNTS` để runner/coordinator biết máy này đã bão hòa tài khoản, chuyển máy hoặc thực hiện dọn dẹp/xoá bớt account cũ thay vì retry vô ích.
3. Test suite kiểm chứng logic: `D:\Taadaa\Tiktok_Reg\tests\test_machine_full_8_acc.py`.
