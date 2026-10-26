# Opportunistic Upload Batch Alert Misclassification & Camera Mode Gallery Picker Triage

## 1. Triệu Chứng & Bản Chất Sự Cố (Symptom & Alert Anatomy)
- **Cảnh báo Telegram hiển thị sai quy trình:**
  ```text
  🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM ADMIN - MÁY 201-280】
  • Quy trình / Script: Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)
  • Quy mô batch: 78 máy | Thành công: 0 | Thất bại: 78
  • Tổng tỷ lệ thất bại toàn batch: 100.0% (78/78 máy)
  ❌ Signature: UploadScriptError:UploadHook: [MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control
  ```
- **Nghịch lý hiện trường:**
  - Ca nuôi lướt feed thực tế đã hoàn thành 100% (mỗi máy lướt đủ 15–20 video, tài khoản và phiên an toàn, không có lỗi nuôi).
  - Nhưng cảnh báo lại báo 100% máy thất bại và gắn nhãn quy trình là "Nuôi Acc / Lướt Feed".

## 2. Nguyên Nhân Kỹ Thuật Gốc (Root Cause Analysis)

### A. Cơ Chế Lồng Ghép (Opportunistic Upload) & Bẫy Gom Lỗi Của Batch Aggregator
1. **Lồng ghép upload vào feed runner:** `scripts/run-feed-session.ps1` được khởi chạy với cờ `-AllowUploadHook`. Khi mỗi máy hoàn tất lướt feed, `_run_upload_hook()` trong `multi_machine_feed_session.py` lập tức gọi subprocess sang `Tiktok-video` để đăng video và ghi kết quả vào:
   `<artifact_root>/machines/machine_<id>/<timestamp>/upload_result.json`
2. **Batch Aggregator đánh giá hỗn hợp:** Cuối phiên chạy của `run-feed-session.ps1`, script gọi:
   `& $Python -m automation_core.batch_aggregator "$targetBatchDir" --telegram`
3. **Gán nhãn sai phạm vi:** `batch_aggregator.py` duyệt thư mục artifact của ca nuôi (`multi_machine_summary`), đọc thấy `upload_result.json` có `status: failed`, liền tạo `MachineResult(error_type='UploadScriptError', error_message='UploadHook: ...')`. Vì thư mục được truyền vào là của ca nuôi, `script_name` mặc định được phân giải thành `tiktok-luot nuoi acc`.
4. Khi 70+ máy fail upload hook, `batch_aggregator` kích hoạt cảnh báo hệ thống vượt ngưỡng kép (rate >= 10% & count >= 3), phát thông báo Telegram giật gân làm người vận hành hiểu nhầm ca nuôi bị sập 100%.

### B. Tại Sao Nâng Cấp APK Không Triệt Tiêu Được Lỗi `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`
1. **Bẫy nạp APK dở dang qua ADB LAN vs Giải pháp Local Admin OneDrive Push:**
   - Khi chạy script nâng cấp hàng loạt (như `upgrade_8w.py`) qua socket ADB LAN từ xa (`192.168.110.119:5037`), việc stream 60 file split APK (~280MB/máy × 78 máy = ~22GB) qua socket mạng nội bộ làm nghẽn bus và timeout hàng loạt (khiến hơn 50 máy từ M201 đến M259 fail).
   - **Quy chuẩn Local Push không qua LAN:** Thư mục APK đã được OneDrive đồng bộ sẵn trên máy chủ Admin tại `D:\OneDrive\apk-bank\com_ss_android_ugc_trill`. BẮT BUỘC thực thi script nâng cấp trực tiếp trên host Admin qua `admin_ssh.py`, sử dụng ADB cục bộ `C:\Program Files (x86)\xiaowei\tools\adb.exe` để nạp thẳng qua các cổng USB vật lý kết nối với điện thoại, loại bỏ 100% nghẽn mạng LAN.
   - **Bẫy OneDrive Files On-Demand & Windows cp1252:**
     * File script mới tạo trong thư mục OneDrive của Admin có thể ở trạng thái Cloud-Only (dung lượng có dấu ngoặc `(size)` trong `dir`), khiến Python ném `[Errno 22] Invalid argument`. Khắc phục: Dùng PowerShell hydrate sang thư mục local ngoài OneDrive: `Get-Content ... -Raw | Set-Content D:\Taadaa\tools\<script>.py`.
     * Console Windows của OpenSSH mặc định dùng `cp1252`, in chữ Tiếng Việt có dấu (như "KẾT QUẢ") sẽ văng `UnicodeEncodeError`. BẮT BUỘC chạy với `python -X utf8` hoặc giữ output log thuần ASCII.
