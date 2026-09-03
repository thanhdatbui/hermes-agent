# Cấu trúc workbook taikhoan_run_safe.xlsx

Workbook nằm ở: `D:\OneDrive\codex_gmail_debug\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx`

## Cột
- `May` (Máy): số máy 1-74
- `Device ID` (Serial): ADB serial của thiết bị
- `ID` (TikTok username): tài khoản TikTok

## Cấu trúc
Mỗi máy có 6 dòng (account slots 1-6). `--account-row-index N` chọn dòng thứ N của mỗi máy.

Ví dụ:
```
May | Device ID            | ID
1   | 9885b64957334f5a46   | lipsellczaw       ← row 1 (account-row-index 1)
1   | 9885b64957334f5a46   | duongkien1202     ← row 2
1   | 9885b64957334f5a46   | tranngan767       ← row 3
1   | 9885b64957334f5a46   | None              ← row 4
1   | 9885b64957334f5a46   | None              ← row 5
1   | 9885b64957334f5a46   | None              ← row 6
2   | 9885e6303951513337   | thanh.h.dng00     ← row 7 (account-row-index 1)
...
```

## Ghi chú
- Các dòng có ID=None nghĩa là slot trống, không có tài khoản
- `--account-row-index` nên dùng 1-3 cho các máy có tài khoản thực
