# Cạm bẫy đếm tài khoản (MACHINE_FULL_8_ACCOUNTS) & loại trừ nút "Thêm tài khoản" (2026-09-24)

## Bối cảnh & Hiện tượng
Trong flow đăng ký TikTok (`Tiktok_Reg/social_reg_v1.py` -> `tap_add_account`), script mở dropdown danh sách tài khoản từ Profile và đếm số lượng tài khoản hiện có để kiểm tra giới hạn 8 tài khoản (`MACHINE_FULL_8_ACCOUNTS`).

Bộ đếm sử dụng tập resource-id bị làm mờ (obfuscated) của TikTok:
`["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"]`.

## Nguyên nhân gốc (Root Cause)
Trên các phiên bản TikTok gần đây, nút hành động **"Thêm tài khoản"** / **"Add account"** / **"Add another account"** ở đáy popup switcher dùng chung resource-id (ví dụ `com.ss.android.ugc.trill:id/lli`) với các dòng tài khoản đang đăng nhập.

Hậu quả:
- Khi máy có **7 tài khoản**, XML dump chứa 7 node tài khoản + 1 node nút "Thêm tài khoản" cùng mang resource-id `lli`.
- Bộ đếm đếm tổng cộng 8 node -> `_acc_count >= 8` -> báo giả (false-positive) `MACHINE_FULL_8_ACCOUNTS`.
- Quá trình đăng ký bị chặn đứng dù thiết bị vẫn còn trống 1 slot hợp lệ.

## Giải pháp chuẩn hóa (Canonical Pattern)
Luôn lọc bỏ các node có `text` hoặc `content-desc` chứa các từ khóa hành động thêm tài khoản:
```python
_acc_count = sum(
    1 for _n in _root.iter("node")
    if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"])
    and not any(x in (_n.attrib.get("text", "") + _n.attrib.get("content-desc", "")).lower() for x in ["thêm tài khoản", "add account", "add another"])
)
```

## Unit Test xác thực
- Test suite: `D:/Taadaa/Tiktok_Reg/tests/test_acc_count_exclude_add_btn.py`
- Kiểm thử các cases:
  1. 7 tài khoản + 1 nút "Thêm tài khoản" cùng ID -> đếm ra 7, không văng lỗi 8 accounts.
  2. 8 tài khoản thực sự (không có nút add) -> đếm ra 8, kích hoạt `MACHINE_FULL_8_ACCOUNTS`.
  3. Function `tap_add_account` trên giả lập XML tiếp tục tìm kiếm nút bấm khi count < 8.
