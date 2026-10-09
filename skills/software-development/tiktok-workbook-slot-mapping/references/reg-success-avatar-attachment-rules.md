# Quy Tắc Gắn Up-Avatar Ngay Sau Khi Reg Thành Công Trong Tiktok_Reg

## Bối Cảnh
Khi tài khoản TikTok vừa đăng ký hoặc login hoàn tất (`Tiktok_Reg`), cần cập nhật ngay avatar để tài khoản hoàn thiện danh tính, tránh tình trạng nick phôi trắng kéo dài hoặc phải đợi đến chu kỳ upload video.

## Quy Chuẩn Nguồn Avatar & Chống Xung Đột Namespace
1. **Đường dẫn chuẩn duy nhất**:
   - `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg` (hoặc `.jpeg`, `.png`).
   - Đây là ảnh đã được trích xuất/sinh kèm khi render video cho từng output folder.
2. **CẤM Fallback sang `D:\video goc\<Folder Video>\avatar.jpg`**:
   - Dải `Folder Video` của các slot về sau (như Slot 5: 5, 13, 21...) trùng số với dải `video gốc` của Slot 1 (1..80), dẫn tới việc nhầm ảnh của tài khoản khác trên máy khác.

## Quy Tắc Mapping Slot & Folder Video (Slot 1..8)
- Công thức tính chuẩn theo vị trí slot $k$ ($1 \le k \le 8$) của máy $m$ ($1 \le m \le 80$):
  $$\text{Folder Video} = (m - 1) \times 8 + k$$
- Cột `Folder Video` (Cột 2) trong sheet `Tài Khoản` của `taikhoan_dat_v2_updated .xlsx` mang đúng giá trị này.
- **Quy tắc Slot 7 & 8 (Phôi Trắng)**:
  - Máy $m$ có Slot 7 = $(m-1)\times 8 + 7$, Slot 8 = $(m-1)\times 8 + 8$.
  - Hai file `Tik7.xlsx` và `Tik8.xlsx` hiện **CHƯA TỒN TẠI** (farm chỉ có Tik1 đến Tik6).
  - Khi up avatar cho Slot 7 & 8: chỉ log trạng thái và folder video tương ứng, **TUYỆT ĐỐI KHÔNG tự ý tạo file workbook mới `Tik7.xlsx` / `Tik8.xlsx`**.

## Nguyên Tắc Tích Hợp & Fail-Safe
1. **Điểm Móc Nối (Hook)**:
   - Gắn trong `ensure_profile_completed_and_track` sau khi `wait_login_success` trả về `ok = True` (và sau khi đã cập nhật Display Name).
2. **Fail-Safe Không Chặn Luồng Reg**:
   - Nếu không tìm thấy file avatar tại `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg` $\rightarrow$ log cảnh báo `AVATAR_SOURCE_MISSING` và bỏ qua nhẹ nhàng, tuyệt đối không làm crash hay dừng luồng reg tài khoản.
3. **Dọn dẹp Device Cache**:
   - Dọn sạch ảnh chụp màn hình tạm hoặc ảnh cũ: `rm -f /sdcard/DCIM/Camera/avatar* /sdcard/Download/avatar* /sdcard/_ss*.png`.
   - Sau khi hoàn tất up avatar, đóng app và đưa máy về Home: `am force-stop com.zhiliaoapp.musically; am force-stop com.ss.android.ugc.trill; input keyevent 3`.
4. **Cờ Bỏ Qua**:
   - Hỗ trợ flag CLI `--no-avatar-after-reg` hoặc env `TIKTOK_REG_AVATAR_AFTER_REG=0` để bỏ qua bước up avatar khi cần reg nhanh hoặc bypass.
