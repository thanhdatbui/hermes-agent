# Quy Chuẩn Chuẩn Hoá Kênh 3 Món (Avatar – Hashtag/Niche – Ghim Video) & Pin Top Device Lock (2026-10-20)

## 1. Bản chất quy trình Chuẩn hoá 3 món
Khi User gửi ảnh màn hình trang cá nhân TikTok và phát lệnh "Chuẩn hoá kênh này" / "Chuẩn hoá acc":
1. **Định vị toạ độ Farm O(1):**
   - Dùng WinRT OCR đọc username `@handle`, tên hiển thị, chỉ số (following, follower, likes, video count).
   - Tra cứu O(1) qua `Tik<N>.xlsx` hoặc `taikhoan_run_safe.xlsx` để xác định: Máy N, Slot Tik, Folder render $F_{out}$ và Folder video gốc $F_{src}$, Niche.
   - Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` để xác nhận thiết bị online, pin, proxy cổng tương ứng.

2. **Món 1 — Ghim Video (Pin Gate $\ge 1.000$ views):**
   - Chỉ ghim khi có clip trên lưới đạt $\ge 1.000$ views; nếu toàn bộ $< 1.000$ views thì giữ nguyên thứ tự tự nhiên.
   - Chạy dry-run kiểm tra: `python D:/Taadaa/tools/pin_top_videos.py --machine <N> --account <handle> --dry-run`.
   - Khi chạy thật: `python D:/Taadaa/tools/pin_top_videos.py --machine <N> --account <handle>`.

3. **Món 2 — Hashtag & Niche:**
   - Đối soát Niche trong `Tik<N>.xlsx` (ví dụ `kienthuc_viral`, `thucung`...).
   - Khóa marker vật lý `.manual_hashtag_locked` tại cả 2 đầu thư mục $F_{out}$ (`D:/TIKTOK-videonuoinick/<F_out>`) và $F_{src}$ (`D:/video goc/<F_src>`).
   - Thêm folder vào registry `D:/Taadaa/data/manual_hashtag_protected_folders.json`.

4. **Món 3 — Avatar chuẩn từ Video gốc ($F_{src}$):**
   - Trích xuất 2 phương án ảnh $512 \times 512$:
     * **Phương án 1 (Khuyên dùng):** Nhân vật/chủ đề từ video gốc $F_{src}$, ngũ quan chính diện, ánh sáng tự nhiên.
     * **Phương án 2:** Ảnh từ kho render $F_{out}$.
   - Ghép ảnh so sánh có vòng tròn định vị viền avatar màu xanh và banner độ tương phản cao để WinRT OCR đọc được nhãn.
   - Soi mắt kiểm định qua OCR/Vision trước khi đính kèm `MEDIA:D:/Taadaa/reports/...` để User chọn.
   - Khi User duyệt phương án (ví dụ chọn "1"):
     * Copy ảnh vào `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`.
     * Tạo marker `.manual_avatar_locked` tại cả 2 đầu kho $F_{out}$ và $F_{src}$.
     * Thêm folder vào `D:/Taadaa/data/manual_avatar_protected_folders.json`.
     * Cập nhật cột `Avatar = 'PENDING'` trong `Tik<N>.xlsx` và `avatar_replace_queue` trong `D:/Taadaa/data/tiktok_tracker.db`.

---

## 2. Invariant Kỹ Thuật: Device Lock `force_preempt=True` & `adb_path` trong Operator Tools

### A. Deadlock do Stale Lock File trong `operator_device_lock`
- **Hiện tượng:** Tool chạy lệnh device lock (như `pin_top_videos.py`) bị timeout 60s/300s dù tiến trình trước đó đã chết, do file `machine_<N>.lock.json` vẫn còn lưu PID cũ.
- **Nguyên nhân:** Hàm `_remove_stale_if_possible` trong `automation_core.device_lock` luôn trả về `False` theo thiết kế bảo vệ nghiêm ngặt, khiến `wait_for_device_lock` polling chờ đến hết timeout.
- **Khắc phục:** Trong các công cụ operator can thiệp có chủ đích (interactive CLI), truyền thêm:
  ```python
  lock_ctx = operator_device_lock(
      machine=args.machine,
      serial=serial,
      force_preempt=True,
      timeout=30.0
  )
  ```
  `force_preempt=True` kích hoạt `allow_takeover=True` với scope `TAKEOVER_SCOPE_OPERATOR_PREEMPT`, tự động tiếp quản hoặc xóa stale lock của PID đã chết ngay lập tức.

### B. AdbClient `adb_path` cho Persistent UI Dump qua ATX
- **Hiện tượng:** `_dump_profile_ui_atx` trong `pin_top_videos.py` gọi `capture_atx_session_ui(dev)` nhưng bị timeout hoặc fallback liên tục vì `dev = AdbClient(serial=serial)` không tìm thấy đường dẫn ADB chính xác.
- **Khắc phục:** Bắt buộc truyền `adb_path=ADB_BIN` (ví dụ `C:\Program Files (x86)\xiaowei\tools\adb.exe`):
  ```python
  dev = AdbClient(serial=serial, adb_path=ADB_BIN)
  p = capture_atx_session_ui(dev, timeout=timeout)
  ```
