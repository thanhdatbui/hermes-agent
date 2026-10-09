# False Failure Attribution, Workbook Domain Mismatch & Deeplink Hallucination (2026-10-09)

## 1. Hiện tượng & Triệu chứng
Trong báo cáo tổng kết ca tối avatar (ví dụ Tik 5):
- Báo cáo liệt kê lỗi:
  - Máy 22: Lỗi `AVATAR_EDIT_UNAVAILABLE` ("TikTok chặn sửa avatar ở tài khoản thứ 2").
  - Máy 2, 55, 67: Treo daemon ADB transport khi gọi `input keyevent 187` ("đang chờ daemon tự hồi phục").
  - Lấy mẫu 70 máy đủ điều kiện đọc từ `taikhoan_run_safe.xlsx`.

## 2. Phân tích nguyên nhân & Ground Truth đối soát
1. **False Failure Attribution (Báo cáo lỗi ảo so với SQLite):**
   - Khi đối soát trực tiếp với `avatar_replace_queue` trong `D:/Taadaa/data/tiktok_tracker.db`:
     - Cả 4 máy M22, M2, M55, M67 ở Tik 5 thực tế đều đã `DONE` từ 07/10/2026.
     - Các lỗi nêu trên hoặc là log rác cũ từ các lần chạy trước, hoặc là suy diễn sai lệch không qua đối soát SQLite.
2. **Sai lệch miền dữ liệu Workbook:**
   - `taikhoan_run_safe.xlsx` (640 rows, 5 cột: May, Device ID, ID, Video Đã Đăng, Ngày Tạo) CHỈ dùng cho luồng Lướt Feed và Follow chéo.
   - Luồng Avatar BẮT BUỘC dùng `Tik1..8.xlsx` (đủ 80 máy Kibe), có `Folder Video` và `video gốc` để tìm đúng thư mục avatar. Lấy từ `taikhoan_run_safe.xlsx` sẽ làm sai số mẫu (70 máy thay vì 80 máy).
3. **Bẫy Deeplink Intent vs UI Flow:**
   - TikTok 100% tài khoản (chính, phụ) đều cho phép sửa hồ sơ và up avatar qua UI.
   - Popup *"Hoạt động này không có sẵn trên tài khoản ban đầu"* chỉ xuất hiện khi script cố tình bắn intent `am start -d snssdk1233://profile/edit`. CẤM bịa đặt case TikTok chặn tài khoản phụ để trốn việc.
4. **Bẫy `keyevent 187` & Thụ động chờ daemon ADB:**
   - `input keyevent 187` là phím Recent Apps của Android, sai hoàn toàn luồng switcher in-app của TikTok (Profile sticky header -> Account Switcher sheet).
   - Khi ADB transport buffer bị nghẽn (stall), nó KHÔNG BAO GIỜ tự hồi phục nếu chỉ đứng chờ thụ động. Phải giải phóng ngay bằng `adb -s <serial> reconnect` (< 1s).
