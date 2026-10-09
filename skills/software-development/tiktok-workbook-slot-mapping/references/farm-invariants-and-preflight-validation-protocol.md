# TikTok Workbook Slot Mapping & Farm Invariant Rules (17/09/2026)

## 1. 5 System Invariants (Bất biến hệ thống)
Mọi script tự động hóa (reg, bù slot, nuôi lướt feed, upload, render, download) bắt buộc phải tuân thủ:
1. **Trần cứng 8 acc/máy**: `COUNT(slots) <= 8` trên mọi máy. Cấm nhồi thêm nick khi máy thật đang có $\ge 8$ nick trên Switcher (tránh đẩy văng nick cũ vào cache Fast Login).
2. **Độc bản Slot tài khoản**: `UNIQUE(device_id, slot_position)` và `UNIQUE(account_id)`. Một tài khoản chỉ gán duy nhất 1 máy, 1 slot.
3. **Folder Video chuẩn công thức**:
   $$\text{FolderVideo} = (\text{Máy} - 1) \times 8 + \text{Slot}$$
4. **Video Gốc chuẩn công thức**:
   $$\text{VideoGoc} = (\text{Slot} - 1) \times 80 + \text{Máy}$$
5. **1 Folder Video Gốc = 1 Kênh duy nhất**: Không nhồi nhiều kênh vào cùng 1 folder làm lẫn lộn nhận diện.

## 2. Preflight Validator (`excel_preflight_validator.py`)
- Script tại `D:/Taadaa/tools/excel_preflight_validator.py`.
- Chạy kiểm tra trước mỗi ca: `python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir "D:/OneDrive/TaadaaData/kibe"`.
- Bắt buộc trả về exit code `0` (PASS 100%) mới được phép khởi chạy ca nuôi hay upload.

## 3. Just-In-Time (JIT) Reconciliation
- Trước khi thêm nick/bù slot: Đọc Switcher máy thật qua ATX-Agent dump XML hoặc WinRT OCR. Nếu đủ 8 nick $\rightarrow$ Chặn lại (Fail-Loud), yêu cầu logout nick mồ côi trước.
- Sau khi thêm nick: Đọc màn hình Profile chính chủ để xác nhận nick đã thực sự vào máy.
- Tuyệt đối không dùng SQLite chia sẻ qua OneDrive giữa Kibe và Admin để tránh lỗi file lock.
