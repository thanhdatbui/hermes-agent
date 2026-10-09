# Resolve Avatar Search Roots & Manifest Inventory Pitfall (2026-10-09)

## 1. Bẫy resolve_avatar_path ưu tiên D:\video goc\<Folder Video> trước D:\TIKTOK-videonuoinick
### Hiện tượng
Khi tài khoản có `Folder Video` (ví dụ `166`) khác `Video Gốc` (ví dụ `421`):
1. Avatar mới được tạo từ `video goc/421` và copy vào `D:\video goc\421\avatar.jpg` cùng `D:\TIKTOK-videonuoinick\166\avatar.jpg`.
2. Thư mục `D:\video goc\166\avatar.jpg` trước đó vẫn còn file `avatar.jpg` cũ (ví dụ ảnh banner rác "Nhận soạn thảo").
3. Runner `resolve_avatar_path` duyệt theo thứ tự `search_roots`:
   ```python
   search_roots = [media_source_root, Path(r"D:\TIKTOK-videonuoinick")]
   ```
   Do `media_source_root` là `D:\video goc`, runner tìm thấy `D:\video goc\166\avatar.jpg` trước và bốc file cũ này push lên máy!
4. Runner hoàn thành với `status == "AVATAR_SMOKE_SUCCESS"` và `avatar_status == "FORCED_REPLACED_VERIFIED"`, nhưng avatar trên TikTok thực tế vẫn giữ nguyên ảnh rác cũ.

### Giải pháp
- **Đồng bộ triệt để 4 đầu kho:**
  Khi `Folder Video` != `Video Gốc`, bắt buộc copy avatar mới vào cả 4 đường dẫn:
  1. `D:\video goc\<Folder Video>\avatar.jpg`
  2. `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`
  3. `D:\video goc\<Video Gốc>\avatar.jpg`
  4. `D:\TIKTOK-videonuoinick\<Video Gốc>\avatar.jpg`
- **Sức mạnh của Invariant LLM Soi Mắt Đọc Ảnh Trước Khi Gửi:**
  Không bao giờ tin tưởng mù quáng vào status `AVATAR_SMOKE_SUCCESS` hay exit code 0 của runner. Phải luôn soi ảnh `avatar-uploaded-confirmed.png` qua Vision API để xác minh nội dung avatar thực tế đã thay đổi trước khi kết luận thành công.

---

## 2. Bẫy AssignmentManifest & WorkerId gây AssignmentError
### Hiện tượng
Khi truyền `-AssignmentManifest` và `-WorkerId` vào `run_tiktok_upload_avatar.ps1`, nếu manifest trỏ tới file cũ của máy khác (ví dụ `machine:34`), hàm `inventoryArguments` sẽ ném ngoại lệ:
`Machine inventory preflight failed: INVENTORY_ERROR: assignment preflight failed: AssignmentError`.

### Giải pháp
- Khi chạy lẻ theo danh sách máy cụ thể (`-ForceAvatarMachineList "21"`), KHÔNG truyền `-AssignmentManifest` và `-WorkerId` nếu không có manifest được tạo riêng cho đợt chạy đó.
- Lệnh chuẩn cho single-machine avatar upload:
  ```powershell
  echo RUN | powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 `
    -Tik <Tik> -MaxParallel 1 `
    -HostConfigPath D:\Taadaa\machine-config\kibe.yaml `
    -ForceAvatarMachineList "<Machine>"
  ```
