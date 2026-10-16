# Remote Admin Farm (M>=200) Avatar Standardization & Verification Patterns

## 1. Remote Admin Host Config Routing Invariant
When launching batch avatar upload or runner scripts for machines on the Admin cluster (Machine ID $\ge 200$, Serial range `ce...` on host `192.168.110.119:5037`):
- `run_tiktok_upload_avatar.ps1` requires `-HostConfigPath D:\Taadaa\machine-config\admin.yaml`.
- Defaulting to `kibe.yaml` restricts the machine range to `[1, 80]`, causing the runner to immediately skip machine $\ge 200$ with 0 targets launched.
- Dual-folder structure for Admin accounts:
  - Render folder: `D:\TIKTOK-videonuoinick-admin\<Folder Video>`
  - Video gốc folder: `D:\video goc may 2\<video gốc>`
  - Both folders must receive `.manual_avatar_locked` and `.manual_hashtag_locked` flags, and both folder IDs must be registered in `manual_avatar_protected_folders.json` and `manual_hashtag_protected_folders.json`.

## 2. Remote SSH Payload Delivery (WinError 206 Prevention)
When pushing binary/image assets or long scripts across SSH to Admin host:
- **DO NOT** embed large base64 strings directly in command-line arguments `python -c "...{b64}..."`. Windows `CreateProcess` fails with `FileNotFoundError: [WinError 206] The filename or extension is too long`.
- **DO** pipe payloads via `stdin`:
  ```python
  import subprocess, base64

  raw = open(local_avatar_path, "rb").read()
  b64 = base64.b64encode(raw)
  py_script = (
      "import sys, base64; "
      "b = base64.b64decode(sys.stdin.read()); "
      "open(r'D:/TIKTOK-videonuoinick-admin/2/avatar.jpg', 'wb').write(b); "
      "open(r'D:/video goc may 2/81/avatar.jpg', 'wb').write(b); "
      "open(r'D:/TIKTOK-videonuoinick-admin/2/.manual_avatar_locked', 'w').write('1'); "
      "open(r'D:/TIKTOK-videonuoinick-admin/2/.manual_hashtag_locked', 'w').write('1'); "
      "print('SYNC_DONE')"
  )
  cmd = ["ssh", "-o", "BatchMode=yes", "admin-farm", f"python -c \"{py_script}\""]
  res = subprocess.run(cmd, input=b64, capture_output=True, check=True)
  ```

## 3. Haar Cascade False-Positive Trap on Food & Animals
- OpenCV `CascadeClassifier(haarcascade_frontalface_default.xml)` has high false-positive rates on:
  - Food dishes, round plates, bowls of sliced vegetables, cooked tubers.
  - Animals (puppy heads, fur textures on flooring).
- **Mandatory Invariant:** Any face crop candidate extracted via Haar cascade MUST be verified by VQA/vision model (`browser_vision` or `ag_cli.py ask`) with a circular preview mask (512x512 with green circle overlay) BEFORE uploading or setting lock flags.
- Check specifically:
  1. Is there an actual human face?
  2. Does the face sit completely inside the 512x512 circle without clipping the chin or forehead?
  3. Are there text overlays, subtitles, or watermarks touching the face?
