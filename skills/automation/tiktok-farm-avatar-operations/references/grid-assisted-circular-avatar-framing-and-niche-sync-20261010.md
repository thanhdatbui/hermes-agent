# Grid-Assisted Circular Avatar Framing & Niche Sync (2026-10-10)

## Context & Problem
When an operator requests: *"Đổi ava và hashtag kênh này về đúng cho t"*, channels often suffer from two coupled systemic issues:
1. **Niche & Hashtag Drift**: Workbook (`Tik<N>.xlsx`) has a completely wrong `Keyword Video` and `Hashtag Pool` (e.g. `Kinh doanh` / `#kinhdoanh...` on a channel posting handsome Asian actors & idols like Chu Dực Nhiên / Song Kang / Đinh Trình Hâm).
2. **Avatar Drift & Subtitle Poisoning**:
   - The avatar on disk was inherited from an old source claim (e.g. `@tipmakeupeasy` from July 2026).
   - Randomly extracting frames from the current video pool (`D:\TIKTOK-videonuoinick\<Folder>`) frequently hits frames with burnt-in video subtitles (e.g. *"Top cách cười gây thương nhớ..."*, *"Flex em ghệ váy xanh:"*).
   - Naive square face cropping causes hair clipping or chin cut-off when TikTok renders the avatar inside a circular mask.

## Workflow: 4-Step Grid-Assisted Circular Avatar Extraction

### 1. Fast Subtitle Screening with WinRT OCR
Before evaluating aesthetic quality, run fast local WinRT OCR (`python D:/Taadaa/tools/ocr.py <frame.jpg>`) across candidate frames.
- Discard any frame where `ocr_text.strip() != ""` (avoids burnt-in subtitles, watermarks, timestamps).
- Discard frames with severe motion blur (`laplacian_var < 5.0`).

### 2. Grid-Assisted Anatomical Localization via Vision API
When OpenCV Haar Cascade struggles with artistic/filtered idol faces or produces off-center bounding boxes:
- Draw a 100px green coordinate grid over the candidate frame with `cv2.line` and `cv2.putText`.
- Query Vision API (via 9Router `http://127.0.0.1:20128/v1/chat/completions`, model `ag/gemini-3.7-flash-high`) asking for exact [x, y] coordinates:
  - Top of head/hair (`[x_top, y_top]`)
  - Center between eyes (`[x_eyes, y_eyes]`)
  - Bottom of chin (`[x_chin, y_chin]`)
  - Left and right lateral boundaries of head/hair (`[x_left, y_right]`)

### 3. Circular Mask Headroom & Eye-Line Calculation
For a square crop of size `side` centered at `(cx, cy)`:
- **Head Height**: $H_{head} = y_{chin} - y_{top}$.
- **Side Dimension**: Set $side \approx 1.25 \times H_{head}$ to ensure the head fills 40–50% of the avatar without clipping.
- **Center Y**: Set $cy = y_{top} + 0.45 \times side$. This places the eyes along the upper-middle third line of the circle and leaves 5–10% breathing room above the hair.
- **Center X**: Center on the facial midline $cx = x_{eyes}$ (or midpoint between lateral head bounds).
- **Synthetic Circular Preview**: Apply a 512x512 circular mask with white background (`cv2.circle`, `cv2.bitwise_and`) to evaluate the exact mobile appearance.

### 4. Niche & Formula Drift Reconciliation
- Update `Tik<N>.xlsx`:
  - `Folder Video`: keep render folder (e.g. `202`).
  - `video gốc`: lock to equal `Folder Video` (e.g. update `106` $\to$ `202`).
  - `Keyword Video`: set correct niche (e.g. `Douyin Nam thần` / `Trai đẹp`).
  - `Hashtag Pool`: natural trending hashtags (e.g. `#douyin #traidep #namthan #visual #idol #chuducnhien #soaica #tiktokvietnam #xuhuong #fyp #videohay`).
- Synchronize `avatar.jpg` to both storage roots (`D:\video goc\<Folder>\avatar.jpg` and `D:\TIKTOK-videonuoinick\<Folder>\avatar.jpg`).
- Reset `avatar_replace_queue` to `status = 'PENDING'` for watchdog execution.
