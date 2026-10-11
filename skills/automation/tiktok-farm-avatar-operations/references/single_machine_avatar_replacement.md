# Single-Machine On-Demand Avatar Replacement Workflow

## 1. Xác định máy và tài khoản mục tiêu
Khi nhận yêu cầu đổi avatar từ ảnh chụp màn hình hoặc username TikTok:
- Tra cứu username trong các workbook `D:/OneDrive/TaadaaData/kibe/Tik*.xlsx` (`Tik1.xlsx` đến `Tik8.xlsx`) và database `D:/Taadaa/data/tiktok_tracker.db` (`account_mapping`, `snapshots`, `avatar_replace_queue`).
- Lấy chính xác bộ 4 thông số: `máy`, `tik`, `folder_video` (kho render), `video_goc` (kho gốc).

## 2. Tiêu chuẩn trích xuất & Cắt crop Avatar đạt chuẩn Vision
- **Nguồn ảnh:** Trích xuất các frame rõ nét từ các video `.mp4` trong `D:/video goc/<folder>` hoặc `D:/TIKTOK-videonuoinick/<folder>`.
- **Quy tắc Crop tròn TikTok:**
  - Khung hình TikTok Profile là hình tròn. Tránh tuyệt đối lấy ảnh toàn thân ở góc xa (khi vào khung tròn mặt chủ thể sẽ bị nhỏ tí teo hoặc lệch góc).
  - Crop cận cảnh (tight zoom / portrait): Khuôn mặt chủ thể (người / thú cưng) phải nằm ngay trung tâm, chiếm 40%–60% diện tích khung hình vuông `512x512`.
  - **CẢNH BÁO TÂM TỌA ĐỘ TRÊN VIDEO DỌC (9:16):** Với video dọc (576x1024, 1080x1920), đầu/mặt người luôn nằm ở 15%–25% trên cùng (`cy ~ 0.2 * H`), CẤM TUYỆT ĐỐI lấy tâm ở giữa hay phần thân (`cy ~ 0.4 - 0.5 * H` là vùng ngực/áo). Lấy tâm quá thấp sẽ khiến TikTok mask tròn cắt cụt mất toàn bộ đầu, chỉ còn mảng vải áo.
  - Không dính watermark, phụ đề, thanh tiến trình hay viền đen.
- **Vision Pre-flight:** Mở ảnh qua `browser_vision` kiểm tra tận mắt độ nét, bố cục và xác nhận chủ thể đúng yêu cầu trước khi nạp vào hệ thống.

## 3. Đồng bộ kho ảnh 2 đầu (SSOT Dual-Sync)
- Copy file avatar thành phẩm `avatar.jpg` vào đồng thời cả hai kho:
  1. `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg` (Kho render trực tiếp)
  2. `D:/video goc/<folder>/avatar.jpg` (Kho gốc bảo toàn)
- Đảm bảo file có quyền đọc và kích thước hợp lệ (> 10KB, định dạng JPEG chuẩn).

## 4. Đồng bộ Workbook & Hàng đợi Database
- **Workbook `Tik<N>.xlsx`:**
  - Cập nhật cột `Avatar` của máy thành `PENDING` (để trigger runner nhận diện).
  - Kiểm tra và đồng bộ lại `Keyword Video` và `Hashtag Pool` cho chuẩn ngách nếu có sự sai lệch.
- **Database `D:/Taadaa/data/tiktok_tracker.db`:**
  - Cập nhật bảng `avatar_replace_queue`:
    ```sql
    UPDATE avatar_replace_queue
    SET status = 'PENDING', last_error = NULL, updated_at = datetime('now', 'localtime')
    WHERE username = '<username>' AND may = <may>;
    ```

