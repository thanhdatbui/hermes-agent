# Safe Workbook Inventory & Cross-Machine Serial Reconciliation

## Hiện tượng & Nguyên nhân xung đột
- Khi chạy detector đăng ký TikTok (`_detect_clean.py` trong repo `Tiktok_Reg`), script đọc file `taikhoan_run_safe.xlsx` qua module `scripts/target_inventory.py` và fail-closed với mã lỗi `TARGET_INVENTORY_CONFLICT: machine X` nếu phát hiện cùng một máy có nhiều serial khác nhau hoặc cùng một serial bị gán trùng cho 2 máy khác nhau.
- Nguyên nhân: File `taikhoan_run_safe.xlsx` được sinh từ script đồng bộ (`sync-safe-workbook.py` trong repo `tiktok-luot nuoi acc`) có từ điển `EXTRA_MACHINES` cấu hình ánh xạ serial cho các máy bổ sung (ví dụ máy 75..80). Nếu từ điển này bị sai lệch thứ tự serial so với file cấu hình chuẩn (`Tik1.xlsx` / ADB thực tế), detector sẽ chặn toàn bộ batch reg.

## Quy trình chuẩn hóa & phục hồi
1. **Kiểm tra serial thực tế trên thiết bị:**
   - Đối chiếu danh sách serial từ lệnh `adb devices` và cột `device ID` trong file chuẩn `Tik1.xlsx`.
2. **Cập nhật ánh xạ `EXTRA_MACHINES` trong `sync-safe-workbook.py`:**
   - Đảm bảo mỗi máy từ 75..80 được gán đúng serial tương ứng.
3. **Tái tạo `taikhoan_run_safe.xlsx`:**
   - Chạy lệnh: `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py"` để sinh lại đủ 480 dòng chuẩn (80 máy x 6 slot).
4. **Kiểm thử với detector:**
   - Chạy `python _detect_clean.py` trong `Tiktok_Reg` để xác nhận detector vượt qua bước kiểm tra inventory và trả về danh sách target hợp lệ.
