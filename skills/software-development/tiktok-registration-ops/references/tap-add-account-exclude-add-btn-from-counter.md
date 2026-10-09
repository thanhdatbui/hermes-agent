# Fix False-Alarm MACHINE_FULL_8_ACCOUNTS Do Đếm Nhầm Nút "Thêm tài khoản" (2026-09-24)

## 1. Hiện tượng & Triệu chứng
Trong đợt chạy Preflight Reg Bù cho Row 8, runner báo lỗi:
`RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`
trên các thiết bị thực tế mới chỉ có đúng 7 tài khoản (ví dụ Máy 3).

## 2. Nguyên nhân kỹ thuật
Trong hàm `tap_add_account` (`social_reg_v1.py`), sau khi mở dropdown tài khoản, script kiểm tra số tài khoản hiện có bằng cách đếm các node XML có `resource-id` thuộc danh sách:
`["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"]`

Tuy nhiên, trên TikTok Android (Samsung S7 / TikTok v46.x):
- Nút "Thêm tài khoản" (Add account) ở đáy Switcher cũng là một dòng trong RecyclerView/ListView và mang **cùng resource-id** (ví dụ `lli` hoặc `lrq`) với các dòng tài khoản người dùng!
- Khi thiết bị có 7 tài khoản chuẩn + 1 nút "Thêm tài khoản" = tổng cộng 8 nodes XML khớp danh sách resource-id.
- Phép so sánh `if _acc_count >= 8` lập tức kích hoạt, tự động đóng dropdown và quăng ngoại lệ `MACHINE_FULL_8_ACCOUNTS` dù nút Thêm tài khoản đang hiển thị rõ ràng trên màn hình.

## 3. Bản vá chuẩn (Code Surgery)
Loại trừ các node mang nhãn "Thêm tài khoản", "Add account", "Add another":
```python
_acc_count = sum(
    1 for _n in _root.iter("node")
    if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"])
    and not any(x in (_n.attrib.get("text", "") + _n.attrib.get("content-desc", "")).lower() for x in ["thêm tài khoản", "add account", "add another"])
)
```

## 4. Kiểm thử hồi quy (Focused Unit Tests)
File test `tests/test_acc_count_exclude_add_btn.py` trong repo `Tiktok_Reg` kiểm chứng:
1. `test_exclude_add_account_button_when_7_accs_and_add_btn`: 7 account nodes + 1 node "Thêm tài khoản" mang cùng id `lli` -> đếm ra đúng 7.
2. `test_count_8_real_accounts_without_add_btn`: 8 account nodes thật (không có nút Thêm tài khoản) -> đếm đủ 8.
3. `test_tap_add_account_does_not_false_alarm_on_7_accs_plus_add_btn`: Gọi `tap_add_account` trên XML 7 acc + 1 nút thêm -> không bị quăng ngoại lệ.
4. `test_tap_add_account_raises_when_8_real_accounts`: Gọi `tap_add_account` trên XML 8 acc thật -> quăng đúng `MACHINE_FULL_8_ACCOUNTS`.
Lệnh chạy: `pytest D:/Taadaa/Tiktok_Reg/tests/test_acc_count_exclude_add_btn.py -q` -> 4 passed.
