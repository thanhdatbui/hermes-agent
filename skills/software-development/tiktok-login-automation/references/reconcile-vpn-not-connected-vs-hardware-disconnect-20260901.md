# Phân biệt Lỗi VICHANGER_VPN_NOT_CONNECTED do Mất Kết Nối ADB / Phần Cứng (2026-09-01)

## Bối cảnh & Hiện tượng
Khi chạy canonical reconcile script:
```bash
cd /d/Taadaa/tiktok-log-in
"D:/Taadaa/python-envs/automation/Scripts/python.exe" scripts/reconcile_tiktok_accounts.py \
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

Runner trả về `FINAL_BLOCKED` với lý do:
`AccountInventoryError: machine N: VICHANGER_VPN_NOT_CONNECTED` hoặc `DeviceLockReadinessError: LIVE_VPN_NOT_READY: serial=... reason=verifier returned false`.

## Nguyên nhân gốc (Root Cause)
1. Trong `account_reconcile.py`, hàm `_live_vpn_verifier` gọi `_require_vpn(adb_path, target, proxy_mapping)`.
2. Khi thiết bị bị mất kết nối ADB (tuột cáp, lỏng hub USB, sập nguồn), lệnh ADB kiểm tra `tun0` / `dumpsys connectivity` trả về `adb.exe: device '<serial>' not found`.
3. Bất kỳ ngoại lệ nào trong `_require_vpn` đều bị `_live_vpn_verifier` catch và trả về `False` $\rightarrow$ `acquire_device_lock` nâng lỗi thành `LIVE_VPN_NOT_READY` / `VICHANGER_VPN_NOT_CONNECTED`.
4. Đây là lỗi **phần cứng/mất kết nối ADB (DEVICE_NOT_FOUND)**, không phải do cấu hình ViChanger hay Proxy bị lỗi.

## Quy trình chẩn đoán chuẩn
Trước khi can thiệp vào ViChanger/Proxy:
1. Chạy `"C:\Program Files (x86)\xiaowei\tools\adb.exe" devices | grep "<serial>"`.
2. Nếu không thấy serial trong danh sách: Báo ngay `DEVICE_NOT_FOUND` và thông báo máy mất kết nối phần cứng.
3. Chỉ thực hiện chẩn đoán VPN khi thiết bị đã online ở trạng thái `device`.
