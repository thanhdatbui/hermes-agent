# Xử lý Stale Post-Intent Receipt (POST_SUBMISSION_UNKNOWN) & Chạy bù song song Upload

## 1. Cơ chế lỗi `[POST_SUBMISSION_UNKNOWN]` (COMPAT-POST-VERIFY-004)

### Hiện tượng
- Khi chạy đăng video cho máy (đặc biệt các nick mới `Video Đã Đăng = 0`, chuẩn bị đăng video 1), script ngay lập tức nhảy vào `VERIFY_POST` rồi kết thúc với:
  `[MANUAL_REVIEW] [POST_SUBMISSION_UNKNOWN] post_submission_state=UNKNOWN: không có bằng chứng TikTok ACCEPTED submission; không được ghi workbook hay báo success (COMPAT-POST-VERIFY-004)`
- Không thực hiện các bước `MEDIA_PUSH`, `VIDEO_PICK`, `CAPTION_FILL`, `POST`.

### Nguyên nhân gốc rễ
- File idempotency receipt nằm tại:
  `D:\CodexRuntime\tiktok-video\idempotency\post-attempts\machine_{M}_account_{ACC}_video_{N}.json`
- Một phiên chạy cũ trong quá khứ bị ngắt/crash ở thời điểm tạo barrier trước Post (`status: intent_pending`, `post_submission_state: UNKNOWN`, có `post_intent_at`, nhưng `post_tapped_at: None` - chưa từng bấm Đăng).
- Khi phiên mới chạy:
  1. `state_machine.py` (`_find_pending_post_receipts_for_machine`) tìm thấy receipt pending với `pending_video == cursor` (ví dụ `1 == 1`).
  2. Vì `pending_video == cursor` (chưa bị workbook vượt qua), script không tự đánh dấu `completed` mà ưu tiên recovery receipt, nhảy thẳng sang `VERIFY_POST`.
  3. Tại `VERIFY_POST`, `_post_submission_state_allows_success()` kiểm tra thấy `post_submission_state == UNKNOWN` và có `post_intent_at`, kích hoạt fail-closed an toàn `COMPAT-POST-VERIFY-004` -> dừng `MANUAL_REVIEW`.

### Quy trình xử lý triệt để
1. **Kiểm tra receipt hiện trường**:
   - Mở file `machine_{M}_account_{ACC}_video_{N}.json`.
   - Xác nhận `post_tapped_at` là `null`/`None` và thời gian `post_intent_at` đã cũ (stale, cách xa hiện tại nhiều ngày).
2. **Sao lưu & Archive receipt**:
   - Tạo thư mục backup: `D:\CodexRuntime\tiktok-video\idempotency\post-attempts\backup_stale_intent_<timestamp>`
   - Copy file receipt vào backup.
   - Đổi tên file gốc thành `*.json.bak-stale-intent-<date>` (hoặc di chuyển ra khỏi thư mục `post-attempts`).
3. **Media Fingerprint**:
   - File reservation tại `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\<key>.json` nếu ở trạng thái `reserved` quá `stale_after_seconds` (mặc định 7200s), hệ thống sẽ tự động giải phóng khi phiên mới chạy lại.
4. **Kiểm chứng Canary 1 máy**:
   - Chạy 1 máy trước với `--no-dry-run` để xác nhận script đi đúng luồng `READ_WORKBOOK` -> `MEDIA_PUSH` -> `VIDEO_PICK` -> `CAPTION_FILL` -> `POST` -> `VERIFY_POST` -> `UPDATE_WORKBOOK`.
   - Thu thập ảnh chụp profile verify và kiểm tra `Video Đã Đăng` tăng trong workbook.

---

## 2. Quy tắc Điều phối Chạy Bù Upload: Chạy Song Song (Parallel Mode)

### Kỷ luật vận hành
- **User chỉ thị: "chạy song song"**: Khi có từ 2 máy trở lên cần chạy bù upload, **CẤM chạy tuần tự (sequential)** từng máy vì mỗi máy có timeout từ 360s - 600s, chạy tuần tự sẽ làm kẹt phiên nhiều giờ đồng hồ.
- **Cơ chế song song an toàn**:
  - Dùng Python `threading.Thread` hoặc PowerShell launcher `run_tiktok_upload_batch.ps1` với `-MaxParallel`.
  - **Stagger 2–3 giây** giữa các luồng khi khởi động (stagger launch delay) để tránh xung đột băng thông USB ADB transport khi gọi lệnh đồng thời.
  - Mỗi máy ghi stdout/stderr ra file log độc lập (ví dụ `parallel_machine_{m}.log`).
  - Đặt timeout tối đa (600s) cho mỗi luồng con.
  - Thu thập kết quả đa luồng và báo cáo đồng thời khi tất cả hoàn tất.
