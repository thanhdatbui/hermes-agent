# TikTok Saved Account Tile Removal & Quick Login 2FA Pitfall

## Bối cảnh & Hiện tượng

Khi TikTok trên Android (phiên bản 46.x / mới) ở trạng thái đăng xuất nhưng có lưu credential tài khoản trước đó, app sẽ hiển thị modal **"Chào mừng bạn trở lại"** (Quick Login Tile).

### Cấu trúc UI của Modal "Chào mừng bạn trở lại"
- Header: `Chào mừng bạn trở lại` (`id/ym3`, bounds `[96,1000][984,1114]`)
- Tên tài khoản lưu: `@username` (`id/ym7`, bounds `[96,1114][984,1228]`)
- Nút "Đăng nhập" (One-tap login): `id/ym4` (bounds `[180,1336][900,1480]`, center `540, 1408`)
- Nút "Thêm tài khoản khác": `id/ym6` (bounds `[180,1480][900,1624]`, center `540, 1552`)
- Nút "Đóng" (Close): `id/z84` (bounds `[936,168][1068,300]`, center `1002, 234`)
- Nút "Báo cáo vấn đề": `id/z6m` (bounds `[12,168][144,300]`)

## Cạm bẫy (Pitfalls)

1. **CỰC KỲ NGUY HIỂM: CẤM bấm "Cài đặt & quyền riêng tư -> Đăng xuất" để gỡ 1 tài khoản trên máy có nhiều nick:**
   - Trên TikTok Android, nút "Đăng xuất" ở đáy Cài đặt sẽ đăng xuất **TOÀN BỘ PHIÊN LÀM VIỆC (Multi-account session)** của ứng dụng, đá app về màn hình đăng nhập trắng ("Hồ sơ -> Đăng nhập vào tài khoản hiện có").
   - Hậu quả: Toàn bộ 6–8 tài khoản trên máy đều bị văng khỏi UI session, gây hoang mang và hiểu lầm là đã "phá bay toàn bộ account khỏi máy".
   - **Xử lý chuẩn:** Tuyệt đối không bấm Đăng xuất trong Cài đặt khi máy có nhiều nick. Muốn gỡ tài khoản rác/lưu nhầm, sử dụng module `automation_core.tiktok.fast_login` (`handle_fast_login_screen`) ở màn hình landing đăng nhập (menu 3 chấm -> Xóa tài khoản) hoặc dùng Account Switcher để quản lý.

2. **Không có nút xóa/quản lý tài khoản trực tiếp trên modal "Chào mừng":**
   - Trên modal "Chào mừng bạn trở lại" (`id/ym3`) **không có** icon 3 chấm, bánh răng cài đặt, hay nút "Chỉnh sửa" / "Quản lý tài khoản".
   - Thiết bị Farm không có quyền `su` (root shell non-root), không thể can thiệp trực tiếp file hệ thống `/data/data/com.ss.android.ugc.trill/shared_prefs` hay database SQLite.

3. **One-tap login có thể bị chặn bởi 2FA / Email Verification:**
   - Khi tap "Đăng nhập" (`id/ym4`), nếu session token đã hết hạn hoặc TikTok gắn cờ thiết bị/IP, app sẽ không vào thẳng Profile mà kích hoạt màn hình:
     > *"Xác minh email: Sử dụng liên kết này hoặc nhập mã được gửi đến <email>"*
   - Nếu không có quyền truy cập hộp thư (Hotmail/Outlook), máy sẽ bị kẹt ở màn hình nhập OTP 6 số.

## Hướng xử lý chuẩn

### Kịch bản 1: Cần chuyển sang tài khoản khác trên máy
- Không bấm "Đăng nhập" vào tài khoản lưu không rõ OTP.
- Bấm nút **"Đóng"** (nút X `id/z84` tại `[936,168][1068,300]`) hoặc **"Thêm tài khoản khác"** (`id/ym6`) để mở trang chọn phương thức đăng nhập thông thường (Sử dụng số điện thoại / email / tên người dùng).
- Tiến hành đăng nhập nick đích.

### Kịch bản 2: Bị văng session toàn bộ (Khôi phục Reconcile)
- Nếu máy bị đăng xuất toàn bộ về màn hình Hồ sơ trắng, toàn bộ thông tin tài khoản (ID, mật khẩu, 2FA, email) vẫn được lưu an toàn 100% trong `taikhoan_dat_v2_updated .xlsx`.
- Kích hoạt runner chuẩn của farm để đăng nhập khôi phục:
  ```bash
  env -u PYTHONPATH "D:/Taadaa/python-envs/automation/Scripts/python.exe" \
    "D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py" \
    --workbook "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx" \
    --machines <STT> \
    --adb-path "C:/Program Files (x86)/xiaowei/tools/adb.exe" \
    --login-project "D:/Taadaa/Tiktok_Reg" \
    --login-workbook "D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx" \
    --allow-live-reconcile \
    --full-scope-takeover
  ```

## Quy chuẩn Nghiệm thu Bằng chứng (Verification Proof Gate)
- **BẮT BUỘC CHỤP ACCOUNT SWITCHER:** Khi thực hiện đăng nhập, đăng xuất, hoặc kiểm tra danh sách tài khoản trên máy, ảnh chụp màn hình nghiệm thu (`MEDIA:<path>`) **BẮT BUỘC** phải chụp tại **Bottom Sheet "Chuyển đổi tài khoản" (Account Switcher)**.
- Ảnh nghiệm thu phải thể hiện rõ ràng toàn bộ danh sách các nick đang active trên thiết bị.
- **CẤM TUYỆT ĐỐI:** Chụp ảnh màn hình Cài đặt và quyền riêng tư, popup xác nhận, màn hình Home, hay màn hình Hồ sơ trắng rồi báo cáo hoàn thành. User sẽ reject ngay lập tức nếu ảnh nghiệm thu không chụp đúng Account Switcher.
