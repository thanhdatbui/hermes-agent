# Google Drive Cleanup Legacy 30-Clip Hazard & 45-Clip Recovery Playbook

## 1. Bản Chất Sự Cố: Bẫy Xóa Nguồn Sớm (< 45 Clip) Do Code Cũ
- **Quy chuẩn bất biến của Farm**: Toàn bộ hệ thống áp dụng tiêu chuẩn duy nhất: **Tối thiểu Min 40 clip, đích đến 45 clip (chuẩn 45 clip)**. Mốc 30 clip là chuẩn cũ đã bị bãi bỏ vĩnh viễn từ ngày 03/10/2026.
- **Lỗ hổng code cũ**: Trong `D:\Taadaa\tools\sync_and_clean_gdrive.py` trên máy Admin, logic dọn đĩa cũ có điều kiện:
  ```python
  rendered = {p.name for p in r_dir.iterdir() if p.is_file() and p.suffix.lower() == ".mp4" and p.stat().st_size > 100000}
  if len(rendered) < 30:
      continue
  ```
- **Hậu quả dây chuyền**:
  1. Khi một kênh trên Admin render đạt 30 đến 44 clip thành phẩm (ví dụ 38 clip).
  2. Script `sync_and_clean_gdrive.py` chạy qua Task Scheduler mỗi 2 tiếng, thấy $38 \ge 30$, liền sao lưu toàn bộ nguồn lên `G:\My Drive\video_goc_backup\<f_src>` và **xóa các file video gốc đã render khỏi `D:\video goc may 2\<f_src>`**.
  3. Thư mục video gốc trên đĩa sụt giảm chỉ còn 15–25 clip unrendered.
  4. Lượt chạy tiếp theo của launcher render (`run_tik*.ps1`) áp dụng quy tắc an toàn: `if ($sourceMp4.Count -lt 40) { continue }`. Thấy thư mục nguồn chỉ còn 15–25 clip, launcher tự động **SKIP** bỏ qua.
  5. **Hậu quả thực tế**: 49 kênh trên cụm Admin bị kẹt cứng vĩnh viễn ở mức 30–44 clip, không bao giờ hoàn tất được chuẩn 45 clip.

## 2. Bản Vá Mã Nguồn Bắt Buộc Trên Admin
Trong `D:\Taadaa\tools\sync_and_clean_gdrive.py`, ngưỡng kiểm tra bắt buộc phải là 45:
```python
rendered = {p.name for p in r_dir.iterdir() if p.is_file() and p.suffix.lower() == ".mp4" and p.stat().st_size > 100000}
if len(rendered) < 45:
    continue
```
Chỉ khi nào thư mục thành phẩm `D:\TIKTOK-videonuoinick-admin\<f_vid>` đã render đủ $\ge 45$ clip thì mới được phép kích hoạt dọn dẹp video gốc.

## 3. Quy Trình Cứu Hộ Cuốn Chiếu (Recovery Playbook)
Khi phát hiện các kênh bị đóng băng dở dang ở 30–44 clip:

### Bước 1: Tạm dừng Downloader trên Admin
- Tránh việc downloader cào thêm video mới làm tràn ổ `D:` SSD (thường chỉ còn 15–20 GB trống).
- Lệnh:
  ```powershell
  Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { $_.CommandLine -like "*download_by_niche*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  ```

### Bước 2: Kéo trả nguồn cuốn chiếu từ Google Drive
- Toàn bộ video gốc ban đầu vẫn còn nguyên vẹn 100% trong `G:\My Drive\video_goc_backup\<f_src>`.
- Kéo trả các file bị thiếu về lại `D:\video goc may 2\<f_src>` theo từng đợt nhỏ (3–5 folder/đợt để không tốn quá 2 GB đĩa):
  ```powershell
  Get-ChildItem "G:\My Drive\video_goc_backup\<f_src>\*.mp4" | ForEach-Object {
      if (-not (Test-Path "D:\video goc may 2\<f_src>\$($_.Name)")) {
          Copy-Item $_.FullName -Destination "D:\video goc may 2\<f_src>\"
      }
  }
  ```

### Bước 3: Render bù lên chuẩn >= 45 clip
- Kích hoạt `random_batch_render.py` với cờ `--resume-verify-existing`:
  ```bash
  python D:/Taadaa/Tiktok-video/scripts/random_batch_render.py \
    --input-dir "D:/video goc may 2/<f_src>" \
    --output-dir "D:/TIKTOK-videonuoinick-admin/<f_vid>" \
    --preset "D:/Taadaa/Tiktok-video/presets/preset_owner.json" \
    --parallel 1 --resume-verify-existing \
    --slot <slot> --machine-id <m_idx>
  ```
- Script sẽ skip 100% các clip đã có (30–44 clip) và chỉ render đúng vài clip còn thiếu lên đủ 45 clip trong vài phút.

### Bước 4: Dọn dẹp an toàn & Giải phóng đĩa
- Chạy `python D:\Taadaa\tools\sync_and_clean_gdrive.py` (đã nâng chuẩn $\ge 45$) để giải phóng các video gốc vừa render xong, trả lại dung lượng đĩa trống.
- Lặp lại cho đợt folder tiếp theo cho đến khi hoàn tất 100% các kênh bị kẹt.

### Bước 5: Khởi động lại Downloader
- Sau khi toàn bộ các folder kẹt đã đạt $\ge 45$ clip và đĩa `D:` được giải phóng an toàn, kích hoạt lại downloader:
  ```bash
  python D:/Taadaa/tools/admin_ssh.py "python C:/Users/Admin/run_admin_downloader_service.py"
  ```

## 4. Chiến Lược Giới Hạn 45 Clip Cán Đích vs Render Hết Nguồn (Disk Safety Tradeoff - User Directive 2026-10-25)
- **Câu hỏi nghiệp vụ**: Khi folder gốc có 60–70 clip (ví dụ folder 499 có 65 clip), có nên render hết sạch sang output không?
- **Quyết định vận hành của User**: **GIỮ VỮNG NGƯỠNG ĐÍCH 45 CLIP TRƯỚC ĐỂ TRÁNH TRÀN Ổ ĐĨA**:
  1. **Dung lượng dự trữ**: Với 45 clip thành phẩm và nhịp xoay ca 4 ngày/lần, tài khoản đã có sẵn đủ video đăng liên tục trong 180 ngày (6 tháng).
  2. **Bảo vệ an toàn đĩa Admin SSD 1TB**: Ổ đĩa D: Admin chỉ còn ~13–15 GB trống. Nếu render vượt trần lên 60–70 clip cho hàng trăm folder, dung lượng video thành phẩm sẽ ngốn thêm 35–45 GB, chắc chắn gây tràn đĩa (`0 MB free`), kích hoạt lại Google Drive virtual cache deadlock và làm sập pipeline.
  3. **Bảo tồn nguồn gốc**: Toàn bộ 60–70 clip gốc đã được sao lưu toàn vẹn 100% trên Google Drive 5TB (`G:\My Drive\video_goc_backup\<f_src>`).
  4. **Kế hoạch đợt 2**: Chỉ render đủ $\ge 45$ clip để đạt chuẩn farm và dọn dẹp local. Khi nào tài khoản đăng gần hết (chạm clip 40–45 sau 5–6 tháng nữa), hệ thống mới kéo các clip từ 46 trở đi về render nối tiếp.
