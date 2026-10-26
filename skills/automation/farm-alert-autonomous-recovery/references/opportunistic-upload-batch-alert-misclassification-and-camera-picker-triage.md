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
1. **Bẫy nạp APK dở dang qua ADB LAN:** Khi chạy script nâng cấp hàng loạt (như `upgrade_8w.py`) qua socket từ xa (`192.168.110.119:5037`), việc đẩy 60 file split APK (~280MB/máy) đồng thời trên nhiều luồng dễ gây nghẽn bus hoặc timeout. Thực tế chỉ có 18 máy đuôi (M260-M280) nâng cấp thành công lên v47.0.3, trong khi các máy từ M201 đến M259 vẫn kẹt ở v46.6.3 hoặc thất bại khi cài.
2. **Lỗi logic Camera Mode Thumbnail Tap (Nguyên nhân thực sự):**
   - Kể cả trên các máy đã có v47.0.3 (ví dụ M202, M203), khi script bấm nút Tạo (`+`), TikTok không mở thẳng Thư viện ảnh/video mà mở giao diện **Camera** (`[CAMERA_MODE]`).
   - Trên màn hình Camera, script cần bấm vào ô thumbnail **"Tải lên"** (Upload) ở góc dưới để mở gallery chọn video. Script sử dụng tọa độ cố định (ví dụ `(156, 1574)`):
     `Camera surface still visible after tap (1/4); retrying thumbnail tap at (156, 1574)`
   - Do lệch tọa độ UI trên bản TikTok mới, hoặc do Camera mode đang hiển thị popup quyền/dialog che khuất, cả 4 lần tap thumbnail đều không mở được gallery picker.
   - Khi hết lượt thử, state machine lùi lại tìm nút điều hướng đáy `+` để phục hồi (`_find_bounded_create_button`). Nhưng vì màn hình vẫn đang ở Camera mode (vốn không có thanh điều hướng đáy hay nút `+`), hàm tìm kiếm trả về `None`, dẫn đến chốt lỗi fail-closed:
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
- Nếu thấy lặp lại `Camera surface still visible after tap... retrying thumbnail tap`:
  - Cập nhật selector động hoặc kiểm tra bounds của nút "Tải lên" trong dump XML của Camera mode thay vì dùng toạ độ hardcode mù `(156, 1574)`.
  - Bổ sung cơ chế dismiss các popup/overlay trong Camera mode trước khi tap thumbnail.
