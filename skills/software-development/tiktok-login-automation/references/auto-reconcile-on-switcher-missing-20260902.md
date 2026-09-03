# Tự Động Kích Hoạt Reconcile / Login Khi Switcher Thiếu Nick (2026-09-02)

## 1. Bản Chất & Phân Biệt 2 Trường Hợp

1. **Trường hợp Máy Thiếu Nick (< 6 nick trên máy hoặc thiếu nick chỉ định theo slot)**:
   - Script nuôi (`multi-machine-feed-session`) mở Account Switcher nhưng không tìm thấy tài khoản mong đợi (`account-switcher-missing-expected`).
   - **Hành vi bắt buộc**: Tự động kích hoạt luồng `reconcile_tiktok_accounts.py` (`tiktok-log-in`) để đăng nhập nick thiếu vào máy thật, sau đó retry bước chuyển đổi profile để tiếp tục ca nuôi.
   - **TUYỆT ĐỐI CẤM**: Tự ý đôn slot, đảo slot hoặc chuyển nick thiếu sang máy khác.

2. **Trường hợp Máy ĐÃ FULL ĐỦ 6 NICK nhưng dính nick thừa ở slot phụ (Slot 7/8)**:
   - Máy thực tế đã đăng nhập tối đa 6 nick, trong đó có nick hợp lệ từ đợt reg ở slot 7/8 và thiếu 1 nick ở slot chính 1..6.
   - Lúc này mới thực hiện swap/re-map trên Excel (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `TikN.xlsx`) để tránh logout/login churn trên thiết bị.

## 2. Lệnh Reconcile Chuẩn

```bash
cd /d/Taadaa/tiktok-log-in
env -u PYTHONPATH "D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe" scripts/reconcile_tiktok_accounts.py \
  --workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" \
  --machines <M> \
  --adb-path "C:\Program Files (x86)\xiaowei\tools\adb.exe" \
  --source-runner "D:\Taadaa\tiktok-luot nuoi acc" \
  --login-project "D:\Taadaa\Tiktok_Reg" \
  --login-workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx" \
  --proxy-mapping "D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx" \
  --allow-live-reconcile \
  --full-scope-takeover
```
