# Pitfall: Hard Outer Watchdog Deadline & Upload Queue Bottleneck (2026-08-27)

## 1. Triệu Chứng & Hiện Tượng Hàng Loạt (Mass Failure)
- Telegram alert báo hàng loạt máy (hơn 40 máy trong một phiên) cùng bị dừng với lý do:
  `hard outer watchdog timeout exceeded (75.0m > 75.0m)` (hoặc `75.1m`, `75.2m`).
- Màn hình chụp hiện trường báo về: Máy đang ở Homescreen sạch sẽ, TikTok đã đóng, không có popup chặn hay đơ lag.
- Log chi tiết từng máy (`log.jsonl`): Phần lướt feed đã hoàn thành `success` 10/10 video, profile verified, cleanup đã chạy xong, nhưng bước `upload-hook` (bước cuối ca) bị kẹt hàng đợi hoặc timeout.

## 2. Nguyên Nhân Thiết Kế (Design Flaws)

### Flaw 1: Nhầm lẫn Per-Worker Budget thành Batch Global Deadline
- Budget 1 worker máy đơn lẻ: `Feed (35m) + Follow (15m) + Upload (20m) + 5m buffer = 75.0m`.
- Trong `multi_machine_feed_session.py`, `hard_deadline = time.monotonic() + worker_hard_timeout` được tính một lần duy nhất tại thời điểm bắt đầu batch.
- Khi tổng thời gian của cả phiên vượt mốc 75 phút (do máy khởi động so le, hoặc xếp hàng nối tiếp), watchdog của batch quét `now_mono >= hard_deadline` và ép dừng (abort/cancel) toàn bộ các máy còn đang chạy, dù các máy đó chưa hề dùng hết 75 phút thực tế của riêng mình.

### Flaw 2: Nghẽn Hàng Đợi Upload Hook (`DEFAULT_UPLOAD_MAX_CONCURRENCY = 16`)
- Khi 57–74 máy cùng lúc hoàn thành feed session sau ~25–30 phút, toàn bộ đàn máy đồng loạt nhảy vào `_run_upload_hook`.
- Vì giới hạn 16 slots (`_UploadConcurrencyLease`), các máy thuộc đợt 2, 3, 4 (từ máy 17 trở đi) phải nằm chờ trong hàng đợi.
- Thời gian chờ hàng đợi cộng với thời gian chạy upload khiến thời gian tổng vượt quá 75 phút của batch deadline, dẫn đến 40+ máy bị cancel đồng loạt.

## 3. Nguyên Tắc & Quy Chuẩn Khắc Phục (Best Practices)
1. **Per-Worker Deadline độc lập**:
   - Mỗi worker phải có `deadline_mono = start_mono + worker_budget` riêng tính từ thời điểm worker đó thực sự bắt đầu chạy (`_timing["start_mono"]`), không dùng chung `hard_deadline` tính từ lúc submit batch.
2. **Không biến lỗi Upload Hook thành lỗi sập Feed Session**:
   - Nếu Feed session đã hoàn tất `success`, `final_status` của máy PHẢI giữ là `success` (hoặc `degraded` nếu có cảnh báo), kết quả upload chỉ ghi nhận vào `upload_result.json` dạng `timeout`/`skipped`.
   - CẤM đánh rớt máy thành `failed` và CẤM kích hoạt lock hiện trường 2h nếu nguyên nhân chỉ do nghẽn hàng đợi upload.
3. **Queue Wait Timeout Isolation**:
   - Timeout khi chờ lock trong `_UploadConcurrencyLease` phải được bắt và xử lý êm (graceful timeout skip), không để exception văng ra ngoài làm sập worker runner.
