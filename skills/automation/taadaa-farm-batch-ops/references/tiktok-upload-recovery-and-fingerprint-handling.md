# Quy Tắc Xử Lý Recovery UI Upload & Quản Lý Fingerprint (2026-08-26)

## 1. Bản chất sự cố chạy đè Batch Upload khi Feed chưa dứt điểm
- **Hiện tượng:** Khi nhịp chạy vét cuối của Phiên 3 (`row-1-231528` / `row-1-001531`) vẫn đang lướt feed muộn trên một số máy, việc kích hoạt `run_tiktok_upload_batch.ps1` chạy song song sẽ làm 2 luồng cùng tương tác trên 1 thiết bị:
  - Luồng Feed đang cố điều hướng về Home / Profile (`tap_home` / `tap_profile`).
  - Luồng Upload mở app, đẩy file video MP4 và cố vào picker.
- **Hậu quả:** Gây văng focus TikTok ra màn hình chính (`TikTok focus lost`), mở nhầm màn hình Camera/Media Picker (`camera_creation_overlay`) và kích hoạt Farm Alerts giả mạo.

## 2. Quy trình Recovery Upload chuẩn qua Script
Khi cần xử lý (fix) các máy bị lỗi UI / kẹt màn hình / mất focus:
1. **Kiểm tra trạng thái Feed:** Bắt buộc xác nhận toàn bộ worker của feed session đã kết thúc hoàn toàn.
2. **Khởi chạy Recovery Mode bằng Script Canonical (CẤM SỬA TAY):**
   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_batch.ps1" -Tik <N> -Confirmation RUN -RecoveryMode -AllowDeviceRebootRecovery
   ```
   - Cờ `-RecoveryMode`: Tự động nhận diện các máy chưa `post_verified` và thử lại đúng video tiếp theo.
   - Cờ `-AllowDeviceRebootRecovery`: Tự động soft-reboot app/thiết bị khi gặp kẹt UI/ATX session.
3. **Bỏ qua máy Offline:** Bỏ qua các máy mất kết nối ADB / USB cáp (`61, 62, 63, 74`) và các máy trống nick (`75, 77, 78, 79, 80`).
4. **Xử lý Media Fingerprint Pending & Tránh chạy đè:**
   - Nếu worker bị crash/kill để lại file `reserved` trong `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\<key>.json`, script recovery sẽ tự động giải phóng các reservation của worker chết nếu quá stale timeout hoặc dọn dẹp trước khi thử lại.
5. **Nguyên tắc Encode Code:** Mọi bản vá logic trong quá trình recovery (decouple timeout budget, fallback import popup handlers, location dialog dismissals) phải được commit và review APPROVED lên Git codebase trước khi triển khai, không chạy tay tùy tiện.

## 3. Chẩn đoán & Xử lý lỗi `POST_SUBMISSION_UNKNOWN` do Stale Post Receipt
- **Triệu chứng:** Máy báo lỗi `[MANUAL_REVIEW] [POST_SUBMISSION_UNKNOWN] post_submission_state=UNKNOWN: không có bằng chứng TikTok ACCEPTED submission; không được ghi workbook hay báo success (COMPAT-POST-VERIFY-004)`.
- **Cơ chế gốc:**
  - File receipt tại `D:\CodexRuntime\tiktok-video\idempotency\post-attempts\machine_<M>_account_<acc>_video_<N>.json` được tạo từ run cũ trước đó bị crash/kill ở trạng thái `status: "intent_pending"`.
  - Receipt có `post_intent_at` nhưng `post_tapped_at: None` (thực tế chưa từng bấm nút Đăng trên TikTok).
  - Khi tài khoản chưa từng đăng video nào (`Video Đã Đăng = 0`), cursor video = 1. Vì `pending_video == cursor == 1`, state machine KHÔNG tự động đánh dấu completed (vốn chỉ dọn khi `pending_video < cursor`), mà ưu tiên recovery và nhảy thẳng vào `VERIFY_POST`.
  - Tại `VERIFY_POST`, guard `COMPAT-POST-VERIFY-004` kiểm tra `post_submission_state == UNKNOWN` và lập tức fail-closed chuyển sang `MANUAL_REVIEW` để chống ghi nhận khống workbook, khiến máy bị kẹt vĩnh viễn ở các lần chạy sau.
- **Quy trình gỡ kẹt an toàn (Idempotency Reconcile):**
  1. **Đối soát hiện trường profile:** Kiểm tra profile nick trên thiết bị thật (qua screencap hoặc log `PROFILE_GRID scan`) để chứng minh số video trên profile là 0 (chưa từng đăng thành công).
  2. **Kiểm tra receipt:** Đảm bảo `post_tapped_at is None` và timestamp `post_intent_at` đã cũ (vượt quá nhiều giờ/ngày).
  3. **Sao lưu & Archive receipt:** Tạo thư mục backup an toàn và rename receipt cũ thành `.json.bak-stale-intent-<timestamp>` (theo đúng tiền lệ `machine_74_video_7.json.bak-false-complete-20260812` trong tài liệu compatibility registry).
  4. **Kiểm tra Media Fingerprint:** Đảm bảo reservation tương ứng trong `idempotency/media-fingerprints/` đã hết hạn (> 4h `stale_after_seconds` sẽ tự giải phóng theo `media_fingerprint.py`).
  5. **Re-run:** Chạy lại upload (bắt đầu bằng Canary 1 máy), target sẽ sạch barrier idempotency và tiến hành đẩy media, pick video và đăng bình thường.

## 4. Kỷ Luật Chạy Bù Upload Nhiều Máy: BẮT BUỘC CHẠY SONG SONG (Parallel Mode)
- **CẤM TUYỆT ĐỐI chạy tuần tự (Sequential Loop):**
  - Một flow upload TikTok hoàn chỉnh (ADB connect -> khởi động app -> chờ feed -> chuyển đổi tài khoản Switcher -> đẩy video -> chọn video trong gallery -> điền caption -> bấm Post -> xác minh màn hình published -> quét Profile grid scan) tốn trung bình **350s – 420s (6 - 7 phút/máy)**.
  - Chạy tuần tự 5 máy sẽ mất tới hơn 30 phút, đồng thời dễ dính lỗi timeout subprocess chém ngang khi máy đang ở pha nhạy cảm (vừa bấm Post đang đợi profile tile).
- **Quy chuẩn Chạy Song Song (Parallel Execution Standard):**
  - Khởi chạy đồng thời tất cả các máy cần bù bằng multi-threading hoặc multi-process (`subprocess.Popen` song song).
  - **Stagger khởi động:** Cài đặt khoảng cách khởi động giữa các máy là **2 - 3 giây** (`stagger = 3.0s`) để chống đột biến lệnh (fork storm) gây nghẽn ADB daemon và transport socket trên hub USB.
  - **Timeout budget:** Cấp timeout độc lập tối thiểu **600s (10 phút)** cho mỗi worker để đảm bảo máy có đủ thời gian transcode video và quét đối soát profile tile.
  - Toàn bộ nhóm máy (ví dụ 5 máy) sẽ hoàn tất đồng thời chỉ trong 6 - 7 phút.

## 5. Xử Lý Máy Đã Post Thành Công Nhưng Kẹt Lặp Quét Profile Tile
- **Hiện tượng (như M28):** Máy đã bấm Post thành công, đã có ảnh `post-published-surface.png`, receipt ghi nhận `post_submission_state = ACCEPTED`, nhưng bước `VERIFY_POST` bị kẹt lặp quét tile profile (do grid TikTok delay hiển thị hoặc tài khoản trước đó có số tile khác khiến `current_scan < baseline`).
- **Quy trình nghiệm thu dứt điểm:**
  1. Kiểm tra bằng chứng thực tế: Nếu `post-published-surface.png` đã ghi nhận bài đăng xuất hiện và receipt mang `post_submission_accepted = true`.
  2. Đồng bộ workbook: Cập nhật tăng `Video Đã Đăng` tương ứng trong workbook `Tik<N>.xlsx`.
  3. Đóng receipt & fingerprint: Đánh dấu receipt sang `status = "completed"` và media fingerprint sang `status = "verified_success"` để tránh chạy lại đè bài.


