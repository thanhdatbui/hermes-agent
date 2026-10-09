# Pitfall: Safe Workbook Mapping Slot theo Folder Modulo 8 & OneDrive Cloud-Only (2026-09-22)

## 1. Triệu chứng sự cố
- Toàn bộ máy cụm Admin (M201-M280) bị bỏ qua (skip) 100% trong các ca cày feed ban đêm (Row 7 / Row 8):
  `tiktok_runner [admin]: Row 8 co 0 account hop le trong D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx, skipping window...`
- Mặc dù trong file DAT gốc (`taikhoan_dat_v2_updated .xlsx`) đã có đầy đủ 77/80 nick ở Row 8 và 56 nick ở Row 7.

---

## 2. Nguyên nhân gốc rễ (Root Cause)

### A. Bug append mù quáng trong `sync-safe-workbook.py`
- Hàm `_build_safe_workbook` đọc từng dòng từ DAT và gộp vào `machine_entries[machine].append((serial, account_id))`.
- Sau đó đắp thêm slot rỗng: `while len(entries) < 8: entries.append((primary_serial, ""))`.
- **Hậu quả:** Khi một máy bị khuyết các slot ở giữa (ví dụ chỉ có nick ở Folder 1, Folder 2 và Folder 8):
  - Nick Folder 8 bị nhồi vào **vị trí dòng thứ 3 (index 2 / Row 3)** của safe workbook.
  - Các slot cuối (Slot 6, 7, 8) bị chèn rỗng `""`.
  - Runner khi chạy Row 8 kiểm tra `slots[7]` thấy rỗng -> kết luận `0 valid accounts` -> skip toàn bộ cụm.

### B. OneDrive Cloud-Only Placeholder (Recall On Data Access)
- File `taikhoan_run_safe.xlsx` của Admin lưu trên OneDrive máy Kibe bị kẹt thuộc tính `Offline / Recall-on-data-access` (chưa tải nội dung thực tế về máy).
- Khi thư viện `openpyxl` cố mở file, Windows ném lỗi `OSError: [Errno 22] Invalid argument / BadZipFile: File is not a zip file`.
- Runner bắt ngoại lệ và fallback về `0 valid accounts`.

---

## 3. Quy tắc Fix & Chuẩn hóa

### A. Fix logic Slot Mapping (Modulo 8 Cố Định)
Bắt buộc đọc cột `Folder Video` và map chính xác từng account vào array 8 phần tử cố định (`machine_slots = [None] * 8`):
```python
slot = None
if raw_folder is not None:
    try:
        f_num = int(str(raw_folder).strip())
        if f_num > 0:
            slot = (f_num - 1) % 8  # index 0..7 tương ứng Row 1..8
    except (TypeError, ValueError):
        pass

if slot is not None and machine_slots[target_slot] is None:
    machine_slots[target_slot] = (serial, account_id)
else:
    # Collision fallback: tìm slot trống đầu tiên
    slot_idx = next((i for i in range(8) if machine_slots[i] is None), None)
    if slot_idx is not None:
        machine_slots[slot_idx] = (serial, account_id)
```

### B. Fix OneDrive Placeholder trên Kibe
- Để tránh bị kẹt `Errno 22` khi OneDrive chưa sync file từ Admin về Kibe, ưu tiên copy trực tiếp qua SCP LAN nội bộ:
  ```bash
  scp admin-farm:"D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx" "D:/Taadaa/runtime/admin/taikhoan_run_safe.xlsx"
  ```
- Hoặc dùng PowerShell xóa placeholder và ghi đè bằng file local đã hydrate:
  ```powershell
  Remove-Item "D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx" -Force
  Copy-Item "D:\Taadaa\runtime\admin\taikhoan_run_safe.xlsx" "D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx" -Force
  ```

### C. Telemetry bắt buộc sau khi sync Safe Workbook
Sau khi hoàn tất xuất file, script phải log telemetry rõ ràng ra stderr để phục vụ audit/debug:
```python
slot_counts = [0] * 8
for i, (m, s, a, v) in enumerate(rows):
    if a:
        slot_counts[i % 8] += 1
sys.stderr.write(f"[TELEMETRY:SAFE_WORKBOOK] machines={len(machine_slots)} total_accounts={sum(slot_counts)} slots={dict(enumerate(slot_counts, 1))}\n")
```
