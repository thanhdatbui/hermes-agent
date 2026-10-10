# Cơ Chế Opportunistic Upload (Đăng Video Cơ Hội Cả Phiên 1 & Phiên 2)

## 1. Bối Cảnh & Rủi Ro Của Gán Cứng "Chỉ Đăng Phiên 2"
- **Tử huyệt điểm lỗi duy nhất (Single Point of Failure):** Khi farm vận hành lịch mỏng hoặc xoay tua (chu kỳ 4 ngày, chạy cách nhật), mỗi tài khoản chỉ có rất ít lượt xuất hiện trong ngày.
- Nếu gán cứng upload video vào Phiên 2: Nếu Phiên 2 gặp lỗi mạng 4G, proxy lag, app crash hoặc kẹt render $\to$ **Tài khoản mất trắng lượt đăng video cả ngày**, làm đứt nhịp phân phối của thuật toán và kéo dài thời gian nuôi acc đạt mốc 10 video.

---

## 2. Kiến Trúc Opportunistic Upload (Phiên 1 Primary + Phiên 2 Fallback)
Cơ chế này cho phép mở cờ upload ở cả 2 phiên, dùng sổ cái tập trung để đảm bảo tính **Idempotent (chỉ đăng duy nhất 1 video/ngày/acc)**:

```
[Bắt đầu ca nuôi]
       │
       ▼
[Phiên 1 (Primary)] ──(Chưa đăng)──► Thử Upload Video
       │                                   │
       │                             ┌─────┴─────┐
       │                          Thành công    Thất bại
       │                             │             │
       │                             ▼             ▼
       │                    Ghi sổ cái SUCCESS   Ghi log fail
       │                                           │
       ▼                                           ▼
[Phiên 2 (Fallback)] ──(Đã có SUCCESS)──► [SKIP UPLOAD]
       │
       └──(Chưa có SUCCESS do P1 xịt)──► [ĐĂNG BÙ NGAY]
```

---

## 3. Quy Tắc Triển Khai Code Chuẩn Farm

### A. Cấu hình tại `tiktok_runner.py` (Runtime & Deploy)
Trong hàm `_spawn_feed_session`:
```python
# Cơ chế cơ hội (Opportunistic Upload): Cho phép upload ở cả Phiên 1 & Phiên 2 khi KHÔNG phải ngày dưỡng sinh.
# Hệ thống có sổ cái shift_upload_history.json tự động chặn nếu phiên trước đã đăng thành công.
*( ["-AllowUploadHook"] if not is_rest_day else [] ),
```
*Lưu ý: Luôn đồng bộ giữa `C:/Users/Kibe/AppData/Local/hermes/scripts/tiktok_runner.py` và `D:/Taadaa/Hermes/deploy/hermes-home/scripts/tiktok_runner.py`.*

### B. Cấu hình tại `run-feed-session.ps1`
```powershell
if ($AllowUploadHook -or $SessionIndex -in 1, 2) {
    $arguments += "--allow-upload-hook"
    $arguments += "--session-index", "$SessionIndex"
} else {
    $arguments += "--session-index", "$SessionIndex"
}
```

### C. Quản lý Sổ Cái tại `multi_machine_feed_session.py`
- Hàm `claim_shift_upload`:
  * Sử dụng khóa file liên tiến trình `_InterProcessFileLock` trên `shift_upload_history.json`.
  * Nếu tài khoản đã có trạng thái `success` hoặc `indeterminate` trong ngày logic $\to$ trả về `already_uploaded_in_shift` và bỏ qua upload.
  * Nếu Phiên 1 lỗi $\to$ không ghi nhận `success`, Phiên 2 nhận quyền reservation và tiến hành upload bù an toàn.
  * Khi là Ngày Dưỡng Sinh (`is_rest_day`): Tắt cờ `-AllowUploadHook` 100%, bảo đảm không upload và không follow.
