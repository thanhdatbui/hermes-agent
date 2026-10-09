# Canonical Parasite Account Reconcile & Logout Workflow

## 1. Mục đích
Xử lý dứt điểm tình trạng nick ký sinh (1 nick đăng nhập nhầm trên 2 máy cùng lúc, hoặc máy chạm trần 8 nick do nick rác) trên thiết bị Taadaa farm.

## 2. Các file & vị trí chuẩn
- **Script điều phối / thực thi logout:**
  `D:/Taadaa/tools/watchdog_idle_parasite_reconcile.py`
  (Bản cron copy tại `C:/Users/Kibe/AppData/Local/hermes/scripts/watchdog_idle_parasite_reconcile.py`)
- **State tracking file:**
  `D:/Taadaa/runtime/kibe/cron-state/parasite_reconcile_state.json`
- **Unit test suite:**
  `D:/Taadaa/tools/tests/test_watchdog_targets.py`
- **Output ảnh nghiệm thu:**
  `D:/Taadaa/reports/m{machine_id}_switcher_verified_logout.png`

## 3. Quy trình chuẩn khi logout nick ký sinh trên 1 máy cụ thể (Manual / One-shot)

### Bước 1: Reset state cho máy mục tiêu
Nếu máy đó từng được đánh dấu `"DONE"` trong `parasite_reconcile_state.json`, cần xóa key tương ứng (ví dụ `"m61_anggiathinh2905"`) trước khi chạy, nếu không script watchdog sẽ bỏ qua.

### Bước 2: Acquire Device Lock
Luôn kiểm tra và acquire lock theo quy tắc **Rule #1: No Touch Without Lock**:
```bash
python -c "import sys; sys.path.insert(0, 'D:/Taadaa/Tiktok_Reg'); from device_lock import acquire_device_lock; l = acquire_device_lock(machine=<M_ID>, serial='<SERIAL>', project='parasite_reconcile', command=['logout', '<USERNAME>'], user_authorized=True); print('Locked:', l)"
```

### Bước 3: Chạy script logout
Chạy trực tiếp hàm hoặc script:
```bash
python D:/Taadaa/tools/watchdog_idle_parasite_reconcile.py
```
Hoặc gọi trực tiếp hàm `do_logout(machine_id, username, serial)` từ `watchdog_idle_parasite_reconcile.py` trong Python oneliner để không phải lặp qua toàn bộ list `TARGETS`:
```python
python -c "import sys; sys.path.insert(0, 'D:/Taadaa/tools'); from watchdog_idle_parasite_reconcile import do_logout; ok = do_logout(61, 'anggiathinh2905', 'ce0916096182161a01'); print('Logout result:', ok)"
```

### Bước 4: Nghiệm thu OCR Switcher trước Teardown (Rule tối cao)
Ảnh switcher sau logout được lưu tại:
`D:/Taadaa/reports/m{machine_id}_switcher_verified_logout.png`

Xác minh qua WinRT OCR:
```bash
python C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py "D:/Taadaa/reports/m{machine_id}_switcher_verified_logout.png"
```
Đảm bảo:
1. Username nick ký sinh không còn trong danh sách tài khoản.
2. Nút "Thêm tài khoản" (Add account) xuất hiện nếu máy còn < 8 tài khoản.

### Bước 5: Release Device Lock & Báo cáo
```bash
python -c "import sys; sys.path.insert(0, 'D:/Taadaa/Tiktok_Reg'); from device_lock import release_device_lock; release_device_lock(machine=<M_ID>, serial='<SERIAL>'); print('Released lock')"
```
Báo cáo kết quả và đính kèm `MEDIA:D:/Taadaa/reports/m{machine_id}_switcher_verified_logout.png` ở dòng riêng biệt.
