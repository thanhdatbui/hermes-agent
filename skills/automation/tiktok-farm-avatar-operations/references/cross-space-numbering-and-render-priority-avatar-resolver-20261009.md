# Cross-Space Numbering Drift & Render-Priority Avatar Resolver (2026-10-09)

## 1. Bản chất sự cố lệch chéo Avatar toàn Farm ("Sao cứ lệch hoài thế")
Trong quá trình vận hành Taadaa Farm, hiện tượng tài khoản TikTok đăng video một đằng (ví dụ video nữ sinh kính cận áo thể thao) nhưng avatar lại hiển thị một nẻo (nam thanh niên gym cơ bắp hoặc banner chữ) lặp lại liên tục do **sự va chạm giữa 2 không gian đánh số**:

1. **Không gian 1: `Folder Video` (Render / Nuôi / Upload)**
   - Đánh số tịnh tiến theo máy vật lý: `(Máy - 1) * 8 + Tik` (chạy từ 1 đến 640).
   - Ví dụ: Máy 62 Tik 3 có `Folder Video = 491`.
   - Toàn bộ video thực tế được bot đăng lên tài khoản TikTok nằm tại `D:\TIKTOK-videonuoinick\<Folder Video>\*.mp4`.

2. **Không gian 2: `video gốc` (Raw Source / Cào nguồn)**
   - Đánh số chia theo từng ca Tik: `(Tik - 1) * 80 + Máy`.
   - Ví dụ: Máy 62 Tik 3 có `video gốc = 222`.
   - Đồng thời, thư mục `D:\video goc\491` trên đĩa lại là nguồn video gốc của **Máy 11 Tik 7** (`Phim Zì Hay` / Milana Vayntrub)!

👉 Có tới **637 / 640 tài khoản** trên farm có `Folder Video != video gốc`.

---

## 2. Lỗi cơ chế trong các Script hiện hành

### Lỗi A: `path_resolver.py` ưu tiên nhầm kho video thô
Trong `scripts/tiktok_workflow/path_resolver.py`:
```python
# LỖI: media_source_root (D:\video goc) đứng đầu danh sách
search_roots = [media_source_root, Path(r"D:\TIKTOK-videonuoinick")]
```
Khi runner tìm avatar cho tài khoản có `Folder Video = 491`:
* Nó ghép `media_source_root / folder_video` $\rightarrow$ `D:\video goc\491\avatar.jpg`.
* Do `D:\video goc\491` tồn tại file `avatar.jpg` (của Máy 11 Tik 7), runner bốc ngay file này và upload lên tài khoản của Máy 62 Tik 3!

### Lỗi B: `regenerate_unique_avatars.py` kiểm tra `ROOT_VG` trước `ROOT_NUOI`
Trong `scripts/regenerate_unique_avatars.py`:
```python
# LỖI: Quét ROOT_VG trước
if (ROOT_VG / str(folder)).exists() and list((ROOT_VG / str(folder)).glob("*.mp4")):
    src_root = ROOT_VG
elif (ROOT_NUOI / str(folder)).exists() and list((ROOT_NUOI / str(folder)).glob("*.mp4")):
    src_root = ROOT_NUOI
```
Khi chạy tái tạo avatar chống trùng, script thấy `D:\video goc\491` có video (của Máy 11), bốc video đó cắt avatar rồi ghi đè sang `D:\TIKTOK-videonuoinick\491\avatar.jpg`. Kết quả: thư mục nuôi bị đầu độc bởi avatar của kênh khác!

---

## 3. Quy chuẩn khắc phục triệt để (The Render-Priority Invariant)

1. **Quy tắc Single Source of Truth cho Avatar:**
   - 100% video xuất hiện trên profile TikTok được lấy từ `D:\TIKTOK-videonuoinick\<Folder Video>`.
   - Do đó, avatar của tài khoản **BẮT BUỘC phải được giải quyết từ `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg` trước tiên**.
   - `search_roots` trong `path_resolver.py` BẮT BUỘC phải đặt `Path(r"D:\TIKTOK-videonuoinick")` lên vị trí đầu tiên.
   - Tuyệt đối không được dò tìm vào `D:\video goc` nếu đường dẫn đó chứa từ khóa `video goc` và `Folder Video != video gốc`.

2. **Quy tắc sinh avatar trong `regenerate_unique_avatars.py`:**
   - Đảo ngược ưu tiên: Kiểm tra `ROOT_NUOI` (`D:\TIKTOK-videonuoinick`) trước `ROOT_VG`.
   - Khi folder render đã có video thành phẩm, avatar BẮT BUỘC phải cắt từ chính các video thành phẩm trong `ROOT_NUOI`.

3. **Đồng bộ Workbook 1:1 khi chuyển kênh độc quyền:**
   - Khi dọn dẹp và cào lại kênh mới cho một folder, cập nhật cột `video gốc` = `Folder Video` để triệt tiêu vĩnh viễn sự chênh lệch chỉ mục giữa 2 không gian số.
