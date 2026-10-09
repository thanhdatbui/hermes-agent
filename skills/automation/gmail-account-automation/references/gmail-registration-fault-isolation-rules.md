# Gmail Registration Fault Isolation & Inventory Rules

## Nguyên Tắc Vận Hành: "Sai Máy Nào Bỏ Qua Máy Đó, Tuyệt Đối Cấm Dừng Cả Farm"

### 1. Bối Cảnh Thực Tế & Lỗi Điển Hình
- Khi file mapping Excel (`taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx`) có 1 dòng bị dán nhầm serial (ví dụ: máy 62 có 8 slot nhưng 1 slot bị dán serial máy khác), hàm `load_device_map_from_excel()` trong `gmail_reg_v10.py` ném `RuntimeError`:
  `RuntimeError: Device map has conflicting valid serials for machine(s): 62`
- Điều này khiến `run_all.ps1` và watchdog sau ca trưa `post_noon_chain_watchdog.py` bị văng `Exit Code 1`, tổng số máy khởi động = 0, toàn bộ 79 máy bình thường khác bị hủy ca chạy.

### 2. Kỷ Luật Xử Lý Cốt Lõi
- Trong `load_device_map_from_excel()`, khi phát hiện máy có serials xung đột:
  - CẤM ném `RuntimeError`.
  - BẮT BUỘC log cảnh báo: `[warn] Máy {stt}: có nhiều serial khác nhau -> bỏ qua máy này để không dừng cả farm`.
  - Loại riêng máy bị lỗi ra khỏi `device_map` (`if stt not in conflicts`).
  - Toàn bộ các máy chuẩn còn lại tiếp tục được nạp và khởi chạy bình thường.
- Tuyệt đối giữ nguyên vẹn dữ liệu nick, password, email và ngày tạo của mọi tài khoản trong Excel khi đối soát/sửa dữ liệu farm.
