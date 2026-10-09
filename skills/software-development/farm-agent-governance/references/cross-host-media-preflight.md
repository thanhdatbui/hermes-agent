# Cross-host media preflight (Central Controller + remote cluster)

When a central controller (Kibe) drives remote Admin devices over ADB TCP, a `video_not_rendered` upload result may be a false alarm if preflight runs on Kibe but the configured `D:\TIKTOK-videonuoinick-admin` path exists only on Admin.

Validated evidence pattern:
- Watchdog alert grouped machines under `Hết video/Cần cào`.
- Direct SSH to `admin-farm` showed the render root existed and target files such as `1/3.mp4`, `17/3.mp4`, and `25/2.mp4` returned `Test-Path=True`.
- The controller's local path was absent, proving a filesystem-locality mismatch rather than missing media.

Required diagnosis:
1. Treat watchdog text as a symptom, not proof of missing media.
2. Identify where the Python preflight executes and where the media physically lives.
3. Verify the target on the owning host with an O(1) `Test-Path`/stat or the remote render watchdog.
4. If remote media exists, use a verified UNC/SMB path or execute the upload hook on the media-owning host. Do not use a remote host's local drive letter from the controller.
5. Report the two-host evidence separately: controller-local check versus remote-owner check.
