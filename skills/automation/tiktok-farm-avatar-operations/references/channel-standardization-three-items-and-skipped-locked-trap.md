# Chuẩn Hoá Kênh 3 Món & Cạm Bẫy SKIPPED_LOCKED Trong Runner Avatar

## 1. Bối Cảnh Sự Cố & Bài Học Xương Máu (15/10/2026 - @sambich012 Máy 49 Tik 4)
- **Sự cố 1 (Đổi avatar nhưng đưa lại ảnh cũ)**:
  - Khi User yêu cầu "chuẩn hoá kênh này" kèm ảnh chụp profile TikTok `@sambich012`, Coordinator thấy file `D:/TIKTOK-videonuoinick/388/avatar.jpg` và `D:/video goc/289/avatar.jpg` đã tồn tại trên đĩa.
  - Coordinator chạy thẳng runner upload file có sẵn đó lên máy mà không kiểm tra xem ảnh đó có phải avatar kênh đang dùng hay không.
  - Kết quả: TikTok tải lên lại y hệt bức ảnh đại diện cũ. User nổi giận: *"dụd mẹ t ns đổi ava mày đưa y cái ava cũ..."*.
  - **Bài học cốt lõi**: File `avatar.jpg` tồn tại sẵn trong folder thường chính là avatar cũ từng up từ các phiên trước. Đổi avatar BẮT BUỘC phải trích xuất nhân vật/frame mới từ các video khác trong kho video gốc.

- **Sự cố 2 (Silent Skip do Device Lock - Exit Code 0 Giả)**:
  - Coordinator chạy `run_avatar_batch_3accs.py --tik 4 --machine 49`.
  - Tiến trình kết thúc với `ExitCode: 0` (`Completed normally`). Coordinator suýt kết luận thành công.
  - Tuy nhiên kiểm tra `summary.csv` thì thấy: `Status: SKIPPED_LOCKED`, `Verified: False`, `Target bị bỏ qua: 49`, `Hoàn tất batch: 0/41`.
  - Nguyên nhân: Máy 49 bị vướng lock từ phiên nuôi feed hoặc lock tạm thời trong `~/.codex/device-locks/`.
  - **Bài học cốt lõi**: `powershell.exe` và `subprocess.run` trả về returncode 0 ngay cả khi 100% máy bị bỏ qua (`SKIPPED_LOCKED`). BẮT BUỘC phải đọc `summary.csv` hoặc log chi tiết để xác nhận `Status == THÀNH CÔNG` và `Verified == True`.

---

## 2. Quy Chuẩn 3 Món Chuẩn Hoá Kênh (Channel Standardization 3-Item Invariant)

Khi nhận lệnh "chuẩn hoá kênh này" hoặc chuẩn hoá tài khoản:

### Món 1: Đổi Avatar Mới Khác Biệt
1. **CẤM TUYỆT ĐỐI**: Không bao giờ lấy lại file `avatar.jpg` có sẵn trong folder để upload lại.
2. **Trích xuất frame mới**:
   - Quét các video `.mp4` trong `D:/video goc/<F_src>` (ví dụ: `10.mp4`, `20.mp4`...) hoặc chọn frame từ `.avatar_work/representative_frames/` khác với video 1.
   - Dùng Haar Cascade hoặc Face Detector lọc khuôn mặt chính diện, rõ nét, biểu cảm tươi tắn khớp ngách kênh.
   - Crop vuông $512 \times 512$ theo center-based crop: giữ trọn vẹn cả hai mắt, sống mũi, miệng, cằm, quai hàm và khoảng đệm an toàn (headroom $\ge 20$px trên đỉnh đầu, chin clearance $\ge 20$px dưới cằm).
   - Kiểm tra viền tròn preview (`circle_preview`).
3. **Ghi đè đồng bộ cả 3 đầu kho**:
   - `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`
   - `D:/video goc/<F_src>/avatar.jpg`
   - `D:/video goc/<F_out>/avatar.jpg` (nếu tồn tại)
4. **Khóa chống ghi đè vật lý**:
   - Đặt file marker `.manual_avatar_locked` tại cả 3 folder trên (`is_folder_avatar_protected = True`).
5. **Cập nhật workbook**:
   - Đặt cột `Avatar = PENDING` trên sheet `TaiKhoan` của `Tik<N>.xlsx`.
6. **Kích hoạt runner & nghiệm thu thực tế**:
   - Chạy `run_avatar_batch_3accs.py --tik <N> --machine <M>`.
   - Kiểm tra `summary.csv` đảm bảo `Verified == True`.
   - Chụp ảnh và soi mắt kiểm tra qua `browser_vision`: `avatar-save-surface-guard.png` và `avatar-uploaded-confirmed.png`.

### Món 2: Kiểm Tra Hashtag & Niche
1. Đối soát ngách của kênh từ video lưới profile (ví dụ: ngách Cười / Hài hước).
2. Kiểm tra cột `Keyword Video` và `Hashtag Pool` trong `Tik<N>.xlsx` đảm bảo phản ánh đúng ngách.
3. Đăng ký folder nguồn $F_{src}$ và $F_{out}$ vào `manual_hashtag_protected_folders.json` để ngăn script cron tự động ghi đè.

### Món 3: Kiểm Tra Điều Kiện Ghim Video (Pin Video)
1. Kiểm tra view của các video đã đăng trên kênh (qua lưới profile hoặc database).
2. **Ngưỡng quy định chuẩn farm**: Chỉ ghim video khi view $\ge 1.000$ views.
3. Nếu video cao nhất chưa đạt ngưỡng (ví dụ: 363 views): **TUYỆT ĐỐI KHÔNG GHIM** và báo cáo rõ số view thực tế cho User. Cấm ghim bừa video view thấp hoặc bịa đặt view.

---

## 3. Cạm Bẫy SKIPPED_LOCKED & Nguyên Tắc Hậu Kiểm Batch

1. **Cơ chế lọc của launcher**:
   - `run_tiktok_upload_batch.ps1` gọi `machine_inventory.py`.
   - Hàm `_filter_locks` quét thư mục `~/.codex/device-locks/`. Nếu tồn tại file lock khớp với `machine` hoặc `serial`, máy bị chuyển sang mảng `skipped` với `status: SKIPPED_LOCKED`.
2. **Cảnh báo Exit Code 0**:
   - Batch hoàn thành bỏ qua tất cả máy vẫn trả về exit code 0.
   - Do đó, BẮT BUỘC parse `summary.csv`:
     ```python
     import csv
     with open(summary_csv_path, 'r', encoding='utf-8') as f:
         reader = csv.DictReader(f)
         for row in reader:
             if int(row["Machine"]) == target_machine:
                 assert row["Status"] == "THÀNH CÔNG" and row["Verified"] == "True"
     ```
3. **Xử lý khi bị SKIPPED_LOCKED**:
   - Kiểm tra xem có tiến trình nuôi feed nào đang giữ lock không (`psutil` hoặc `Get-Process`).
   - Nếu tiến trình nuôi feed đang chạy: chờ kết thúc phiên hoặc điều phối an toàn ngoài ca.
   - Nếu là lock rác (dead PID): thu hồi lock bằng cơ chế reconcile chuẩn trước khi chạy lại runner.
