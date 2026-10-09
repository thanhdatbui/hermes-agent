# Taikhoan_run_safe Single Source of Truth & Zero-Manifest Rule (2026-09-03)

## 1. Nguyên tắc cốt lõi (User chốt 2026-09-03)
- File nguồn tài khoản duy nhất và chính thống cho toàn bộ farm: `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`.
- Mỗi máy có tối đa 6 slot tài khoản tương ứng:
  - Slot 1 = Tik1 (Ca 1 - Phiên 1)
  - Slot 2 = Tik2 (Ca 1 - Phiên 2)
  - Slot 3 = Tik3 (Ca 2 - Phiên 1)
  - Slot 4 = Tik4 (Ca 2 - Phiên 2)
  - Slot 5 = Tik5 (Ca 3 - Phiên 1)
  - Slot 6 = Tik6 (Ca 3 - Phiên 2)
- **CẤM TỰ CHẾ MANIFEST**: Mọi script vận hành, batch launcher, avatar upload hay watchdog phải lấy danh sách máy và nick trực tiếp từ `taikhoan_run_safe.xlsx` (hoặc workbook `TikN.xlsx` đã sync tương ứng). Tuyệt đối không tự sinh hoặc phụ thuộc vào các file JSON manifest trung gian (`assignment-manifest-*.json`) không cần thiết.

## 2. Quy trình lọc máy khi chạy Batch
1. **Đọc `taikhoan_run_safe.xlsx`**: Lấy danh sách máy có tài khoản hợp lệ ở Slot tương ứng với ca cần chạy.
2. **Lọc trạng thái ADB Live**:
   - Chạy `adb devices` để lấy danh sách serial thực sự đang `device` (online).
   - Loại bỏ các máy offline (máy mất kết nối USB/Wi-Fi).
   - Loại bỏ các máy chưa được gán nick (cột ID trống hoặc `None`).
3. **Kích hoạt Launcher chuẩn**:
   - Truyền danh sách máy đã lọc qua `-ForceAvatarMachineList "<m1,m2...>"` vào `run_tiktok_upload_batch.ps1` với `-MaxParallel 40` (không cần tham số manifest).
