# Ca 2 (Chiều) 2026-08-25: Vận hành Nuôi acc & Phân tích Đăng Video

## 1. Thông tin Vận hành Ca Chiều (2026-08-25)
- **Tài khoản chạy:** Thuộc Row 3 trong mapping và `tik3.xlsx` (Ca 2).
- **Lịch phiên nuôi:**
  - Phiên 1 (12:00 – 13:45): 50 máy Success, 2 máy dừng an toàn (M2, M42 - kẹt Location popup đã fix).
  - Phiên 2 (13:45 – 15:30): Toàn bộ máy chạy bù & chính hoàn tất mượt mà.
  - Phiên 3 (15:30 – 18:20): **53/53 máy Success (100%)**, 0 máy Fail.
- **Có đăng video ở cuối Phiên 3 ca chiều không?**
  - **KHÔNG.** Hệ thống cấu hình hook upload tự động chỉ chạy cho `Row 1` và `Row 2` (thuộc `Tik1.xlsx` và `Tik2.xlsx` có lịch video).
  - Toàn bộ 662 lượt check hook upload trong các đợt chạy Row 3 chiều nay đều tự động ghi nhận trạng thái: `status: skipped` với lý do `upload-disabled-outside-row-1-2`.

## 2. Phân loại 27 máy không tham gia trong Ca Chiều (Tổng 80 máy, chạy 53 máy)
1. **Trống nick TikTok trên `tik3.xlsx` (15 máy):**
   - `22, 31, 34, 39, 40, 53, 66, 67, 70, 73, 75, 77, 78, 79, 80`
   - Ô ID tài khoản TikTok trong file `tik3.xlsx` đang để trống, runner tự động bỏ qua an toàn.
2. **Mất kết nối ADB Offline (4 máy):**
   - `61, 62, 63, 74`
   - Thiết bị mất kết nối cáp USB/ADB với host.
3. **Kẹt VPN ViChanger `blocked-vichanger-vpn` (5 máy):**
   - `33, 36, 37, 71, 72`
   - Thiết bị online nhưng ứng dụng ViChanger mất kết nối hoặc không get được IP live, cổng an toàn tự động ngắt (`fail-closed`).
4. **Tắt VPN trên thiết bị (1 máy):**
   - `76` (Không có interface `tun0` active).
5. **Trùng nick giữa các ca (2 máy):**
   - `10, 69` (`tik3.xlsx` đang điền trùng nick của Ca 2: `laquyen2601` / `quachtieu2106`), runner giữ an toàn không nạp trùng nick trong cùng ngày.
