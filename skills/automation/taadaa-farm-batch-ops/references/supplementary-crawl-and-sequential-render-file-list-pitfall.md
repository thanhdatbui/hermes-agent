# Quy Trình Cào Bổ Sung & Bẫy Sắp Xếp Lexicographical Khi Render Nối Tiếp (File-List Invariant)

## 1. Bối cảnh & Hiện tượng
Khi một folder trên Farm (ví dụ: Folder 154 - Máy 20, Tik 2) chỉ có 40 clip do vừa chạy hoán đổi nguồn (`--min-videos 40`), trong khi Watchdog (`farm-render-download-watchdog`) áp ngưỡng cứng $\ge 45$ clip khiến báo cáo cụm bị khuyết (`79/80 folder [98.8%]`), người dùng sẽ yêu cầu cào bù thêm clip và render nối tiếp để tròn 80/80 (100%).

---

## 2. Bẫy Chết Người: Sắp Xếp Ký Tự (Lexicographical Sorting) Trong `random_batch_render.py`
* **Cơ chế quét mặc định của `scan_input(input_dir)`:**
  `files = sorted((p for p in input_dir.rglob("*") if p.is_file()), key=lambda p: str(p).lower())`
* **Hậu quả khi thêm file mới trực tiếp vào `input_dir`:**
  - Nếu kho video gốc `D:\video goc\<raw>` đang có `1.mp4` đến `40.mp4`, thứ tự sắp xếp chuỗi là:
    `1.mp4`, `10.mp4`, `11.mp4`, ..., `40.mp4`, `5.mp4`, `6.mp4`, `7.mp4`, `8.mp4`, `9.mp4`.
  - Khi cào thêm `41.mp4` đến `50.mp4` và thả chung vào `input_dir`, hàm `sorted()` sẽ chèn `41.mp4` ... `50.mp4` vào **giữa** `40.mp4` và `5.mp4`!
  - Khi chạy lại lệnh render với `--start-seq 22`, toàn bộ ánh xạ số thứ tự đầu ra của `5.mp4` (trước đây là `57.mp4`) sẽ bị đẩy lệch sang `67.mp4`. Điều này làm phá vỡ hoàn toàn cơ chế `--resume-verify-existing`, gây render đè lung tung hoặc lệch con trỏ đăng video của nick trên farm.

---

## 3. Giải Pháp Bắt Buộc: Cơ Chế `--file-list` Cách Ly Tuyệt Đối
Để bảo toàn 100% các video đã render trước đó (`22.mp4` $\rightarrow$ `61.mp4`), BẮT BUỘC dùng cờ `--file-list`:

1. **Tải file mới vào kho gốc:**
   - Đánh số tiếp nối: `41.mp4`, `42.mp4`, ..., `50.mp4`.
   - Kiểm tra chuẩn `ffprobe` luồng video và dung lượng > 100 KB.
2. **Tạo danh sách file riêng biệt (`supplement_file_list.txt`):**
   ```text
   D:/video goc/100/41.mp4
   D:/video goc/100/42.mp4
   ...
   D:/video goc/100/50.mp4
   ```
3. **Kích hoạt render nối tiếp với `--start-seq` mới:**
   ```bash
   python D:/Taadaa/Tiktok-video/scripts/random_batch_render.py \
     --input-dir "D:/video goc/100" \
     --output-dir "D:/TIKTOK-videonuoinick/154" \
     --preset "D:/Taadaa/Tiktok-video/presets/preset_owner.json" \
     --randomize \
     --resume-verify-existing \
     --slot 1 \
     --machine-id 19 \
     --start-seq 62 \
     --file-list "D:/Taadaa/Tiktok-video/supplement_file_list.txt" \
     --run-id "kibe-m20-slot2-f100-supp"
   ```
   *Kết quả:* Script chỉ render đúng 10 task cho 10 file mới, sinh ra chính xác từ `62.mp4` đến `71.mp4`, hoàn toàn không chạm vào hay quét lại các file từ `22.mp4` đến `61.mp4`.

---

## 4. Đồng Bộ Sổ Sách Hai Đầu & Bẫy Atomic Replace Excel
Sau khi render xong 10 clip bổ sung, việc cập nhật sổ cái `Tik{N}.xlsx` có 2 bẫy trọng yếu:
1. **Đồng bộ song song cả 2 sheet:**
   - Sheet `TaiKhoan`: Dòng máy là `row = machine + 1` (do dòng 1 là tiêu đề). Cập nhật cột `Render MP4` (cột 11 / index 10) lên số lượng thực tế mới (ví dụ: 50).
   - Sheet `Hashtag theo Folder`: Dòng có `Folder Nguồn == folder_raw`. Cập nhật cột `Số Video` (cột 5 / index 4) lên 50.
   - *Bẫy lệch sổ cái:* Nếu chỉ cập nhật sheet `TaiKhoan` mà bỏ sót `Hashtag theo Folder` (hoặc ngược lại), auditor và các công cụ preflight sẽ đánh giá dữ liệu không nhất quán và từ chối nghiệm thu.
2. **Kỹ thuật Atomic Replace chống xung đột OneDrive Sync Lock:**
   Khi lưu workbook nằm trên OneDrive, gọi trực tiếp `wb.save(path)` có thể bị OneDrive chiếm lock hoặc nuốt thay đổi ngầm. BẮT BUỘC lưu qua file tạm và hoán đổi atomic:
   ```python
   tmp_path = workbook_path.with_suffix('.tmp.xlsx')
   wb.save(tmp_path)
   wb.close()
   os.replace(tmp_path, workbook_path)
   ```

---

## 5. Quy Chuẩn Hồ Sơ Nghiệm Thu Chốt Phiên (Closeout Gate Evidence Contract)
Khi người dùng phát lệnh "Done" / "Chốt phiên" trên tác vụ vận hành media farm (không có git code diff), reviewer `closeout_gate.py` sẽ chấm REJECTED nếu chỉ cung cấp mô tả văn bản suông. Để đạt điểm APPROVED ($\ge 85/100$), hồ sơ bằng chứng (`--input evidence.txt`) BẮT BUỘC gồm đủ 5 trụ cột:
1. **Kiểm chứng Filesystem Độc Lập:** Danh sách và tổng số file thực tế, kiểm tra tính liên tục không khuyết số (`assert seqs == list(range(start, end + 1))`).
2. **Bằng Chứng Bảo Toàn MTime (Zero-Overwrite Proof):** Đối chiếu mtime xác minh các clip cũ giữ nguyên thời gian tạo trước đó và nhỏ hơn mtime của các clip mới cào (`max(old_mtimes) < min(new_mtimes)`).
3. **Bảng Dữ Liệu Thô FFprobe (Raw Stream Table):** Xuất bảng probe kiểm tra codec (`h264`), độ phân giải dọc 1080x1920 (9:16) và thời lượng của toàn bộ các clip mới.
4. **Kiểm Chứng Sổ Cái Hai Đầu:** Trích xuất giá trị thực tế sau khi lưu từ cả hai sheet `TaiKhoan` và `Hashtag theo Folder` chứng minh số lượng đã khớp với filesystem.
5. **Nghiệm Thu Thị Giác (Vision Inspection):** Trích xuất frame video bằng ffmpeg (`-ss 00:00:03 -vframes 1`) và soi mắt bằng `browser_vision` xác nhận nội dung đúng chủ đề, không màn hình đen, không lỗi render trước khi đính kèm `MEDIA:`.
