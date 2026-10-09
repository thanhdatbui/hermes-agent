# Render Root SSOT & Avatar Cross-Folder Poisoning Remediation (2026-10-09)

## 1. Bản Chất Bẫy Lệch Avatar Toàn Farm (Cross-Folder Poisoning)
### Hiện tượng
* Trên TikTok Phone Farm, nhiều tài khoản đăng video một ngách (ví dụ: bạn nữ áo thể thao đỏ kính cận), nhưng avatar lại là ngách khác (nam thanh niên gym đeo kính râm gồng bắp tay).
* Dù trước đó đã chạy tái tạo avatar nhiều lần, tình trạng lệch vẫn tái diễn trên nhiều máy.

### Căn nguyên kỹ thuật
1. **Lệch hệ số đánh số (Dual Numbering Spaces):**
   * Trong 8 workbook (`Tik1.xlsx` đến `Tik8.xlsx`):
     - `Folder Video` = `(Máy - 1) * 8 + Tik` (chia theo từng máy vật lý 1..80).
     - `video gốc` = `(Tik - 1) * 80 + Máy` (chia theo từng ca cào video 1..8).
   * 637 / 640 tài khoản trên farm có `Folder Video != video gốc` (ví dụ Máy 62 Tik 3: `Folder Video = 491`, nhưng `video gốc = 222`).
2. **Path Resolver ưu tiên nhầm kho video thô (`path_resolver.py`):**
   * Trong `path_resolver.py`:
     ```python
     search_roots = [media_source_root, Path(r"D:\TIKTOK-videonuoinick")]
     ```
   * Biến `media_source_root` được cấu hình là `D:\video goc`.
   * Khi resolve avatar cho nick có `Folder Video = 491`, tool chạy vào `D:\video goc\491\avatar.jpg` để tìm kiếm trước!
   * Nhưng `D:\video goc\491` lại là video thô của một tài khoản KHÁC (Máy 11 Tik 7)!
   * Do đó, avatar của tài khoản khác bị bốc nhầm và upload lên máy!
3. **Tool tạo avatar tự động (`regenerate_unique_avatars.py`):**
   * Kiểm tra `ROOT_VG` (`D:\video goc`) trước `ROOT_NUOI` (`D:\TIKTOK-videonuoinick`).
   * Cắt avatar từ video thô của thư mục trùng số rồi ghi đè vào thư mục render của nick khác.

---

## 2. Giải Pháp Khóa Cứng Cơ Chế (Single Source of Truth - SSOT)
1. **`D:\TIKTOK-videonuoinick\<Folder Video>` là SSOT duy nhất:**
   * Mọi video đăng tải lên TikTok đều nằm trong `D:\TIKTOK-videonuoinick\<Folder Video>`.
   * Avatar đại diện cho kênh BẮT BUỘC phải lấy từ chính thư mục render này.
2. **Khóa chết `path_resolver.py`:**
   * Loại bỏ hoàn toàn mọi root chứa `"video goc"` khỏi danh sách tìm kiếm avatar.
   * `search_roots` chỉ tìm trong `D:\TIKTOK-videonuoinick / folder_value`.
   * Nếu không tìm thấy avatar trong thư mục render, ném ngoại lệ fail-closed (`PathResolverError`), tuyệt đối không fallback ngầm sang kho video thô.
3. **Khóa chết `regenerate_unique_avatars.py`:**
   * Ưu tiên `ROOT_NUOI` trước `ROOT_VG`. Nếu thư mục render đã có video, bắt buộc trích xuất avatar từ chính video render đó.
4. **Bộ test hồi quy:**
   * `pytest tests/test_tiktok_workflow.py -k resolve_avatar` (3/3 PASS, bao gồm `test_resolve_avatar_never_picks_from_video_goc`).
