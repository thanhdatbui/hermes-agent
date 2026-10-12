# TikTok Avatar Note Bubble Trap & Profile Layout C Incident (2026-10-12)

## 1. Hiện tượng & Sự cố thực tế (Incident 12/10/2026)
- **Bối cảnh:** User yêu cầu đổi avatar cho tài khoản `@cao.m.phng7` trên Máy 21 (Folder 163 - ngách Phát triển bản thân / Ông Chú Tâm Lý).
- **Sự cố 1 (Bẫy Bong bóng Note & Ngộ nhận đã đổi avatar):**
  - Script chạy xong, Agent chụp màn hình và crop theo tọa độ Layout B cũ `[90, 160, 330, 400]`.
  - Vùng crop rơi trúng khoảng trắng và bong bóng Note *"Bạn có tin vui?"*, nhưng Agent lại hallucinate kết luận là: *"Đã đổi thành công avatar Ông Chú Tâm Lý, ngũ quan rõ nét 100%"*.
  - User gửi lại ảnh chụp đúng góc bong bóng Note *"Bạn có tin vui?"* kèm phản hồi chất vấn: *"Gì v ?"*.
  - Kiểm tra thực tế: Avatar của kênh **HOÀN TOÀN CHƯA ĐỔI**, vẫn giữ nguyên ảnh bạn nữ cũ (tóc búi, đeo khuyên tai ngọc trai).

---

## 2. Nguyên nhân kỹ thuật cốt lõi (Root Cause)

### A. Biến thể Profile Layout C (Avatar góc trên bên phải, Không có nút 'Sửa hồ sơ' ở giữa)
TikTok có nhiều biến thể giao diện trang cá nhân (Profile):
- **Layout A (Cũ):** Avatar ở giữa `(x ~ 540, y ~ 280)`, có icon bút chì hoặc nút Sửa hồ sơ ở giữa.
- **Layout B (Cá nhân mới 1):** Avatar lệch trái `(x ~ 210, y ~ 280)`, có nút hình chữ nhật xám "Sửa hồ sơ" ở giữa `(327, 748)`.
- **Layout C (Cá nhân mới 2 / TikTok v47+):**
  * Avatar nằm ở **góc trên bên phải**: bounds `[708, 300][1080, 636]`.
  * Tên hiển thị và username nằm ở **bên trái**: `[36, 280][672, 364]`, `@cao.m.phng7` `[36, 370][309, 415]`.
  * **HOÀN TOÀN KHÔNG CÓ nút "Sửa hồ sơ" ở giữa!** Vị trí này chỉ có nút *"Thêm tiểu sử"* (`[36, 660][838, 744]`). Khi đã có tiểu sử thì nút này biến mất và chỉ còn dòng text tiểu sử.
  * Việc áp dụng cứng tọa độ Layout B `(327, 748)` trên Layout C sẽ tap trượt vào khoảng trống hoặc rơi vào ô nhập tiểu sử (Bio), hoàn toàn không mở màn Sửa hồ sơ!

### B. Cạm bẫy Bong bóng Trạng thái / Story Note (Note Thought Bubble Trap)
- Trên Layout C, TikTok gắn tính năng Note/Trạng thái 24h vào avatar.
- Một bong bóng suy nghĩ màu trắng (`[763, 258][1037, 465]`) mọc đè ngay phía trên/bên cạnh vòng tròn avatar với các câu text gợi ý: *"Bạn có tin vui?"*, *"Thì thầm to nhỏ"*, *"Trà hay cà phê?"*, *"Bạn có chuyện gì?"*.
- **Bẫy Tap Avatar:** Khi tap vào vùng avatar `[708, 300][1080, 636]`, TikTok kích hoạt tính năng Note 24h và mở bottom sheet *"Hiển thị với follower trong 24 giờ"* với ô EditText và nút *"Đăng"*, thay vì mở Photo Picker!
- **Bẫy Crop Zoom sai tọa độ:** Khi script crop theo tọa độ cũ của Layout B (`cx=210, cy=280`), ảnh cắt ra rơi vào vùng trống hoặc cạnh bong bóng Note, dẫn đến báo cáo mù và ảo giác thị giác nghiêm trọng.

### C. Xung đột Device Lock với Ca nuôi Cron Farm (Feed Session Lock Collision)
- Trên Farm 80-280 máy, các ca nuôi tài khoản (`multi-machine-feed-session`, `run_tiktok.py`) chạy ngầm định kỳ theo lịch.
- Tiến trình nuôi giữ file lock `~/.codex/device-locks/machine_N.lock.json` với PID thực tế đang hoạt động (ví dụ PID `62992`).
- **Nguy cơ xóa nhầm Lock:** Nếu Agent tự tiện dùng script xóa file lock khi PID đó vẫn đang sống trong `psutil`, hai tiến trình ADB sẽ cùng lúc can thiệp vào máy, gây xung đột lệnh tap, văng app TikTok và làm hỏng cả ca nuôi lẫn tác vụ đổi avatar.

---

## 3. Quy tắc khắc phục & Kỷ luật vận hành bắt buộc

### 1. Phân loại Layout trước khi Tap (UI XML Pre-check)
- CẤM TUYỆT ĐỐI tap mù theo tọa độ cứng khi chưa xác định layout.
- Trước khi thực hiện luồng đổi avatar, BẮT BUỘC dump UI XML (`uiautomator dump`) để xác định layout:
  * Nếu XML có node text `"Sửa hồ sơ"` -> Layout B: Lấy bounds chính xác của node đó để tap (thường `327, 748`).
  * Nếu avatar nằm ở `x > 700` và có text `"Thêm tiểu sử"` -> **Layout C**: Avatar ở góc phải, cần xử lý luồng riêng, không dùng tọa độ Layout B.

### 2. Kỷ luật Zoom Crop Vòng tròn Avatar chuẩn theo Layout (Chống Báo cáo Láo)
- Tọa độ crop kiểm chứng BẮT BUỘC phải lấy theo bounds của node `Ảnh hồ sơ` trong XML:
  * Layout A: Center `(540, 280)`.
  * Layout B: Center `(210, 280)`.
  * Layout C: Center `((708+1080)//2, (300+636)//2) = (894, 468)`.
- **Soi mắt tận mắt qua `browser_vision`:**
  * Mở file crop kiểm tra: BẮT BUỘC thấy rõ ngũ quan người thật (mắt, mũi, miệng) hoặc nhân vật mới (ví dụ Ông Chú Tâm Lý).
  * Nếu thấy bong bóng suy nghĩ trắng hoặc avatar vẫn là người cũ (bạn nữ áo đen, khuyên tai ngọc trai) -> **BÁO CÁO NGAY LÀ CHƯA ĐỔI**, CẤM TUYỆT ĐỐI báo cáo khống đã hoàn tất!

### 3. Kỷ luật Device Lock: Kiểm tra PID trước khi can thiệp
- Khi gặp `SKIPPED_LOCKED` hoặc nghi ngờ stale lock:
  * BẮT BUỘC đọc file lock lấy `pid`.
  * Dùng `psutil.Process(pid).is_running()` để kiểm tra tiến trình.
  * **NẾU PID CÒN SỐNG:** Đây là tiến trình nuôi hợp lệ của Farm! CẤM XÓA LOCK, CẤM CAN THIỆP MÁY. Báo cáo rõ ràng máy đang bận ca nuôi và chờ nhả lock.
  * **CHỈ ĐƯỢC XÓA LOCK** khi `psutil.NoSuchProcess` xác nhận tiến trình đã chết (stale lock thực sự).
