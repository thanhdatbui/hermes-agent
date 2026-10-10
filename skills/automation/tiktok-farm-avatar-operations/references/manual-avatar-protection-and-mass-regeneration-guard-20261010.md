# Manual Avatar Protection & Anti-Mass Regeneration Guard (2026-10-10)

## 1. Problem Context
- Operator feedback: *"Từ h bất kì kênh nào t yêu cầu đổi ava = tay thì k đc script can thiệp nữa (hiện có code kiểu quét folder tạo ava lại hàng loạt, nó dùng fix mấy nick lúc trc, nhưng vô tình phá luôn nick t yêu cầu đổi = tay t chat vs m)"*.
- Root cause: Scripts like `regenerate_unique_avatars.py` and `_make_avatar.py` perform bulk scans over all numerical folders (`/141`, `/338`, etc.) in `D:\TIKTOK-videonuoinick` and `D:\video goc` to resolve MD5 hash collisions or missing avatars.
- When bulk regenerators run, they automatically extract fallback frames (e.g. from `1.mp4` via Haar/YOLO or frame 0) and overwrite `avatar.jpg`, destroying custom avatars that the Operator previously hand-picked or requested via chat.

## 2. Triple-Layer Protection Architecture
1. **Central Protected Registry (`manual_avatar_protected_folders.json`):**
   - Stored at `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json` (and mirrored at `D:/Taadaa/data/`).
   - Contains list of `protected_folders` (e.g. `141`, `338`, `2`, `138`, `148`, `266`, `275`, `398`) and metadata about each account and reason.
2. **In-Folder Atomic Marker File (`.manual_avatar_locked`):**
   - Placed directly inside protected folders: `D:\TIKTOK-videonuoinick\<folder>\.manual_avatar_locked` and `D:\video goc\<folder>\.manual_avatar_locked`.
   - Contains JSON payload detailing operator request timestamp, target username, and niche description.
3. **Core Guard Module (`manual_avatar_guard.py`):**
   - Provides helper functions `get_protected_folders() -> set[int]` and `is_folder_avatar_protected(folder) -> bool`.
   - Checks both central JSON registries and in-folder markers.

## 3. Integration into Bulk Scripts
- In `regenerate_unique_avatars.py`:
  * `find_all_duplicate_folders()` subtracts `protected` folders from candidate duplicate sets (`unprotected_dups = unique_folders - protected`).
  * `process_folder(folder)` guards at entry:
    ```python
    if is_folder_avatar_protected(folder):
        return (folder, True, "SKIPPED_MANUAL_PROTECTED", time.time() - t0)
    ```
- In `_make_avatar.py`:
  * Guards against overwriting protected folders unless `--force` is explicitly passed:
    ```python
    if not args.force and is_folder_avatar_protected(args.folder):
        print(f"[GUARD] Folder {args.folder} là avatar đổi tay thủ công theo yêu cầu operator. Bỏ qua ghi đè tự động.")
        return 0
    ```

## 4. Operational Invariant
- Whenever the operator asks in chat to change an avatar manually for a channel:
  1. Extract and sync the approved avatar to both `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg` and `D:\video goc\<folder>\avatar.jpg`.
  2. Register the folder in `manual_avatar_protected_folders.json`.
  3. Create the `.manual_avatar_locked` marker file in both folders.
  4. Never run bulk unconstrained regenerators without the manual guard active.
