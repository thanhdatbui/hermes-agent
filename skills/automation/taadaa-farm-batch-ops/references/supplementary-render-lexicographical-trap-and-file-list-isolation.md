# Bẫy Lệch Chuỗi Do Sắp Xếp Lexicographical Khi Render Bổ Sung & Quy Chuẩn Cách Ly `--file-list`

## 1. Bản Chất Bẫy Lệch Chuỗi Video (Lexicographical Sort Drift Trap)
Trong pipeline render của Farm (`random_batch_render.py`), khi người dùng chỉ định `--input-dir <raw_dir>` mà không dùng danh sách chỉ định, hệ thống tự động quét folder bằng hàm:
```python
def scan_input(input_dir: Path) -> tuple[list[Path], list[Path]]:
    files = sorted((p for p in input_dir.rglob("*") if p.is_file()), key=lambda p: str(p).lower())
    videos = [path for path in files if path.suffix.lower() in VIDEO_EXTS]
    return videos, assets
```
Khi render lần đầu 40 clip với `--start-seq 22`, thứ tự file raw và output thành phẩm là:
- `1.mp4` $\rightarrow$ `22.mp4`
- `10.mp4` $\rightarrow$ `23.mp4` ... `19.mp4` $\rightarrow$ `32.mp4`
- `2.mp4` $\rightarrow$ `33.mp4` ... `29.mp4` $\rightarrow$ `43.mp4`
- `3.mp4` $\rightarrow$ `44.mp4` ... `39.mp4` $\rightarrow$ `54.mp4`
- `4.mp4` $\rightarrow$ `55.mp4`, `40.mp4` $\rightarrow$ `56.mp4`
- `5.mp4` $\rightarrow$ `57.mp4`, `6.mp4` $\rightarrow$ `58.mp4`, `7.mp4` $\rightarrow$ `59.mp4`, `8.mp4` $\rightarrow$ `60.mp4`, `9.mp4` $\rightarrow$ `61.mp4`

**Hiểm họa khi tải bổ sung (`41.mp4` .. `50.mp4`):**
Nếu lưu thêm file `41.mp4` .. `50.mp4` vào thư mục raw rồi gọi lại `random_batch_render.py` trên toàn folder:
- Theo thứ tự chuỗi chữ cái (`str.lower()`), `41.mp4` đến `49.mp4` sẽ đứng **TRƯỚC** `5.mp4`, `6.mp4`, `7.mp4`, `8.mp4`, `9.mp4`.
- Kết quả: Vòng lặp `enumerate(videos, start_seq=22)` sẽ gán các file `41.mp4` .. `49.mp4` vào các slot thứ tự vốn thuộc về `5.mp4` .. `9.mp4` (từ `57.mp4` trở đi).
- Ngay cả khi có cờ `--resume-verify-existing`, nếu tên output bị lệch file nguồn tương ứng, video cũ có thể bị bỏ sót hoặc video mới bị nhảy số lộn xộn, phá vỡ tính toàn vẹn của chuỗi video nuôi nick.

---

## 2. Quy Chuẩn Cách Ly Bằng Cờ `--file-list` (File-List Isolation Invariant)
Khi cào bổ sung thêm N video (ví dụ tải 10 video từ `41.mp4` đến `50.mp4` để nâng tổng từ 40 lên 50 video đạt chuẩn $\ge 45$ clip):
1. **Tuyệt đối không quét lại toàn bộ input-dir.**
2. **Ghi danh sách đường dẫn tuyệt đối của các file raw mới vào một file tạm:**
   ```text
   D:/video goc/<folder_raw>/41.mp4
   D:/video goc/<folder_raw>/42.mp4
   ...
   D:/video goc/<folder_raw>/50.mp4
   ```
3. **Kích hoạt render với `--file-list` và `--start-seq` nối tiếp chính xác:**
   ```bash
   python D:/Taadaa/Tiktok-video/scripts/random_batch_render.py \
     --input-dir D:/video goc/<folder_raw> \
     --output-dir D:/TIKTOK-videonuoinick/<folder_render> \
     --preset D:/Taadaa/Tiktok-video/presets/preset_owner.json \
     --randomize \
     --resume-verify-existing \
     --slot <slot_idx_0> \
     --machine-id <machine_idx_0> \
     --start-seq <max_seq_cu + 1> \
     --file-list D:/Taadaa/Tiktok-video/supplement_file_list.txt \
     --run-id kibe-m<M>-slot<S>-f<raw>-supp
   ```
4. **Ưu điểm vượt trội:**
   - Bảo toàn 100% các file render đã có từ trước (không chạm vào các file `22.mp4` đến `61.mp4`).
   - Render đúng và chỉ đúng N file mới tải, đánh số tuần tự mượt mà từ `62.mp4` đến `71.mp4`.
   - Thời gian render nhanh gọn (10 video chỉ mất ~2.5 phút thay vì phải đối soát lại toàn bộ 50 file).

---

## 3. Quy Chuẩn Đồng Bộ Sổ Cái 2 Đầu Trong `TikN.xlsx`
Sau khi render bổ sung thành công, file Excel `TikN.xlsx` bắt buộc phải cập nhật đồng bộ ở cả 2 sheet:
1. **Sheet `TaiKhoan`:** Tìm dòng có cột `Máy` tương ứng, cập nhật cột index 10 (`Render MP4`) bằng tổng số lượng file video thực tế hiện có trong `D:\TIKTOK-videonuoinick\<folder_render>`.
2. **Sheet `Hashtag theo Folder`:** Tìm dòng có cột `Folder Goc` tương ứng, cập nhật cột index 4 (`Count` / `Video Count`) bằng tổng số lượng video thành phẩm mới (ví dụ 50).
3. Kiểm tra bằng `data_only=True` để đảm bảo không bị lệch dữ liệu giữa 2 sheet làm Watchdog đọc nhầm số liệu.
