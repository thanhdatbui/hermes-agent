# Unrendered Source Drift and Cross-Tik Video Collision Triage

## Context & Phenomenon
When an account experiences a severe view suppression (0 view, 80–110 view test floor across all posted videos), the operator may suspect a duplicate video source collision with another farm account.

### Root Cause Mechanism
1. **Config Remapping Without Re-rendering**:
   - In `Tik<N>.xlsx`, an operator or script updates `Video Goc (Nguon Cao)` from old folder $A$ to new folder $B$ (e.g. `F_vid: 8`, updated `F_src: 561`).
   - The new raw videos in `D:/video goc/<B>/` are downloaded, but **never rendered** into `D:/TIKTOK-videonuoinick/<A>/`.
   - The existing render folder `D:/TIKTOK-videonuoinick/<A>/` still retains legacy clips rendered from folder $A$.
2. **Cross-Tik Collision**:
   - Meanwhile, another machine on another slot (e.g. Machine 8, Tik 1) has `F_src: A` and has already posted 30 clips from folder $A$.
   - The runner on Machine 1 Tik 8 posts the stale un-rendered clips from `D:/TIKTOK-videonuoinick/<A>/`, resulting in 100% identical frame-for-frame duplicate posts.
   - TikTok's multimodal duplicate detector flags the second channel as duplicate reup, capping distribution at 0–110 views.

## O(1) Investigation & Verification Protocol

### Step 1: Resolve Target Identity via Dashboard API
Query the local dashboard API at `http://127.0.0.1:1905/api/data` or `/api/history?username=<target>`:
- Obtain `may` (machine ID), `tik` (slot ID), `cluster` (`kibe` or `admin`), and historical posting stats.

### Step 2: Bounded 16-Workbook Audit (No Recursive Scan)
Do not use `glob(recursive=True)` or `os.walk` (violates farm terminal guards). Use the explicit 16-workbook list:
```python
paths = [
    f"D:/OneDrive/TaadaaData/{host}/Tik{s}.xlsx"
    for host in ["kibe", "admin"]
    for s in range(1, 9)
]
```
For each workbook, read the `TaiKhoan` sheet to inspect:
- `Folder Video (Render Dich)` ($F_{vid}$)
- `Video Goc (Nguon Cao)` ($F_{src}$)
- `Keyword Video`
- `Video Đã Đăng`

Identify any collision where:
- Another row has $F_{src} == F_{vid}$ of target, or
- Another row has $F_{src} == F_{src}$ of target.

### Step 3: Frame-Count Proof via OpenCV
Compare video duration and frame count between:
1. Active render folder: `D:/TIKTOK-videonuoinick/<F_vid>/1.mp4`
2. Configured raw folder: `D:/video goc/<F_src>/1.mp4`
3. Fallback raw folder: `D:/video goc/<F_vid>/1.mp4`

```python
import cv2

def get_frames(path):
    cap = cv2.VideoCapture(path)
    fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.release()
    return fc, fc / fps
```
If `fc(render)` matches `fc(video goc / F_vid)` instead of `fc(video goc / F_src)`, the render folder is proven stale and un-rendered from the new source.

## Remediation Workflow
1. Purge stale clips in `D:/TIKTOK-videonuoinick/<F_vid>/`.
2. Render fresh clips from `D:/video goc/<F_src>/` preserving `--start-seq = Video Đã Đăng + 1`.
3. Check avatar consistency: if avatar depicts a different niche/subject than the new video content, extract a clean face/subject frame from the new video and update avatar queue.
