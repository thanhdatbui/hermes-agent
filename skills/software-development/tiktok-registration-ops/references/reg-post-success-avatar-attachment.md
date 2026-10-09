# Gắn Up-Avatar Ngay Sau Reg Thành Công Trong Tiktok_Reg

## Bối cảnh & Mục đích
- Khi đăng ký TikTok thành công trên thiết bị (`Tiktok_Reg`), cần cập nhật ngay avatar đại diện từ kho ảnh chuẩn đã render thay vì để nick phôi trắng hoặc đợi đến phiên upload video mới up.
- Tránh lỗi xung đột namespace giữa `Folder Video` (1..640) và `video gốc` (1..480).

## Quy chuẩn Nguồn Avatar
1. **Avatar Source chuẩn duy nhất**:
   - `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg` (hoặc `.jpeg`, `.png`).
   - Đây là ảnh đã được sinh kèm khi render video cho từng folder output.
2. **CẤM Fallback sang `D:\video goc\<Folder Video>\avatar.jpg`**:
   - Dải `Folder Video` của các nick sau (như Tik5: 5, 13, 21...) trùng số với dải `video gốc` của Tik1 (1..80), dẫn tới việc bốc nhầm ảnh nguồn của nick máy khác.

## Quy tắc Mapping Slot & Folder Video (Slot 1..8)
- Công thức tính chuẩn theo vị trí slot:
  $$\text{Folder Video} = (m - 1) \times 8 + k$$
  với $m$ là số thứ tự máy ($1 \le m \le 80$), $k$ là số thứ tự slot ($1 \le k \le 8$).
- Cột `Folder Video` (Cột 2) trong sheet `Tài Khoản` của `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` mang đúng giá trị này.
- **Quy tắc Slot 7 & 8 (Phôi Trắng)**:
  - Máy $m$ có Slot 7 = $(m-1)\times 8 + 7$, Slot 8 = $(m-1)\times 8 + 8$.
  - Hai file `Tik7.xlsx` và `Tik8.xlsx` hiện **CHƯA TỒN TẠI** (chỉ có Tik1 đến Tik6).
  - Khi up avatar cho Slot 7 & 8: chỉ log trạng thái và folder video tương ứng, **TUYỆT ĐỐI KHÔNG tự ý tạo file workbook mới `Tik7.xlsx` / `Tik8.xlsx`**.

## Nguyên tắc Tích hợp & An toàn (Fail-Safe)
1. **Điểm Móc Nối (Hook)**:
   - Được gắn ngay sau khi `wait_login_success` trả về `ok = True`, bên trong `ensure_profile_completed_and_track` (hoặc ngay sau khi hoàn tất thiết lập tên hiển thị).
2. **Fail-Safe Không Chặn Reg**:
   - Nếu không tìm thấy file avatar tại `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg` $\rightarrow$ log cảnh báo `AVATAR_SOURCE_MISSING` và bỏ qua nhẹ nhàng, tuyệt đối không làm crash hay dừng luồng reg tài khoản.
3. **Dọn dẹp Device Cache sau khi Up**:
   - Dọn sạch ảnh chụp màn hình tạm hoặc ảnh cũ: `rm -f /sdcard/DCIM/Camera/avatar* /sdcard/Download/avatar* /sdcard/_ss*.png`.
   - Sau khi cập nhật avatar xong, đóng app và đưa máy về Home: `input keyevent 3`.
4. **Cờ Bỏ Qua**:
   - Hỗ trợ flag CLI `--no-avatar-after-reg` hoặc env `TIKTOK_REG_AVATAR_AFTER_REG=0` để bỏ qua bước up avatar khi cần reg nhanh hoặc bypass.
