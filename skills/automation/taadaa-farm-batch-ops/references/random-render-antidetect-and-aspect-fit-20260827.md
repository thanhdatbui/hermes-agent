# Random Render Anti-Detection Upgrades & Auto-Aspect Ratio Detection (2026-08-27)

## 1. Tik5 Render Architecture & Slot Mapping
- **Công thức ánh xạ Tik5 (Slot 5, 0-indexed Slot 4)**:
  - Máy $m \in [1, 80]$.
  - Output folder: `D:\TIKTOK-videonuoinick\<F>` với $F = (m - 1) \times 8 + 5$ (dải `5, 13, 21, ..., 637`).
  - Source video gốc: `D:\video goc\<S>` với $S = 320 + m$ (dải `321 .. 400`).
  - Workbook: `D:\OneDrive\TaadaaData\kibe\Tik5.xlsx`.
  - Launcher canonical:
    ```powershell
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tik5_random_render.ps1" -StartMachine 1 -EndMachine 80 -Slot 4 -Parallel 1 -ResumeVerifyExisting -AutoRun
    ```
- **Quy tắc máy thiếu ID**: Máy bị `MISSING_ID` hoặc trống cột ID vẫn render bình thường vào đúng folder output. ID có thể bổ sung vào master sheet sau này mà không làm gián đoạn render.

---

## 2. Nâng cấp Anti-Detection & A/V Sync (Random Render Pipeline)
- **Audio/Video Trim đồng bộ**:
  - Clip $\ge 8.0\text{s}$ được cắt ngẫu nhiên $0.2\text{--}0.6\text{s}$ ở đầu và đuôi trước khi warp tốc độ $\rightarrow$ phá vỡ so khớp Frame 0 mà không làm lệch tiếng.
  - Bất biến $audio\_tempo = \frac{speed\_factor}{pitch\_factor}$ đảm bảo đồng bộ hoàn hảo độ dài hình và tiếng.
- **Chống triệt tiêu khi gộp Mono (In-line Audio Noise Floor)**:
  - Thêm lớp nhiễu vi mô in-line `aeval` ($-40\text{dBFS}$) $\rightarrow$ phá vỡ phổ Chromaprint/AcoustID ngay cả khi TikTok downmix stereo về mono.
- **Adaptive Nyquist Filter**:
  - High-pass ($50\text{--}70\text{Hz}$) và Low-pass ($14.5\text{--}17\text{kHz}$) tự động giới hạn an toàn dưới $\le 0.45 \times \text{sample\_rate}$.
- **Endpoint Clamping & Anti-clipping**:
  - `alimiter=limit=0.95:level=disabled:asc=1:latency=1` kèm `apad` + `atrim=0:D_out` loại bỏ phần đuôi thừa và chống méo tiếng.

---

## 3. Tự động Nhận diện Tỷ lệ Khung hình (Auto-Aspect Detection & `fit_pad`)
- **Vấn đề**: Video ngang 16:9 ($1920\times 1080$) nếu chạy qua layout `fill_crop` dọc 9:16 ($1080\times 1920$) sẽ bị phóng to và cắt mất 70% khung hình ở hai bên trái/phải (mất chữ, logo, trường quay).
- **Cơ chế xử lý tự động**:
  1. `MediaInfo` đọc `rotation` từ `side_data_list` (Display Matrix) fallback sang `tags.rotate`, chuẩn hóa góc âm và góc trực giao $\{0, 90, 180, 270\}$.
  2. Đọc và validate `sample_aspect_ratio` (SAR).
  3. Tính Display Aspect Ratio:
     $$DAR = \frac{w \times \text{SAR}_x}{h \times \text{SAR}_y}$$
     (Nếu `rotation in (90, 270)`: hoán đổi $w, h$).
  4. Phân loại layout:
     - **Nếu $DAR \le 1.0$ (Video dọc 9:16 / vuông 1:1)**: Sử dụng layout `fill_crop` tràn viền.
     - **Nếu $DAR > 1.0$ (Video ngang 16:9 / 4:3)**: Chuẩn hóa square-pixel `scale=trunc(iw*sar/2)*2:ih,setsar=1` $\rightarrow$ scale vừa vặn khung hình $1080\times 1920$ kèm viền đen trên dưới (`fit_pad`), giữ trọn vẹn 100% nội dung không bị cắt xén.
