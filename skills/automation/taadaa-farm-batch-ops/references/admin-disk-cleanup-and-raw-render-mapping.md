# Admin Farm Disk Cleanup & Raw/Render Mapping Invariants

## 1. Kiến trúc kho video Admin Farm (640 tài khoản / 80 máy x 8 slot)

Farm Admin tổ chức video theo 2 cấu trúc thư mục khác nhau:
- **Thư mục Video Gốc (`D:\video goc may 2\<f_src>`):** Đánh số gom theo Slot (Tik 1..Tik 8).
  - Slot 1 (Tik 1): folder 1 .. 80
  - Slot 2 (Tik 2): folder 81 .. 160
  - ...
  - Slot 8 (Tik 8): folder 561 .. 640
  - Công thức: `f_src = (slot - 1) * 80 + m_idx` (với `slot` ∈ [1..8], `m_idx` ∈ [1..80] tương ứng Máy 201..280).

- **Thư mục Video Render (`D:\TIKTOK-videonuoinick-admin\<f_vid>`):** Đánh số gom theo từng Máy (Máy 201..280).
  - Máy 201 (m_idx=1): folder 1 .. 8 (tương ứng Slot 1..8)
  - Máy 202 (m_idx=2): folder 9 .. 16
  - ...
  - Máy 280 (m_idx=80): folder 633 .. 640
  - Công thức: `f_vid = (m_idx - 1) * 8 + slot`.

## 2. Bẫy chết người: CẤM Map Ngang `N == N`
- Tuyệt đối KHÔNG ĐƯỢC so sánh `D:\video goc may 2\<N>` với `D:\TIKTOK-videonuoinick-admin\<N>`.
  - *Ví dụ:* `f_src = 2` là video gốc của Máy 202 - Slot 1. File render của nó phải nằm ở `f_vid = (2 - 1)*8 + 1 = 9`.
  - Nếu map ngang `2` với `2`, kiểm tra nhầm thư mục render của Máy 201 - Slot 2 (nguồn từ `f_src = 81`). Xóa raw ở `2` sẽ làm mất video gốc chưa render của Máy 202!

## 3. Công thức chuyển đổi chuẩn
```python
def f_src_to_f_vid(f_src: int, machines_per_slot: int = 80, slots_per_machine: int = 8) -> int:
    if f_src < 1 or f_src > machines_per_slot * slots_per_machine:
        raise ValueError(f"invalid f_src={f_src}")
    slot = (f_src - 1) // machines_per_slot + 1
    m_idx = (f_src - 1) % machines_per_slot + 1
    return (m_idx - 1) * slots_per_machine + slot
```

## 4. Script Canonical Dọn Đĩa Farm: `clean_farm_disk.py`
CẤM tự viết script dọn đĩa ad-hoc. Luôn sử dụng script canonical trong repo:
```bash
python D:/Taadaa/tools/clean_farm_disk.py          # Mặc định DRY-RUN (an toàn)
python D:/Taadaa/tools/clean_farm_disk.py --apply  # Thực thi xóa thật
```

Tiêu chuẩn nghiệm thu xóa file:
1. **Dọn Installers/Downloads:** Chỉ xóa `.exe`, `.msi`, `.crdownload` trong `D:\Downloads` và các installer xác định ở gốc `D:\`. Giữ nguyên toàn bộ tài liệu, zip, config.
2. **Dọn Raw Video:**
   - Chỉ xóa raw video trong `D:\video goc may 2\<f_src>` KHI VÀ CHỈ KHI thư mục render đích thật `f_vid = f_src_to_f_vid(f_src)` đã có **≥ 30 clip `.mp4` hoàn tất (dung lượng > 100 KB)**.
   - Chỉ xóa các file raw có tên trùng khớp với file đã render hoàn tất.
   - Giữ nguyên các file chưa render hoặc file không phải video (`avatar.jpg`, `notes.txt`).

## 5. Quy trình khôi phục khi lỡ xóa video raw (Reconcile Video DB)
Nếu video raw bị xóa mất mà SQLite tracking database của downloader vẫn ghi nhận `status='complete'`:
1. Downloader nền sẽ bỏ qua không tải lại, còn Render worker sẽ bỏ qua không render vì thiếu raw -> Nick bị đói video.
2. **Khắc phục ngay lập tức:**
   - Sao lưu database sang file `.bak`.
   - Với mọi `folder_num` (1..640) có số file `.mp4` thực tế trên đĩa `< 35`:
     - Cập nhật folder: `status='pending'`, `video_count = actual_count`.
     - Xóa các bản ghi video ma (file không còn trên đĩa) khỏi bảng `videos` và `perceptual_hashes`.
3. Sau khi reconcile, downloader nền với pool 20 worker sẽ tự động nhận diện `status='pending'` và cào tải bù lại từ link kênh nguồn.
