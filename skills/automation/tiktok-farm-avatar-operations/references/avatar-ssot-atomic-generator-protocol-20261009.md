# Avatar SSOT and Atomic Generator Protocol (2026-10-09)

## 1. Single Source of Truth (SSOT) Invariant
- **SSOT Location:** `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`.
- **Root Cause of Avatar Drift:**
  - `path_resolver.py` historically prioritized `media_source_root` (`D:\video goc`) over the rendered video folder.
  - Sổ cái Excel bị lệch 99.5% giữa `Folder Video` (`(Máy-1)*8 + Tik`) và `video goc` (`(Tik-1)*80 + Máy`).
  - Khi bốc avatar từ `D:\video goc\<Folder Video>`, hệ thống bốc nhầm video thô của tài khoản khác có cùng chỉ số thư mục nhưng khác ngách/nội dung.
- **Rule:** `D:\TIKTOK-videonuoinick` là gốc tìm kiếm chính duy nhất. CẤM TUYỆT ĐỐI runner bốc avatar từ bất kỳ thư mục nào chứa chuỗi `video goc`.

## 2. Atomic Avatar Generation & Temporary File Protocol
- **Temporary Filename Extension:** Always name temporary image files with valid image extensions (e.g., `avatar.tmp.jpg`), NEVER bare extension suffixes like `avatar.jpg.tmp`. OpenCV / PIL / FFmpeg rely on file extensions to determine format encoders/muxers; omitting `.jpg` causes silent fallback or crashes.
- **Atomic Replace:** Generate into `avatar.tmp.jpg`, then execute atomic replacement via `os.replace("avatar.tmp.jpg", "avatar.jpg")`.
- **Destination Verification on Sync:** When copying generated avatar to secondary backup roots (`D:\video goc`), only copy if the destination directory already exists (`vg_folder.is_dir()`). Do not silently create orphaned or unwanted folders in raw directories.
- **Multi-Root Duplicate Detection:** When scanning for duplicate avatar hashes, scan across BOTH `ROOT_NUOI` and `ROOT_VG` to catch cross-directory hash collisions.