2. **Lỗi logic Camera Mode Gallery Thumbnail Tap (Nguyên nhân thực sự được xác nhận qua `browser_vision`):**
   - Kể cả trên các máy đã có v47.0.3 (ví dụ M202, M203), khi script bấm nút Tạo (`+`), TikTok mở giao diện **Camera** (`[CAMERA_MODE]`).
   - **Bố cục thực tế của TikTok Camera (soi mắt kiểm chứng trên `video-pick-camera-surface.png`):**
     * Góc dưới bên **TRÁI** (`x≈156, y≈1574`): Nút **"Hiệu ứng"** (Effects).
     * Chính giữa đáy: Nút tròn đỏ Quay/Chụp (Shutter).
     * Góc dưới bên **PHẢI** (`x≈930, y≈1650`): Mới là nút **"Tải lên"** (có icon album ảnh và chữ "Tải lên").
   - **Lỗ hổng trong code (`state_machine.py` dòng 9658):**
     * `ordered_candidates = left_targets + right_targets` (do tàn dư của Case 90).
     * Vì icon "Hiệu ứng" bên trái có màu sắc nổi bật (`non_dark_l >= 0.20`), thuật toán luôn đưa `left_targets` lên đầu và tap cố định 4 lần liên tiếp vào tọa độ `(156, 1574)` (bấm trúng nút **Hiệu ứng** thay vì nút "Tải lên").
     * Gallery picker không bao giờ mở ra được. Khi hết lượt retry, state machine lùi lại tìm nút điều hướng đáy `+` để phục hồi (`_find_bounded_create_button`). Nhưng vì màn hình vẫn ở Camera mode (không có nút `+`), code trả về `None`, dẫn đến chốt lỗi fail-closed:
       `[MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control`.

## 3. Quy Trình Chẩn Đoán & Khắc Phục O(1)

### Bước 1: Phân Lập Ngay Hiện Trường (Isolate Feed vs Upload)
- Khi nhận batch alert có chữ ký `UploadScriptError:UploadHook`:
  - Khẳng định ngay với Operator: **Ca nuôi hoàn toàn bình thường, đây là lỗi của khâu đăng video (Upload Hook)**.
  - Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` để xác nhận thiết bị đã về `LauncherActivity` và màn hình `OFF (Sleep/Dozing)`.

### Bước 2: Tách Rời Hoặc Kiểm Soát Hook Upload Trong Ca Nuôi
- Nếu ca nuôi không yêu cầu đăng video: Bỏ cờ `-AllowUploadHook` trong lệnh spawn của `tiktok_runner.py` để ca nuôi chạy thuần túy, tránh rác log và báo động giả.
- Trong `batch_aggregator.py`: Phân tách rành mạch lỗi feed (`multi_machine_summary`) và lỗi upload (`upload_result.json`), không để lỗi upload hook đánh trượt toàn bộ batch của ca nuôi.

### Bước 3: Sửa Lỗi Camera Mode Gallery Thumbnail Trong `Tiktok-video`
- Kiểm tra `execution.log` trong thư mục run trên máy Admin (`D:\CodexRuntime\tiktok-video\runs\...`).
- Nếu thấy lặp lại `Camera surface still visible after tap... retrying thumbnail tap at (156, 1574)`:
  - Trong `state_machine.py` (`_tap_visual_camera_upload_entry`): Đổi thứ tự ưu tiên sang `ordered_candidates = right_targets + left_targets` để luôn ưu tiên tap nút **"Tải lên"** ở góc phải (`x≈930, y≈1650`).
  - Đảm bảo trong vòng lặp retry, nếu candidate hiện tại không mở được gallery picker thì chuyển sang candidate tiếp theo (`ordered_candidates[target_idx]`) thay vì lặp lại cùng một tọa độ trượt.
