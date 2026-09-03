# Quy tắc Tự Động Up Avatar Khi Đăng Video Đầu Tiên (Video #1)

## Bối cảnh & Mục đích
Khi farm tiến hành đăng video nuôi nick (ở Phiên 3 hàng ngày), các nick mới hoặc nick chưa từng đăng video (`Video Đã Đăng == 0`) cần được thiết lập đầy đủ nhận diện kênh ngay trong lần xuất bản đầu tiên.

## Quy tắc Nghiệp vụ (Policy)
1. **Điều kiện kích hoạt:**
   - Khi kiểm tra dữ liệu tài khoản (`Video Đã Đăng == 0` hoặc `video_number == 1` / lần đầu đăng video).
2. **Hành vi tự động:**
   - Sau khi hoàn tất đăng video 1 (`VERIFY_POST` -> `UPDATE_WORKBOOK`), workflow tự động kích hoạt state `ENSURE_AVATAR` để tải avatar lên Profile.
   - Nguồn ảnh avatar: Tự động trích xuất file `avatar.jpg`, `avatar.png`, hoặc `avatar.jpeg` từ thư mục media của nick đó (`D:\video goc\<Folder Video>\avatar.jpg`).
   - Tuyệt đối không đòi hỏi danh sách ép thủ công (`-ForceAvatarMachineList` hay `avatar_force_machines`) đối với trường hợp nick chưa có avatar / video đầu tiên.
3. **Các lần đăng tiếp theo (Video >= 2):**
   - Giữ nguyên avatar hiện tại, chỉ upload avatar mới nếu người dùng chủ động chỉ định trong `avatar_force_machines`.
