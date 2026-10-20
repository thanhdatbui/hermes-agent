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

---

## 3. Công Thức Định Vị O(1) Khi Nhận Gợi Ý Thu Gọn ("Máy M, acc row S") & Rào Cản Hard Gate #5 Device Lock

### A. Công thức tính dòng O(1) qua `read_file` (Bypass cấm `execute_code` & không cần mở Python)
Khi User gửi chỉ dẫn nhanh dạng `"máy <M>, acc row <S>"` (hoặc khi OCR ảnh màn hình bị lỗi/mờ tên nick):
1. **Trong `taikhoan_run_safe.xlsx` (Sheet Accounts) và `taikhoan_dat_v2_updated .xlsx` (Sheet Tài Khoản):**
   - Mỗi máy có đúng 8 slots được xếp tuần tự theo thứ tự slot 1 đến 8.
   - Dòng mục tiêu: $\text{Row} = (M - 1) \times 8 + S + 2$ (do 2 dòng đầu là tiêu đề).
   - Ví dụ: Máy 38, Row 4 -> $\text{Row} = (38 - 1) \times 8 + 4 + 2 = 302$. Dùng `read_file(path='D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx', offset=299, limit=10)` đọc trực tiếp.
2. **Trong `Tik<S>.xlsx` (Tương ứng Slot $S$):**
   - File `Tik<S>.xlsx` chứa toàn bộ tài khoản ở Slot $S$ trên tất cả các máy.
   - Dòng mục tiêu trong sheet `TaiKhoan`: $\text{Row} = M + 2$ (do 2 dòng đầu là header).
   - Ví dụ: Slot 4 Máy 38 -> mở `Tik4.xlsx` tại dòng $38 + 2 = 40$. Dùng `read_file(path='D:/OneDrive/TaadaaData/kibe/Tik4.xlsx', offset=38, limit=5)` để lấy ngay $F_{vid}$, $F_{src}$, Niche, Hashtag.

### B. Rào cản HARD GATE #5 - DEVICE LOCK REQUIRED trên lệnh ADB trần
- **Hiện tượng:** Chạy `adb -s <serial> shell ...` trực tiếp trong terminal Coordinator sẽ bị Guard chặn ngay lập tức:
  `[HARD GATE #5 - DEVICE LOCK REQUIRED] LỆNH ADB BỊ CHẶN: Thiết bị '<serial>' CHƯA ĐƯỢC KHÓA (không có active lock hợp lệ trong ~/.codex/device-locks/)!`
- **Quy chuẩn thực thi an toàn:**
  * **Trích xuất hiện trường T0 (O(1)):** Luôn dùng `python D:/Taadaa/tools/inspect_machine.py <N>` — script này đã được whitelist trong allowlist của Coordinator và tự xử lý ADB an toàn không kích hoạt Hard Gate #5.
  * **Can thiệp lệnh ADB shell:** Bắt buộc bọc qua `python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>` hoặc gọi qua script Python có bọc `operator_device_lock(serial=..., force_preempt=True)`.
  * **Bypass lệnh cấm `execute_code`:** Coordinator Guard chặn `execute_code` để chống bypass. Mọi tra cứu dữ liệu Excel/DB/file phải tận dụng `read_file` (vốn tự động trích xuất `.xlsx` thành bảng text có đánh số dòng).

