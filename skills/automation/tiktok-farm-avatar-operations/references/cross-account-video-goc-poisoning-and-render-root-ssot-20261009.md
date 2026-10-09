# Cross-Account Video Gốc Poisoning & Render Root SSOT Invariant (2026-10-09)

## 1. Hiện tượng & Căn nguyên gốc rễ (Root Cause)
Trên toàn bộ Taadaa Farm (640 tài khoản), hệ thống workbook phân chia theo 2 công thức đánh số chéo nhau:
* `Folder Video` (cột 4): `(Máy - 1) * 8 + Tik` (chia theo từng máy vật lý, từ 1 đến 640).
* `video gốc` (cột 5): `(Tik - 1) * 80 + Máy` (chia theo từng ca cào video, từ 1 đến 640).
=> **637 / 640 tài khoản (99.5%)** có số `Folder Video` khác hoàn toàn `video gốc`.

### Bẫy ngộ nhận 2 không gian số:
* Thư mục `D:\video goc\<N>` được đánh số theo **`video gốc`** (kho video thô cào về).
* Thư mục `D:\TIKTOK-videonuoinick\<M>` được đánh số theo **`Folder Video`** (kho video render thành phẩm thực tế bot dùng để đăng bài).
* Trong code cũ của `path_resolver.py`:
  ```python
  # BUG GÂY LỆCH CHÉO TOÀN FARM:
  search_roots = [media_source_root, Path(r"D:\TIKTOK-videonuoinick")]
  ```
  Khi cấu hình `avatar_source_root = D:\video goc`, runner truyền `media_source_root = D:\video goc` kết hợp với `folder_video` (ví dụ 491 của Máy 62 Tik 3).
  Runner kiểm tra `D:\video goc\491\avatar.jpg` trước!
  Tuy nhiên, `D:\video goc\491` lại là video thô của **Máy 11 Tik 7** (kênh phim/vlog gái xinh), trong khi Máy 62 Tik 3 lại là kênh gym nam (`video gốc = 222`).
  Hệ quả: Runner bốc avatar của máy khác gán sang cho máy hiện tại!

Tương tự trong `regenerate_unique_avatars.py`:
  ```python
  # BUG TRONG SCRIPT DEDUP:
  if (ROOT_VG / str(folder)).exists() ...:
      src_root = ROOT_VG
  elif (ROOT_NUOI / str(folder)).exists() ...:
      src_root = ROOT_NUOI
  ```
  Kiểm tra `ROOT_VG` trước dẫn đến việc cắt avatar từ video thô của tài khoản khác rồi ghi đè lên thư mục render của tài khoản hiện tại.

---

## 2. Quy tắc cốt lõi: SSOT Duy Nhất (Single Source of Truth)
* **`D:\TIKTOK-videonuoinick\<Folder Video>` là SSOT DUY NHẤT** cho toàn bộ runtime (Uploader bot, Avatar resolver, Post verifier). Mọi video xuất hiện trên profile TikTok đều xuất phát từ đây.
* Avatar của kênh BẮT BUỘC phải trích xuất từ video trong thư mục render `D:\TIKTOK-videonuoinick\<Folder Video>`.
* CẤM TUYỆT ĐỐI runner tìm hoặc bốc avatar từ `D:\video goc`.

---

## 3. Bản vá cơ chế chuẩn (Đã kiểm chứng Offline Pytest 3/3 PASS)

### Trong `tiktok_workflow/path_resolver.py`:
```python
def resolve_avatar_path(media_source_root: Path, folder_video: Any) -> Path:
    folder_value = _normalize_folder_video(folder_video)
    if not folder_value:
        raise PathResolverError("Folder Video is empty")
    if ".." in folder_value or "/" in folder_value or "\\" in folder_value:
        raise PathResolverError(f"Invalid Folder Video (path traversal): {folder_video}")

    search_roots = []
    norm_media = str(media_source_root).replace("\\", "/").lower() if media_source_root else ""
    # Chặn cứng tuyệt đối kho video goc
    if media_source_root and "video goc" not in norm_media:
        search_roots.append(media_source_root)

    nuoi_root = Path(r"D:\TIKTOK-videonuoinick")
    if nuoi_root not in search_roots:
        search_roots.append(nuoi_root)

    for root in search_roots:
        folder = root / folder_value
        candidates = [folder / name for name in AVATAR_NAMES if (folder / name).is_file()]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise PathResolverError(f"Multiple avatar files found in folder: {folder}")

    raise PathResolverError(f"Avatar file not found in folder: {media_source_root / folder_value}")
```

### Trong `scripts/regenerate_unique_avatars.py`:
```python
def process_folder(folder: int) -> tuple[int, bool, str, float]:
    t0 = time.time()
    src_root = None
    # Ưu tiên kiểm tra video render/nuoi (TIKTOK-videonuoinick) trước
    if (ROOT_NUOI / str(folder)).exists() and list((ROOT_NUOI / str(folder)).glob("*.mp4")):
        src_root = ROOT_NUOI
    elif (ROOT_VG / str(folder)).exists() and list((ROOT_VG / str(folder)).glob("*.mp4")):
        src_root = ROOT_VG
```
