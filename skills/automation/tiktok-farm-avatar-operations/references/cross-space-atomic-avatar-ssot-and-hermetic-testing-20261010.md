# Cross-Space Atomic Avatar SSOT & Hermetic Testing Discipline (2026-10-10)

## 1. Bối cảnh & Căn nguyên Lệch Avatar
Trên Taadaa Farm, tồn tại hai không gian số hoàn toàn độc lập:
- **Không gian Render (`Folder Video`):** Đánh số `(Máy-1)*8 + Tik` (từ 1 đến 640). Đây là thư mục lưu video thành phẩm đã render tại `D:\TIKTOK-videonuoinick\<Folder Video>`, chính là video đang được bot upload đăng lên kênh TikTok của tài khoản.
- **Không gian Cào Thô (`video gốc`):** Đánh số `(Tik-1)*80 + Máy`. Thư mục video gốc tại `D:\video goc\<video gốc>` là nguồn cào Douyin/TikTok ban đầu.

### Tử huyệt trong Code cũ
1. `path_resolver.py` xếp `search_roots = [media_source_root, Path(r"D:\TIKTOK-videonuoinick")]`. Khi `media_source_root` là `D:\video goc`, tool đi ghép `D:\video goc\<Folder Video>\avatar.jpg`. Thư mục này thuộc về video thô của MỘT TÀI KHOẢN KHÁC, làm bot upload bốc nhầm avatar của tài khoản đó (ví dụ kênh gym nam bốc nhầm avatar nữ review phim).
2. `regenerate_unique_avatars.py` kiểm tra `ROOT_VG` trước `ROOT_NUOI`, làm cắt avatar từ video thô của tài khoản khác rồi ghi đè sang `ROOT_NUOI`.
3. Khi sao chép sang `video goc`, code thiếu `mkdir(parents=True, exist_ok=True)` làm văng ngoại lệ `EXC` nếu thư mục đích chưa tồn tại.
4. Ghi đè file trực tiếp vào `avatar.jpg`: nếu tiến trình bị timeout (180s) giữa chừng, file ảnh hỏng (0KB hoặc dở dang) nằm lại trên đĩa, làm resolver sau này bốc phải file rác.

---

## 2. Giải pháp Chuẩn hóa Kiến trúc (3 Chốt chặn)

### Chốt chặn 1: SSOT Tuyệt đối trong `path_resolver.py`
```python
def resolve_avatar_path(media_source_root: Optional[Path], folder_video: Any) -> Path:
    folder_value = _normalize_folder_video(folder_video)
    nuoi_root = Path(r"D:\TIKTOK-videonuoinick")
    search_roots = []

    # Nếu caller truyền root tường minh (unit tests / mock) và không phải video goc
    if media_source_root is not None:
        norm_media = str(media_source_root).replace("\\", "/").lower()
        if "video goc" not in norm_media and Path(media_source_root) != nuoi_root:
            search_roots.append(Path(media_source_root))

    if nuoi_root not in search_roots:
        search_roots.append(nuoi_root)

    for root in search_roots:
        folder = root / folder_value
        candidates = [folder / name for name in AVATAR_NAMES if (folder / name).is_file()]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise PathResolverError(f"Multiple avatar files found in folder: {folder}")

    root_display = str(media_source_root) if media_source_root is not None else str(nuoi_root)
    raise PathResolverError(f"Avatar file not found in folder: {root_display}\\{folder_value}")
```
* **Bảo vệ `media_source_root is None`:** Dùng `root_display` tránh crash `TypeError`.
* **Loại trừ tuyệt đối `video goc`:** Bất kỳ path nào chứa `video goc` đều bị loại bỏ khỏi `search_roots`.

### Chốt chặn 2: Quét Trùng lặp Kép & Ghi Nguyên tử trong `regenerate_unique_avatars.py`
1. **Quét trùng lặp cả 2 kho:**
   Quét MD5 hash trên cả `ROOT_NUOI` và `ROOT_VG` để không bỏ sót bất kỳ nhóm trùng nào giữa hai kho.
2. **Ghi nguyên tử (Atomic Write):**
   ```python
   tmp_target = src_root / str(folder) / "avatar.jpg.tmp"
   final_target = src_root / str(folder) / "avatar.jpg"
   tmp_target.parent.mkdir(parents=True, exist_ok=True)
   ...
   # Sau khi sinh ảnh thành công:
   os.replace(tmp_target, final_target)
   ```
   Nếu tiến trình timeout hoặc lỗi giữa chừng, xóa `tmp_target`, không bao giờ để lại file ảnh dở dang.
3. **Đồng bộ có `mkdir` an toàn:**
   Trước khi `shutil.copy2` sang `nuoi_path` và `vg_path`, bắt buộc gọi `parent.mkdir(parents=True, exist_ok=True)`.

### Chốt chặn 3: Kiểm chứng Hermetic Unit Test
Trong `tests/test_tiktok_workflow.py`:
- Dùng `monkeypatch` giả lập `D:\video goc` và `D:\TIKTOK-videonuoinick` sang `tmp_path`.
- Kiểm chứng:
  * Khi truyền `Path(r"D:\video goc")` làm `media_source_root`, resolver bắt buộc bỏ qua kho video gốc và chỉ bốc từ `fake_videonuoinick`.
  * Khi truyền `None` làm `media_source_root`, resolver xử lý êm thuận không crash `TypeError`.
  * Khi thư mục rỗng, báo lỗi rõ ràng `Avatar file not found in folder`.
