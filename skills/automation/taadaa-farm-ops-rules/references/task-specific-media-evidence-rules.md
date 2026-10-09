# Evidence-First Rules by Task Type

## Nguyên tắc cốt lõi
Khi nghiệm thu một hành động can thiệp / fix lỗi trên farm (Action Verb + Artifact), ảnh MEDIA chụp lại PHẢI phản ánh trạng thái thành công đích của chính nghiệp vụ đó, TRƯỚC KHI thực hiện teardown về HOME.

Tuyệt đối KHÔNG chụp ảnh màn hình HOME hoặc màn hình ngẫu nhiên (Feed, Sleep) để nghiệm thu cho một tác vụ có màn hình đích cụ thể.

## Mapping chi tiết theo từng nghiệp vụ:

1. **Clear Cache TikTok (Dọn dẹp bộ nhớ đệm):**
   - **Màn hình đích:** Màn hình "Giải phóng dung lượng" / "Free up space".
   - **Bằng chứng hợp lệ:** Chụp screencap ngay khi dòng "Bộ nhớ đệm" / "Cache" hiển thị **0,0MB** (hoặc 0.0MB) sau khi bấm Xóa và xác nhận dialog.
   - **Cấm:** Chụp Feed video TikTok hoặc chụp màn hình Launcher Home để báo cáo nghiệm thu clear cache. Sau khi chụp bằng chứng 0,0MB mới force-stop TikTok và về Home.

2. **Login / Logout / Switcher TikTok:**
   - **Login thành công:** Màn hình Hồ sơ (Profile) hiển thị đúng username mục tiêu.
   - **Logout / Dọn nick ký sinh (INVARIANT BẮT BUỘC):**
     * **Màn hình đích duy nhất hợp lệ:** BẮT BUỘC mở và chụp screencap tại **Account Switcher Bottom Sheet** (màn hình "Chuyển đổi tài khoản" liệt kê danh sách tài khoản còn lại và hiển thị nút "Thêm tài khoản" / "Add account").
     * **CẤM TUYỆT ĐỐI:** Gửi ảnh màn hình "Cài đặt và quyền riêng tư", màn hình Profile, hay màn hình Launcher/Home làm bằng chứng nghiệm thu dọn ký sinh. Người dùng cần nhìn thấy danh sách nick trên Switcher để xác nhận nick ký sinh đã biến mất và slot đã được giải phóng.
   - **2FA:** Màn hình popup phê duyệt thiết bị hoặc đã vào trong trang chủ/profile sau khi duyệt.

3. **ChatGPT / OAuth:**
   - **Nghiệm thu:** Mất nút [Đăng nhập], có icon avatar hoặc [+ Nâng cấp gói] / giao diện chatbox sẵn sàng.

4. **Gmail / Google Account:**
   - **Check live / Sync:** Màn hình Đồng bộ hóa tài khoản hoặc Inbox của Gmail mục tiêu.

5. **Quy trình chuẩn 3 bước khi hoàn thành tác vụ:**
   - **Bước 1:** Đến màn hình đích -> Thực hiện hành động -> Chờ trạng thái đích xuất hiện.
   - **Bước 2:** Chụp screencap lưu file ảnh evidence đích (ví dụ `mXX_cache_cleared_0mb.png`).
   - **Bước 3:** Teardown an toàn (`am force-stop`, `input keyevent KEYCODE_HOME`, nhả lock).
   - **Bước 4:** Báo cáo kết quả và đính kèm `MEDIA:<path_anh_evidence_buoc_2>`.
