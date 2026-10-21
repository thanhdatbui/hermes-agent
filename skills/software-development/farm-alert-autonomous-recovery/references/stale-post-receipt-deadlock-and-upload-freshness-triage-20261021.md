# Stale Post Receipt Deadlock & Upload Freshness Triage Protocol (21/10/2026)

## 1. Bối cảnh & Hiện tượng (The Idempotency Receipt Trap)
- **Cảnh báo từ Watchdog:** `daily-stale-upload-accounts-watchdog` báo cáo hàng chục tài khoản bị "Nguy cơ đóng băng (> 14 ngày không có video mới)".
- **Nghịch lý tại hiện trường:** 
  - Máy vẫn online, TikTok vẫn hoạt động.
  - Thư mục video `D:/TIKTOK-videonuoinick/<folder>/` có đầy đủ 45–57 clip render sẵn, clip tiếp theo (`next_video.mp4`) tồn tại 100%.
  - Khi runner chạy đến máy, workflow lập tức dừng với trạng thái `MANUAL_REVIEW`:
    `[POST_SUBMISSION_UNKNOWN] post_submission_state=UNKNOWN: không có bằng chứng TikTok ACCEPTED submission; không được ghi workbook hay báo success (COMPAT-POST-VERIFY-004)`

## 2. Bản chất kỹ thuật (Root Cause Analysis)
1. **Lệch pha cơ chế hết hạn (Expiry Gap) giữa Media Fingerprint và Post Attempt Receipt:**
   - `media_fingerprint.py` có cơ chế tự giải phóng an toàn khi worker bị crash: `stale_after_seconds = 1800` (sau 30 phút, reservation ở trạng thái `reserved` sẽ tự động nhả cho worker sau).
   - Ngược lại, thư mục `D:\CodexRuntime\tiktok-video\idempotency\post-attempts\` lưu các file `machine_{M}_account_{acc}_video_{N}.json` **HOÀN TOÀN KHÔNG CÓ CƠ CHẾ AUTO-EXPIRY**.
2. **Cơ chế gây Deadlock:**
   - Trong một phiên chạy cũ, khi runner phát lệnh tap Post hoặc vừa chạm vào intent đăng nhưng gặp sự cố (ADB timeout, app crash, USB micro-spike, hoặc văng launcher), file receipt được ghi với `status: "intent_pending"` và `post_submission_state: "UNKNOWN"`.
   - Ở các phiên tiếp theo, hàm `_route_existing_post_receipt_to_verification()` phát hiện có receipt chưa hoàn tất nên cưỡng chế chuyển thẳng sang `VERIFY_POST`.
   - Tại `VERIFY_POST`, hàm `_post_submission_state_allows_success()` kiểm tra `post_submission_state`. Vì trạng thái là `UNKNOWN` (không có bằng chứng `ACCEPTED`), rule bảo vệ `COMPAT-POST-VERIFY-004` lập tức chặn không cho verify tiếp, không cho ghi workbook và ép dừng ở `MANUAL_REVIEW`.
   - Vì receipt không tự hết hạn, **máy bị kẹt vĩnh viễn ở video đó qua hàng chục ngày** (như Máy 4 kẹt 16 ngày, Máy 74 kẹt 21 ngày).

## 3. Quy trình Triage & Giải Phóng Deadlock O(1)

### Bước 1: Phân loại danh sách cảnh báo Stale Upload
- Tách 70–80% tài khoản thuộc Admin Farm (M201–M280): Cụm Admin chỉ tạm dừng để render video gốc, không phải lỗi hệ thống.
- Kiểm tra các máy offline phần cứng: M10, M30 (lỏng chân cáp Micro-USB vật lý).
- Kiểm tra các máy kẹt ADB transport: M74 (chạy `recover_stuck_s7.py -m 74` thực hiện Level 3 Reconnect để thông pipe socket).

### Bước 2: Rà soát & Lưu trữ (Archive) Stale Post Receipts
- Kiểm tra các receipt bị kẹt > 24h trong `D:\CodexRuntime\tiktok-video\idempotency\post-attempts\`:
  ```bash
  python D:/Taadaa/tools/reconcile_stale_post_receipts.py
  ```
- Thực thi di chuyển (archive an toàn, không xóa mất dấu vết) sang thư mục `archived_stale/`:
  ```bash
  python D:/Taadaa/tools/reconcile_stale_post_receipts.py --apply
  ```
- Sau khi receipt được archive, workflow ở các ca tiếp theo sẽ nhận diện không còn receipt treo và tự động nạp video mới để upload bình thường.

## 4. Kỷ luật kiểm chứng (Verification Invariant)
- Sau khi chạy `--apply`, BẮT BUỘC chạy lại `python D:/Taadaa/tools/reconcile_stale_post_receipts.py` xác nhận số lượng receipt kẹt là `0`.
- Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` trên các máy vừa giải phóng để xác nhận máy đã ở trạng thái sẵn sàng (`LauncherActivity` hoặc `Sleep/Dozing`, pin > 60%, proxy kết nối tốt).
