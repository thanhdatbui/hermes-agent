# Cơ Chế Opportunistic Upload & Phân Tách Lịch Dưỡng Sinh Farm (2026-10-11)

## 1. Bản Chất Kỹ Thuật (Architecture Invariant)
Trong hệ thống nuôi tài khoản TikTok đa máy (`tiktok-luot nuoi acc` và `tiktok_runner.py`), hai luồng hành vi cần được tách bạch tuyệt đối:
- **Luồng Follow (Anti-Fraud Guarded):** Chịu sự quản lý của bậc thang Probation, cờ `_is_follow_cooldown` (khi bị nhả follow) và biến môi trường `TAADAA_REST_DAY_NO_FOLLOW=1` (ngày dưỡng sinh / ca tối xả tải).
- **Luồng Upload Video (Recommendation Engine Oriented):** Là hành vi Creator lành mạnh. **Luôn mở cờ `-AllowUploadHook` ở cả Phiên 1 và Phiên 2**, không phụ thuộc vào trạng thái nghỉ follow hay cooldown của tài khoản.

---

## 2. Cơ Chế Opportunistic Upload (Phiên 1 hoặc Phiên 2)
1. **Tránh Điểm Lỗi Duy Nhất (Single Point of Failure):**
   - Khi lịch nuôi mỏng hóa theo chu kỳ (3 ca / 4 ngày), mỗi tài khoản có rất ít lượt xuất hiện. Nếu chỉ gán cứng upload vào Phiên 2, một sự cố rớt mạng/proxy/app crash ở Phiên 2 sẽ làm mất trắng slot đăng cả ngày.
   - Phiên 1 (Primary) lướt feed và thử upload. Nếu thành công -> ghi nhận vào sổ cái `shift_upload_history.json`.
   - Phiên 2 (Fallback): Sổ cái kiểm tra thấy đã có video trong ngày -> tự động trả về `already_uploaded_in_shift` và **BỎ QUA (SKIP)**. Nếu Phiên 1 thất bại -> Phiên 2 đăng bù ngay lập tức.
2. **Không Retry Dồn Dập Tại Chỗ:**
   - Phiên 1 gặp lỗi upload -> ghi nhận fail, đóng phiên, để phiên 2 cách 2 tiếng thử lại tự nhiên. Không retry liên tục tránh bị thuật toán TikTok đánh dấu automation spike.
3. **Quy Tắc Runner Parameters:**
   - Trong `tiktok_runner.py`, tham số `-AllowUploadHook` được truyền vô điều kiện:
     ```python
     # Cơ chế cơ hội (Opportunistic Upload): Cho phép upload ở cả Phiên 1 & Phiên 2.
     # Sổ cái shift_upload_history.json tự động chặn nếu phiên trước đã đăng thành công.
     "-AllowUploadHook",
     ```
   - Trong `run-feed-session.ps1`:
     ```powershell
     if ($AllowUploadHook -or $SessionIndex -in 1, 2) {
         $arguments += "--allow-upload-hook"
         $arguments += "--session-index", "$SessionIndex"
     }
     ```