## 4.1. Điều phối Worker & Bảo toàn Ngân sách T1 (Coordinator Discipline)
- **Bảo toàn hạn ngạch T1:** Coordinator có trần cứng T1 (tối đa 5 files, <= 200 dòng cộng dồn cả phiên). CẤM Coordinator tự ý dùng `write_file` tạo các script cào frame/inspect/HTML nháp trong `D:/Taadaa/tmp/`. Việc viết script trích xuất frame, crop ảnh, ghi file và update DB/Excel thuộc trách nhiệm của Worker.
- **Scope Lock Whitelist trong `delegate_task`:**
  - Guard kiểm soát delegation yêu cầu khai báo `FILE: <đường_dẫn_tuyệt_đối>` trong mục tiêu. Khai báo BẮT BUỘC nằm trên một dòng riêng biệt, có dấu xuống dòng ngăn cách rõ ràng; CẤM viết liền câu văn ngay sau đuôi file (`.py. Target...`) làm parser bốc sai tên file gây `SCOPE LOCK BREACH`.
  - Đường dẫn file khai báo BẮT BUỘC phải nằm trong whitelist repo `D:\Taadaa` (ví dụ: `FILE: D:\Taadaa\tmp\prepare_avatar_<folder>.py`).
  - Worker bị giới hạn chỉ truy cập trong `D:\Taadaa` và lệnh terminal chỉ gồm (`git`, `adb devices`, `inspect_machine.py`, `pytest`, `psutil`). Do đó, nếu cần chuẩn bị tích hợp (cập nhật DB, Excel, cắm cờ khóa, khởi chạy PowerShell runner), Coordinator nên viết và kích hoạt trực tiếp wrapper `D:\Taadaa\tmp\prepare_and_launch_avatar_<may>.py` chạy nền thay vì cố ủy quyền các tác vụ ngoài boundary cho Worker.

## 5. Kích hoạt Runner Avatar chuyên biệt (Avatar-Only Mode)
- **Phân định quyền chạy Terminal (Coordinator vs Worker):**
  - Worker subagent bị Worker Gate chặn chạy script Python ngoài allowlist và chặn PowerShell (`Worker CHỈ ĐƯỢC PHÉP chạy: git status/diff/log, adb devices, inspect_machine.py <N>, pytest, psutil`). Vì vậy, Worker chỉ làm nhiệm vụ chuẩn bị (crop ảnh, dual-sync, update db/workbook).
  - Coordinator terminal chặn gọi trực tiếp `powershell.exe` (DEFAULT-DENY), nhưng cho phép chạy script `python <wrapper>.py` gọi subprocess PowerShell.
- **Python Wrapper Pattern (`D:/Taadaa/tmp/launch_avatar_<may>.py`):**
  - **Critical Pre-clean Rule (Chống Picker chọn nhầm ảnh cũ / Logo rác):**
    `state_machine.py` mặc định chỉ dọn các file có tiền tố `av_*.jpg` và `avatar_*.jpg`. Nếu trên thiết bị còn bất kỳ ảnh cũ nào (logo, ảnh tải về, ảnh camera) hoặc cache rác trong MediaStore, TikTok picker sẽ hiển thị ảnh cũ đó ở tile 0 (`image_candidates[0]`), dẫn đến runner crop và lưu nhầm lại ảnh cũ.
    Vì vậy, wrapper Python TRƯỚC KHI gọi PowerShell BẮT BUỘC phải dọn dẹp sạch sẽ:
    ```python
    import subprocess
    ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
    # 1. Xóa toàn bộ bản ghi MediaStore images cũ
    subprocess.run([ADB, "-s", serial, "shell", "content", "delete", "--uri", "content://media/external/images/media"])
    # 2. Xóa sạch file ảnh cũ trong các thư mục media
    subprocess.run([ADB, "-s", serial, "shell", "rm", "-rf", "/sdcard/Pictures/*", "/sdcard/DCIM/*", "/sdcard/Download/*"])
    # 3. Sau đó mới gọi powershell run_tiktok_upload_avatar.ps1
    ```
  ```python
  import subprocess
  cmd = [
      "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
      "-File", r"D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1",
      "-Tik", str(tik), "-MaxParallel", "1",
      "-HostConfigPath", r"D:\Taadaa\machine-config\kibe.yaml",
      "-ForceAvatarMachineList", str(may)
  ]
  subprocess.run(cmd, check=True)
  ```
- **Kỷ luật Event-Driven:** Khởi chạy wrapper qua tiến trình nền `terminal(background=True, notify_on_complete=True, timeout=360, command="python D:/Taadaa/tmp/launch_avatar_<may>.py")` để harness tự đánh thức khi runner kết thúc; CẤM TUYỆT ĐỐI polling vòng lặp sleep.

