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

## 4. Đồng Bộ Sổ Sách & Nghiệm Thu
Sau khi render xong 10 clip bổ sung:
1. **Kiểm tra kho thành phẩm:** Đảm bảo `len(list(RENDER_DIR.glob("*.mp4"))) >= 45` (ví dụ: 50 clips).
2. **Cập nhật Workbook `Tik{N}.xlsx`:**
   - Sheet `TaiKhoan` (Dòng máy tương ứng): Cập nhật cột `Render MP4` (cột 11 / index 10) lên số lượng thực tế mới (50).
   - Sheet `Hashtag theo Folder` (Dòng folder tương ứng): Cập nhật cột `Count` (cột 5 / index 4) lên 50.
3. **Hậu kiểm Watchdog:** Báo cáo kiểm toán render tiếp theo sẽ tự động ghi nhận cụm đạt chuẩn 100% (80/80 folder $\ge 45$ clip).
