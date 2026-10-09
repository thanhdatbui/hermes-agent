# Khắc phục lỗi TikTok Login trên máy Admin (STT >= 201) & Cơ chế Switcher vs One-tap Login

## 1. Lỗi Resolve Device trên cụm Admin (`tiktok_login_v1.py`)
### Hiện tượng
Khi chạy:
```bash
python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py 266 --email letam2502
```
Script crash ngay lập tức:
```text
STOPPED: Khong co STT 266 trong ACCOUNTS
```

### Nguyên nhân
- `tiktok_login_v1.py` dùng mảng cứng `ACCOUNTS` từ `social_reg_v1.py`, mảng này chỉ định nghĩa máy STT 1..80 của cụm Kibe.
- Các máy Admin (STT 201..280) không nằm trong `ACCOUNTS`.

### Giải pháp chuẩn
Cập nhật `resolve_device(stt)` trong `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py`:
- Nếu STT có trong `ACCOUNTS` và có serial `device`: return serial đó.
- Nếu không có: fallback sang `scripts.target_inventory.load_machine_devices(TARGET_INVENTORY_WORKBOOK)` (đọc từ `taikhoan_run_safe.xlsx`).
- Luôn truyền `ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"` và `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml"` khi thao tác trên cụm Admin.

---

## 2. Cơ chế Account Switcher vs One-tap Login ("Chào mừng bạn trở lại")
### Hiện tượng
- User thắc mắc: "Tại sao đăng nhập cả 2 acc rồi mà account switcher không bung ra? Bấm vào tên không bung ra switcher mà lại xuất hiện màn Chào mừng bạn trở lại?"
- Bấm vào tên `letam2502` hay `bongbong0289` ở góc trái Profile không bung Switcher mà mở widget "Thêm vị trí/sở thích".

### Bản chất kỹ thuật trên TikTok v46.x (Android 8 / Galaxy S7)
1. **Tại sao không có chevron ▼ bên cạnh tên?**
   - Với các layout TikTok mới, tên hiển thị trên Profile nằm ở góc trái (`bounds=[36, 256][397, 340]`), bên cạnh hoàn toàn không có icon mũi tên dropdown.
   - Khi chưa cuộn, bấm vào tên chỉ là text tĩnh hoặc mở trang chi tiết bio/vị trí.
2. **Quy tắc bung Switcher theo thiết kế hệ thống:**
   - **Bắt buộc cuộn nhẹ Profile lên** (swipe từ dưới lên khoảng 600px) để thanh tiêu đề dính cố định (`pmf` / `pmi`) xuất hiện trên cùng chính giữa màn hình header.
   - Khi đó bấm vào thanh tiêu đề `pmf` trên header mới kích hoạt bung Account Switcher.
3. **Tại sao trong Settings chỉ có "Đăng xuất" mà không có "Chuyển đổi tài khoản"?**
   - Khi app chỉ có duy nhất 1 session active độc lập, TikTok ẩn mục "Chuyển đổi tài khoản" ở đáy Settings.
   - Muốn thêm tài khoản mới khi đang ở trạng thái này:
     + Cách A: Vào Settings -> Cuộn đáy -> Bấm "Đăng xuất" (TikTok tự lưu session cũ vào One-tap Login) -> Về Profile bấm "Đăng nhập" -> "Thêm tài khoản khác" -> Đăng nhập bằng Email/OTP.
     + Cách B: Mở màn hình One-tap Login ("Chào mừng bạn trở lại") -> Bấm "Thêm tài khoản khác".
4. **Trạng thái One-tap Login ("Chào mừng bạn trở lại"):**
   - Cả 2 tài khoản đều được lưu giữ token an toàn trong app. Chạm vào nick nào trên danh sách One-tap là app lập tức chuyển active sang nick đó trong 1 giây mà không cần nhập lại mật khẩu/OTP.
