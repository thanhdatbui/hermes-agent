# Post Idempotency Recovery & Media Fingerprint Ledger

## 1. Context & Problem
Khi chạy batch upload TikTok trên Phone Farm (repo `D:\Taadaa\Tiktok-video`), các lần retry hoặc re-run sau sự cố có thể gặp 2 lớp bảo vệ idempotency:
1. **Post Intent / Attempt Receipt Barrier**: `idempotency/post-attempts/machine_<M>_account_<A>_video_<V>.json`.
2. **Media Fingerprint Ledger**: `idempotency/media-fingerprints/<hash_key>.json`.

Nếu xử lý không đúng ở 2 lớp này, runner sẽ crash với `upload_subprocess_nonzero` hoặc fail closed với `MEDIA_FINGERPRINT_PENDING`.

---

## 2. Post Attempt Receipt & Safe Auto-Recovery

### Triệu chứng lỗi (Crash non-zero exit):
```text
RuntimeError: Post tap already recorded for this machine/video; refusing duplicate post tap to avoid double-posting
```
Gây sập subprocess Python với exit code khác 0 (`upload_subprocess_nonzero`).

### Quy tắc chuẩn trong `state_machine.py`:
- **At-most-once posting**: Không bao giờ bấm nút "Đăng" lần 2 nếu lần trước đã tap và chưa có chứng minh `PROVEN_NOT_POSTED`.
- **Graceful State Machine Transition**: Khi `_handle_post()` phát hiện receipt cũ đã ghi nhận tap (`post_tapped` hoặc `verification_pending`), KHÔNG được quăng unhandled exception làm sập tiến trình.
- Thay vào đó:
  1. Ghi nhận `post_tap_attempted = True`.
  2. Bỏ qua thao tác tap Post.
  3. Trả về `True` để state machine tự động chuyển tiếp sang state tiếp theo: `VERIFY_POST`.
  4. `VERIFY_POST` sẽ kiểm tra UI markers và quét grid profile để xác nhận video đã lên hay chưa.

### Receipt Account Matching Rule:
- Khi `target_account` được xác định, receipt matching phải kiểm tra chính xác `target_account` (case-insensitive, normalized lstrip `@`).
- Tránh việc một account cũ trên cùng máy làm block nhầm account mới.

---

## 3. Media Fingerprint Ledger & Stale Reservation Pitfall

### Cơ chế:
- Trước `MEDIA_PUSH`, `MediaFingerprintLedger.reserve()` hash source video (`SHA-256`) và lưu reservation (`status: reserved`, `run_id`, `timestamp`).
- Sau khi `VERIFY_POST` thành công, `finalize()` chuyển status thành `verified_success`.

### Pitfall (Kẹt reservation khi tiến trình bị ngắt giữa chừng):
- Nếu lệnh chạy bị timeout (ví dụ terminal timeout 180s - 300s) hoặc bị kill giữa chừng khi đang ở `VIDEO_PICK` hay `CAPTION_FILL`:
  - Reservation file vẫn giữ `status: "reserved"`.
  - Mặc định ledger coi reservation còn hiệu lực trong `stale_after_seconds = 1800` (30 phút).
  - Lần chạy tiếp theo trong vòng 30 phút sẽ ném lỗi:
    `[MEDIA_FINGERPRINT_PENDING] Exact media SHA-256 has unresolved ledger status=reserved`

### Biện pháp phòng tránh & Xử lý:
1. **Timeout cho canary / live upload**: Video upload trên máy thật có thể mất 3 - 6 phút (bao gồm chuyển app, dismiss popup, scan profile grid baseline, push video qua ADB, pick video, caption, post và verify). Luôn đặt `timeout >= 600s` cho lệnh terminal thực thi live.
2. **Rebind khi retry**: Khi retry có bằng chứng rõ ràng hoặc re-run trên cùng target, ledger cần hỗ trợ `rebind_reserved` theo `previous_run_id` hoặc kiểm tra tính sống còn của tiến trình sở hữu reservation.