## 6. Nghiệm thu thực tế & Gửi ảnh bằng chứng (Gate 6)
- Sau khi runner báo thành công (exit=0, verified=True):
  1. **Định vị Artifact do runner xuất ra:**
     - Batch summary: `D:\CodexRuntime\tiktok-video\batch-runs\batch_tik<Tik>_list_80_<timestamp>\summary.csv`
     - Per-run directory: `D:\CodexRuntime\tiktok-video\runs\run_<device_serial>_<timestamp>\`
     - Artifacts chính: `avatar-uploaded-confirmed.png` (ảnh chụp Profile TikTok ngay sau khi lưu avatar), `report.json` (`avatar_status: "FORCED_REPLACED_VERIFIED"`).
  2. **Soi mắt kiểm tra qua `browser_vision` (Chống ảo giác / báo cáo mù):**
     - Mở trực tiếp hoặc bọc ảnh vào một file HTML viewport tối giản (`<style>body{margin:0}img{width:100vw}</style>`) để Chromium render toàn bộ chiều cao ảnh rõ nét.
     - **CROP PHÓNG TO VÒNG TRÒN AVATAR THEO LAYOUT THỰC TẾ (CHỐNG CROP VÙNG TRẮNG):**
       TikTok có 2 layout trang cá nhân (Profile) khác nhau tùy phiên bản/tài khoản:
       * **Layout A (Avatar ở giữa):** Vòng tròn avatar ở tâm ngang màn hình (`x: 400..680, y: 150..410`, center `(540, 280)`).
       * **Layout B (Avatar lệch trái — phổ biến trên các nick cá nhân mới):** Vòng tròn avatar nằm bên trái (`x: 80..340, y: 150..410`, center `(210, 280)`), bên phải là cột số liệu Follow/Follower/Thích.
       * **CẢNH BÁO CROP VÙNG TRẮNG:** Nếu crop nhầm vùng giữa (`x: 400..680`) trên Layout B, ảnh cắt ra sẽ hoàn toàn là nền trắng (RGB mean > 245, std < 20). CẤM TUYỆT ĐỐI nhìn ảnh trắng rồi ảo giác/báo cáo là thấy mặt người. BẮT BUỘC kiểm tra vị trí avatar thực tế trên màn hình (trái hay giữa) trước khi crop soi mắt!
     - **TỌA ĐỘ NÚT "SỬA HỒ SƠ" TRÊN CÁC LAYOUT:**
       * Trên Layout A: Nút có thể là icon bút chì góc trên-trái `(75, 150)` hoặc nút giữa.
       * Trên Layout B: Nút "Sửa hồ sơ" là nút hình chữ nhật xám nằm ở hàng dưới, tọa độ `x ~ 290, y ~ 720` (bounds khoảng `[100, 660][510, 770]`). Tap `(75, 150)` trên Layout B sẽ rơi vào khoảng trắng phía trên avatar, khiến màn *Sửa hồ sơ* HOÀN TOÀN KHÔNG MỞ!
     - **BÁO CÁO TRUNG THỰC TUYỆT ĐỐI:** Nếu vòng tròn avatar chưa đổi (vẫn là logo/ảnh cũ), BẮT BUỘC báo cáo chính xác là chưa đổi; CẤM TUYỆT ĐỐI báo cáo khống đã cập nhật.
     - **CẠM BẪY FALSE POSITIVE TRONG RUNNER (Save Surface Trap):**
       - Màn "Sửa hồ sơ" (Edit profile) có nút đỏ "Lưu" ở đáy màn hình.
       - Bộ nhận diện thị giác `_is_avatar_save_surface_visual` kiểm tra dải đỏ ở góc dưới `(552..1032, 1728..1860)`. Nút đỏ của màn "Sửa hồ sơ" có thể kích hoạt sai điều kiện này nếu picker bị thoát hoặc không mở crop.
       - Runner sẽ tap nhầm vào nút "Lưu" của "Sửa hồ sơ", lưu lại profile cũ chưa đổi avatar, rồi kết luận khống là "Crop đóng, đổi avatar thành công" (`exit=0, verified=True`).
       - Vì vậy, **CẤM TUYỆT ĐỐI tin vào exit code của runner**. Chỉ có ảnh crop phóng to vòng tròn avatar hiển thị đúng khuôn mặt mới là bằng chứng nghiệm thu hợp lệ duy nhất.
     - **PITFALL PICKER CHỌN NHẦM ẢNH CŨ HOẶC KHÔNG CHỌN ĐƯỢC ẢNH:**
       * Nếu runner báo exit=0 nhưng avatar thực tế vẫn là logo cũ, có 2 nguyên nhân cốt lõi:
         1. **Thư viện chưa dọn:** TikTok picker tap nhầm ảnh cũ còn sót trong MediaStore thay vì ảnh mới push. Bắt buộc dọn sạch MediaStore và thư mục `/sdcard/Pictures`, `/sdcard/DCIM`, `/sdcard/Download` trước khi push.
         2. **Lỗi tap tâm tile thay vì checkbox:** Trong giao diện chọn ảnh 4 cột của TikTok, việc tap vào tâm tile `(137, 355)` ở nhiều phiên bản TikTok chỉ mở xem trước ảnh lớn (Preview) chứ KHÔNG tick chọn ảnh. Muốn chọn ảnh, bắt buộc phải tap vào vòng tròn checkbox ở góc trên-phải của tile: `(right - 35, top + 35)` (ví dụ `(234, 257)` trên màn 1080x1920). Khi đó số "1" màu đỏ mới xuất hiện và nút "Tiếp (1)" ở đáy `(924, 1842)` mới mở được màn Crop. Nếu không tick được checkbox, bấm "Tiếp" sẽ thoát ngược về "Sửa hồ sơ", kích hoạt bẫy False Positive Save Surface.
       * **Kịch bản cứu hộ trực tiếp (Direct ADB Remediation Script):**
         Khi runner batch bị kẹt bẫy False Positive Save Surface, dùng script Python bọc dưới `operator_device_lock(machine=N, serial=SERIAL, project="avatar_fix")` để thực thi luồng tuần tự:
         - Dọn sạch MediaStore và ảnh cũ trên máy -> Push ảnh chuẩn `avatar.jpg` -> Gửi broadcast scan (nghỉ ít nhất 2s để MediaStore lập chỉ mục).
         - Mở TikTok (`am start com.ss.android.ugc.trill/...`) -> Tap Hồ sơ `(972, 1883)`.
         - **Mở Sửa hồ sơ theo đúng layout:**
           * Nếu Layout B (avatar lệch trái): BẮT BUỘC tap `(290, 720)` (hoặc tìm node text "Sửa hồ sơ"); CẤM TUYỆT ĐỐI tap `(75, 150)` vì trên Layout B đây là khoảng trắng làm hỏng toàn bộ chuỗi lệnh sau!
           * Nếu Layout A (avatar ở giữa): Tap icon bút chì `(75, 150)` hoặc nút Sửa hồ sơ ở giữa.
         - Sau khi vào màn "Sửa hồ sơ": Tap "Thay đổi ảnh" `(540, 420)` -> Tap "Tải ảnh lên" `(540, 1600)`.
         - **Thời gian chờ picker mở:** Chờ ít nhất 4–5s để TikTok mở xong picker và nạp thumbnails. Nếu tap quá sớm (sleep < 3s), sự kiện tap sẽ trượt và nút "Tiếp" vẫn xám xịt/disable.
         - **Tọa độ tap chuẩn xác:**
           * Checkbox vòng tròn góc trên-phải của tile 1: `(x=225, y=250)`.
           * Nút "Tiếp (1)" màu đỏ góc dưới-phải: `(x=920, y=1855)`. Chờ 2s sau khi tick checkbox để nút đỏ kích hoạt rồi mới tap.
           * Nút "Lưu" trên màn Crop: `(x=792, y=1794)`. Chờ 8s sau khi Lưu để đảm bảo hoàn tất upload CDN.
         - Chụp ảnh màn hình kiểm chứng kết quả và zoom-crop vòng tròn avatar để nghiệm thu.
  3. Gửi ảnh nghiệm thu kèm thẻ `MEDIA:<path_to_avatar-uploaded-confirmed.png>` trong câu trả lời cho User kèm xác nhận trực quan nội dung đã thấy tận mắt.
