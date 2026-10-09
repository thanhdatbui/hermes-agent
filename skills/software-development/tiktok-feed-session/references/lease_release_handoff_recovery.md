# Triệu chứng: 'lease release or handoff failed' (blocker_type: lease-finish-failed)

## 1. Vị trí phát sinh chính xác
- **File:** `D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\multi_machine_feed_session.py` (khối teardown `finally`, dòng ~4930-5070).
- **Lưu ý:** Lỗi này **KHÔNG** nằm trong `flows/feed_swipe_smoke.py`. Không dùng grep quét đĩa toàn bộ repo kẻo timeout.

## 2. Cơ chế và Root Cause
Trong `multi_machine_feed_session.py`:
- Sau khi worker chạy xong session (thành công hoặc thất bại), luồng teardown `finally` sẽ thu hồi và hoàn tất lease:
  ```python
  lease = lock_holder.get("lease")
  if lease is not None:
      ...
      if goal_completed:
          try:
              if timing is not None:
                  pub_lock = timing.get("publication_lock")
                  state_lock = timing.get("state_lock")
                  def _release_under_lock() -> bool:
                      if _watchdog_deadline_expired(timing) or not _claim_success_release(timing):
                          return False
                      ...
                      lease.finish(succeeded=True)
                      ...
                      now = time.monotonic()
                      def _record_completion():
                          if now >= float(timing.get("deadline_mono", 0)) or timing.get("terminalized") or timing.get("publication_owner") != "worker":
                              return False
                          timing["success_release_completed_at"] = now
                          timing["success_release_completed"] = True
                          return True
  ```
- **Các nguyên nhân kích hoạt `lease_release_failed = True`:**
  1. **Watchdog deadline expired:** Quá thời hạn quy định trong `timing.get("deadline_mono")`.
  2. **Race condition / Tranh chấp lock:** `_claim_success_release(timing)` thất bại khi watchdog thread đã can thiệp terminalize trước.
  3. **File lock write failure:** Ngoại lệ khi ghi đè trạng thái `handoff` hoặc `released` vào file lock (nằm ở `~/.codex/device-locks/machine_<N>.lock.json`).
  4. Khi `lease_release_failed` được bật, kết quả của máy bị ghi đè:
     - `final_status="failed"`
     - `blocker_type="lease-finish-failed"`
     - `stop_reason="lease release or handoff failed"`

## 3. Quy trình xử lý
1. **Kiểm tra stale lock:**
   - Kiểm tra `~/.codex/device-locks/machine_<N>.lock.json` xem có còn tồn tại PID cũ hay timestamp bị treo > 600s không.
2. **Kiểm tra watchdog timing & deadline:**
   - Kiểm tra cấu hình timeout của worker và đảm bảo `deadline_mono` đủ dài cho các máy có độ trễ I/O cao.
3. **Patch an toàn trong `multi_machine_feed_session.py`:**
   - Đảm bảo nếu session swipe thực tế đã đạt target (`initial_goal_completed`), việc release lock chậm không được làm sai lệch trạng thái thành `failed` nếu lock vẫn un-claim/release thành công sau đó.
4. **Lệnh Canary verification:**
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
   ```
