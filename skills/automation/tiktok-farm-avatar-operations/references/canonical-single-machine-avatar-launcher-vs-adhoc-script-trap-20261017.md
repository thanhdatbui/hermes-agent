# Canonical Single-Machine Avatar Launcher vs Ad-Hoc Script Trap (2026-10-17)

## 1. Context & The "Re-Inventing the Wheel" Trap
When an operator asks to change an avatar for an account on a specific machine (e.g. Machine 59, `@vantieu11`):
- **The Bad Coordinator Instinct:**
  - Coordinator notices the active profile on device is currently a different account (e.g. `@thutuan4916` from Tik 8).
  - Coordinator panics about "false target mutation" and decides to write a brand new ad-hoc script (e.g. `execute_m59_avatar.py`) to manually wake device, open switcher, and tap coordinates.
  - Subagents are dispatched to patch this custom script, hitting 600s timeouts, parsing failures, and quota waste.
  - Operator questions: *"Ủa tao nhớ có file up avatar rồi mà sao mày còn đi tạo cái mới? Ý tao là script m59_avatar.py là sao?"*

- **The Ground Truth:**
  - The repository ALREADY has a fully integrated, tested, canonical single-machine avatar runner:
    ```bash
    python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Tik> --machine <Máy>
    ```
  - This runner wraps `D:/Taadaa/Tiktok-video/run_tiktok_upload_avatar.ps1` which invokes `run_tiktok_upload_batch.ps1 -AvatarOnly -ForceAvatarMachineList <Máy>`.
  - The batch engine ALREADY has a built-in `ACCOUNT_SWITCHER` state that automatically parses `Tik<N>.xlsx`, verifies identity, opens the account switcher, and switches to the correct target account before opening "Sửa hồ sơ".
  - Writing ad-hoc single-machine scripts is a severe violation of **REUSE > EXTEND > NEW**.

---

## 2. The Stale Staged Avatar Trap ("Mày có xem hình trước khi gửi tao không?")
- **The Mistake:**
  - Coordinator checks `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg` and assumes it's already a prepared new avatar.
  - In reality, that file was the OLD avatar from a previous cycle (e.g. a picture of an earphone cable) that matched the old avatar currently on the TikTok profile.
  - Coordinator sent preview of the old avatar, triggering operator frustration: *"Mày có xem hình trước khi gửi tao không đấy?"*
- **The Invariant:**
  - NEVER trust existing `avatar.jpg` in `<folder>` without comparing it against the profile or extracting a fresh candidate.
  - ALWAYS extract fresh candidate frames from recent videos in `D:/TIKTOK-videonuoinick/<folder>/*.mp4` (e.g. `1.mp4`, `7.mp4`).
  - Visually inspect with `browser_vision` to confirm it is a human portrait/creator matching the channel content.
  - Synchronize dual SSOT:
    - `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg`
    - `D:/video goc/<folder>/avatar.jpg`

---

## 3. Strict 4-Step O(1) Execution Checklist

When instructed to change an avatar for any single machine/account:

### Step 1: Ground-Truth Lookup O(1)
- Query `D:/Taadaa/data/tiktok_tracker.db` (`account_mapping`, `farm_account_info`):
  Retrieve `(may, tik, folder_video, video_goc)`.

### Step 2: Extract & Verify Fresh Avatar Candidate (Khâu tạo ảnh)
- Extract 2–3 face frames from recent `.mp4` in `D:/TIKTOK-videonuoinick/<folder_video>/`.
- Crop square `512x512` with face centered (40%–60% circle area) and adequate headroom.
- Save circular preview `prev_<folder>.jpg` and inspect via `browser_vision`.
- Send `MEDIA:<path_to_preview>` to operator for confirmation.
- Copy approved image to:
  1. `D:/TIKTOK-videonuoinick/<folder_video>/avatar.jpg`
  2. `D:/video goc/<folder_video>/avatar.jpg`

### Step 3: Launch Canonical Runner (CẤM ĐẺ SCRIPT MỚI)
- Execute the canonical runner in the background:
  ```bash
  python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Tik> --machine <Máy>
  ```
  *(Invoke via `terminal(background=True, notify_on_complete=True, timeout=300)`)*.
- DO NOT create `launch_m<N>.py` or `execute_m<N>.py`.
- DO NOT poll with sleep loops.

### Step 4: Physical Evidence Verification (Gate 6)
- Check run output directory: `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/`.
- Verify `avatar-uploaded-confirmed.png` via WinRT OCR and vision.
- Confirm target username and circular avatar face match.
- Update queue database (`avatar_replace_queue.status = 'DONE'`) and Excel (`Avatar = 'OK'`).
- Deliver final proof with `MEDIA:<path_to_confirmed_image>`.
