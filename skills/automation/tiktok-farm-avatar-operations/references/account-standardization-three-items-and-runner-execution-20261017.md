# Chuẩn Hoá 3 Món: Quy Ước Lệnh "Đổi Ảnh", Type Safety Protected Folders & Subprocess Launcher (17/10/2026)

## 1. Quy Ước Phản Hồi Ngắn Gọn Của User: "Đổi ảnh"
- **Hiện tượng**: Sau khi Coordinator phân tích hiện trường và gửi 2 phương án avatar kèm ảnh `MEDIA:`, User chỉ nhắn ngắn gọn: *"Đổi ảnh"*.
- **Nguyên tắc xử lý**:
  - Không hỏi lại *"Anh chọn PA1 hay PA2?"* (gây lãng phí vòng chat và làm chậm tiến độ farm).
  - Mặc định chọn ngay **Phương án 1 (Khuyên dùng)** — phương án đã được Coordinator soi mắt thẩm định qua vision là khớp lưới video và nhận diện thương hiệu/nhân vật tốt nhất.
  - Lập tức kích hoạt quy trình đồng bộ kho và khởi chạy runner nạp app.

---

## 2. Kỷ Luật Dữ Liệu: Type Safety `protected_folders` (Bắt Buộc Kiểu `int`)
- **Cạm bẫy**: Khi ghi folder vào `D:/Taadaa/data/manual_avatar_protected_folders.json` và `manual_hashtag_protected_folders.json`, nếu chèn folder ID dạng chuỗi (`"261"`, `"353"`):
  - Các script nuôi feed và crawler chạy kiểm tra `if int(f) in protected_folders:` sẽ bị trượt điều kiện (do so sánh `int` với `str`).
  - Hậu quả: Marker registry bị vô hiệu hóa, cronjob tự động quét và ghi đè lại avatar/hashtag mặc định.
- **Quy tắc chuẩn**:
  - `protected_folders`: Luôn ép kiểu `int(f)` trước khi append:
    ```python
    for fid in [f_out, f_src]:
        if int(fid) not in j_reg["protected_folders"]:
            j_reg["protected_folders"].append(int(fid))
    ```
  - Trong `accounts`: Key của dictionary là string `str(fid)`.

---

## 3. Quy Trình 5 Bước Chuẩn Bị File & Registry Trước Khi Gọi Runner
1. **Copy Avatar chuẩn 512x512 clean** (không dính viền xanh preview):
   - Đẩy vào `D:/video goc/<f_src>/avatar.jpg`
   - Đẩy vào `D:/TIKTOK-videonuoinick/<f_out>/avatar.jpg`
   - Nếu tồn tại `D:/video goc/<f_out>/`: copy luôn vào đây.
2. **Cắm Physical Marker**:
   - Tạo file `.manual_avatar_locked` tại cả 2 kho (`video goc/<f_src>` và `TIKTOK-videonuoinick/<f_out>`).
   - Tạo file `.manual_hashtag_locked` tại cả 2 kho.
3. **Cập nhật Registry JSON**:
   - Ghi thông tin tài khoản và folder vào `manual_avatar_protected_folders.json` và `manual_hashtag_protected_folders.json`.
4. **Cập nhật Workbook Excel**:
   - Mở `D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx`, tìm dòng số máy tương ứng, gán cột `Avatar = 'OK'`.
5. **Cập nhật SQLite Queue**:
   - Trong `D:/Taadaa/data/tiktok_tracker.db` bảng `avatar_replace_queue`:
     ```sql
     UPDATE avatar_replace_queue SET status='PENDING', updated_at=DATETIME('now') WHERE username=?;
     ```

---

## 4. Kỹ Thuật Khởi Chạy Subprocess Cho `run_tiktok_upload_avatar.ps1`
- **Đặc điểm runner**:
  - `run_tiktok_upload_avatar.ps1` gọi `run_tiktok_upload_batch.ps1` chạy tương tác, yêu cầu chuỗi xác nhận `RUN\n` trên stdin.
  - Console Windows có thể xuất ký tự CP1252/ANSI gây `UnicodeDecodeError` khi Python đọc stdout.
- **Pattern khởi chạy an toàn qua Python script**:
  ```python
  import subprocess
  import sys

  cmd = [
      "powershell.exe",
      "-NoProfile",
      "-ExecutionPolicy", "Bypass",
      "-File", r"D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1",
      "-Tik", str(tik_num),
      "-ForceAvatarMachineList", str(machine_num),
      "-MaxParallel", "1",
      "-HostConfigPath", r"D:\Taadaa\machine-config\kibe.yaml",
  ]
  proc = subprocess.Popen(
      cmd,
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      encoding="utf-8",
      errors="replace",
  )
  stdout, _ = proc.communicate(input="RUN\n")
  sys.exit(proc.returncode)
  ```
- **Kỷ luật Coordinator**:
  - Tác vụ upload trên thiết bị thật kéo dài 1–3 phút, bắt buộc khởi chạy nền:
    `terminal(background=True, notify_on_complete=True, timeout=300)`
  - CẤM chạy vòng lặp sleep polling kiểm tra tiến trình để tuân thủ nguyên tắc Event-Driven Wakeup.

---

## 5. Ghim Video (Pin Top) Cho Kênh $\ge 1.000$ Views
- Khi chuẩn hoá kênh có video đạt $\ge 1.000$ views (ví dụ clip đạt 371K views) nhưng chưa có nhãn "Đã ghim":
  - Sau khi runner nạp avatar xong và mở màn hình profile, chạy công cụ ghim:
    ```bash
    python D:/Taadaa/tools/pin_top_videos.py --machine <N> --min-views 1000 --account <username>
    ```
  - Nghiệm thu qua `screencap` và soi mắt bằng `browser_vision` xác nhận nhãn đỏ "Đã ghim" trước khi báo cáo hoàn tất 3 món.
