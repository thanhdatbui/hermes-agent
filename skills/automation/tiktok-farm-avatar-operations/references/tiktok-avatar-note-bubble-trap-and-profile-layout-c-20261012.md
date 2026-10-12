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

### 1. Phân loại Layout trước khi Tap (UI XML Pre-check) & Xác minh đúng Nick
- CẤM TUYỆT ĐỐI tap mù theo tọa độ cứng khi chưa xác định layout.
- **Xác minh đúng tài khoản (Anti-drift sau ca nuôi):** Các tiến trình nuôi (`multi-machine-feed-session`) khi chạy qua máy thường tự động chuyển qua lại giữa các nick (máy 8 slot). Sau khi ca nuôi nhả lock, TikTok có thể đang ở một nick khác (ví dụ máy 21 đang ở `@michekbz8oz` thay vì `@cao.m.phng7`). BẮT BUỘC kiểm tra node username `@<expected_id>` trên màn hình Profile. Nếu sai nick: tap góc trên-trái `(180, 320)` để mở Account Switcher và chọn đúng nick mục tiêu.
- Trước khi thực hiện luồng đổi avatar, BẮT BUỘC dump UI XML (`uiautomator dump`) để xác định layout:
  * Nếu XML có node text `"Sửa hồ sơ"` -> Layout B: Lấy bounds chính xác của node đó để tap (thường `327, 748`).
  * Nếu avatar nằm ở `x > 700` và có text `"Thêm tiểu sử"` -> **Layout C**: Avatar ở góc phải `[708,300][1080,636]`.
  * **Tọa độ tap an toàn trên vòng tròn avatar Layout C:** Tránh nửa trên bị bong bóng Note đè (`y: 258..465`) và tránh góc dưới-phải bị icon badge "Tạo một Nhật ký" đè (`[931,499][1080,636]`). Điểm tap an toàn duy nhất để vào avatar là nửa dưới-trái của vòng tròn: `(x=780, y=520)`.

### 2. Kỷ luật Điều phối Worker khi gặp Layout C (Chống Cạn Ngân sách T1)
- Việc giải quyết layout A/B test không có nút "Sửa hồ sơ" đòi hỏi chuỗi lệnh ADB dò tìm và thử nghiệm. Coordinator tự viết nhiều script tạm sẽ nhanh chóng cạn ngân sách T1 (<= 5 files, <= 200 dòng).
- Khi phát hiện Layout C hoặc layout dị thường: Coordinator BẮT BUỘC dispatch Worker qua `delegate_task`:
  * Khai báo rõ ràng: `TASK_KIND: INVESTIGATE`.
  * Khai báo Fail-fast: `FAIL_FAST: Dừng ngay nếu trong 3 iteration đầu không thể kết nối máy hoặc không mở được Photo Picker`.
  * Khóa máy bằng `with_device_lock.py --machine <N>`.

### 3. Kỷ luật Zoom Crop Vòng tròn Avatar chuẩn theo Layout (Chống Báo cáo Láo)
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

### 4. False-Positive Bút Chì Top-Left & Deep-link Fallback (Bug `TopLeftPencilLayout`)
- **Triệu chứng:** `TopLeftPencilLayout` trong `profile_layouts/top_left_pencil.py` nhận diện nhầm icon "Thêm bạn bè" `[24,96][126,204]` thành bút chì sửa hồ sơ do icon không có `text` hay `desc`, dẫn đến việc tap trượt vào `(75, 150)` và sau đó văng vào bẫy Note bubble (`[AVATAR_UPLOAD_MENU_MISSING]`).
- **Dấu hiệu nhận biết Add Friend:** Node `[24,96][126,204]` luôn đi kèm với button `id/zz5` hoặc `id/pwb` (`[126,96][228,204]`).
- **Cách khắc phục trong code:**
  * Bổ sung điều kiện loại trừ trong `TopLeftPencilLayout.matches()`: `if tree.has_rid("zz5", "pwb") or tree.has_text("thêm bạn", "thêm người", "find friends", "add friends"): return False`.
  * Khi `TopLeftPencilLayout` bị loại trừ, `state_machine.py` kích hoạt fallback deep-link `snssdk1233://profile/edit` của TikTok APAC để mở thẳng màn Sửa hồ sơ.

### 5. Kỷ luật Fix Script khi Coordinator chạm trần T1 (Chống Bại liệt / Trốn việc)
- Khi gặp bug script farm nhưng Coordinator đã chạm trần ngân sách T1 (<= 200 dòng, <= 5 files), **CẤM TUYỆT ĐỐI đứng im báo BLOCKED để đùn việc cho User**.
- BẮT BUỘC lập **Patch Contract O(1)** và dispatch Worker AG Gemini (`ag-gemini-pool-3`) theo chuẩn guard:
  * Khai báo: `TASK_KIND: EDIT`
  * Khai báo file: `FILE: <đường_dẫn_tuyệt_đối>`
  * Khai báo test: `FOCUSED_TEST: python -m pytest <path>::<test_node>`
  * Khai báo anchor: `OLD_STRING:` và `NEW_STRING:` (bắt buộc khác nhau, anchor duy nhất `c == 1` trong file).
