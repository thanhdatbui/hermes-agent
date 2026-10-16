# Immediate Single-Machine Avatar Upload & Header Switcher Candidate Trap (2026-10-17)

## 1. Bẫy Dừng Lại Chờ Watchdog Thụ Động (Immediate Execution Invariant)
- **Hiện tượng / Phản hồi từ User:** Khi User đã chọn xong Phương án Avatar (ví dụ: User chốt "1"), Agent hoàn thành việc đồng bộ file ảnh 512x512, cắm marker `.manual_avatar_locked`, cập nhật Excel và set trạng thái `PENDING` trong database `tiktok_tracker.db` nhưng lại dừng lại và báo *"Watchdog sẽ tự động nạp ảnh trong ca..."*. User phản ứng gay gắt: *"Sao k up luôn mà phải chờ v"*.
- **Quy tắc bắt buộc (End-to-End Invariant):**
  - Chuẩn hoá 3 món (Avatar - Hashtag - Pin) là quy trình khép kín End-to-End: `Crop 512x512 -> User duyệt PA -> Lock/Excel/DB -> KÍCH HOẠT NGAY RUNNER NẠP APP -> Nghiệm thu ảnh MEDIA:`.
  - CẤM TUYỆT ĐỐI dừng lại ở bước enqueue database rồi nằm chờ cron/watchdog ban đêm hoặc chờ User giục.
- **Lệnh thực thi chuẩn cho 1 máy lẻ:**
  ```powershell
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik <tik> -ForceAvatarMachineList "<machine>" -MaxParallel 1 -HostConfigPath D:\Taadaa\machine-config\<host>.yaml
  ```
- **Lưu ý điều phối Coordinator Guard:**
  - Lệnh PowerShell trực tiếp bị chặn bởi Coordinator default-deny guard.
  - Cần chạy qua file script Python launcher đã chuẩn hóa (hoặc dispatch worker nếu cần) với cơ chế non-blocking: `terminal(background=True, notify_on_complete=True, timeout=300)` để harness tự đánh thức khi runner hoàn tất, sau đó chụp màn hình Profile thực tế bằng ADB để soi mắt kiểm định (Gate 6).

---

## 2. Bẫy Header Candidates = 2 Khi Mở Account Switcher (Profile Header Ambiguity)
- **Hiện tượng lỗi:**
  - Runner chạy `run_tiktok_upload_avatar.ps1` trên máy lẻ thất bại ở state `ACCOUNT_SWITCHER`:
    `[ACCOUNT_SWITCHER_FAILED] open_switcher failed: SWITCHER_NOT_CONFIRMED: switcher markers were not confirmed. Cần MANUAL_REVIEW...`
  - Trong file `execution.log`, adapter log liên tục 6 lần:
    `[PREPARE_SWITCHER] Header candidates=2 centers=[(277, 298), (504, 483)] limit=672`
    nhưng không thực hiện bất kỳ cú tap nào (`taps == 0`).
- **Nguyên nhân gốc rễ:**
  - Trên màn hình Profile chuẩn của TikTok (ví dụ: tài khoản `@linhsoc6240` tên "Ngô Thị Vy"):
    1. Tên hiển thị xuất hiện trên thanh Action Bar trên cùng: `(cx=277, cy=298)` kèm mũi tên trỏ xuống mở switcher.
    2. Tên hiển thị xuất hiện lần thứ hai ở tiêu đề lớn ngay dưới ảnh avatar: `(cx=504, cy=483)`.
  - Cả 2 text node này đều nằm trong vùng quét `top < header_limit` (`header_limit = 672`).
  - Trong `D:/Taadaa/Tiktok-video/scripts/tiktok_workflow/adapter.py`, hàm `prepare_switcher_anchor` đặt điều kiện kiểm tra cứng nhắc:
    ```python
    if len(candidates) == 1:
        t, cx, cy = candidates[0]
        self.tap(cx, cy)
    ```
  - Khi có đúng 2 nodes trùng tên hợp lệ, `len(candidates) == 2` khiến logic bỏ qua không tap gì, chờ lặp đến khi timeout và fail toàn bộ runner.
- **Giải pháp chuẩn hóa (Patch Pattern O(1)):**
  - Thay vì chỉ chấp nhận `len(candidates) == 1`, sắp xếp candidates theo tọa độ trục Y tăng dần (`cy` nhỏ nhất = nằm cao nhất trên màn hình) và chọn candidate trên cùng:
    ```python
    if candidates:
        candidates.sort(key=lambda c: c[2])
        t, cx, cy = candidates[0]
        self.tap(cx, cy)
        logger.info(f"[PREPARE_SWITCHER] Tapped profile name at ({cx}, {cy})")
        time.sleep(0.75)
        return True
    ```
  - Tọa độ `(cx, cy)` nhỏ nhất đảm bảo luôn chạm đúng vào thanh Action Bar đỉnh màn hình để mở popup Switcher tài khoản một cách tin cậy.
