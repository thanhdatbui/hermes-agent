# Random Render Pipeline Anti-Detection Architecture (2026-08-27)

## 1. Bản chất sự khác biệt: Random Render vs Fixed Preset ("Ông Anh")

| Tiêu chí | Bản "Ông Anh" (CapCut/Fixed Preset) | Bản Random Render (Tối ưu Anti-Detect) |
| :--- | :--- | :--- |
| **Dấu vân tay (Fingerprint)** | Cố định 100% qua hàng nghìn video (cùng zoom, curves, pitch) | Biến thiên ngẫu nhiên theo `seed` riêng biệt cho từng video |
| **Filter Graph** | Nặng CPU do `geq` (side_gradient) và `gblur` | 100% native C filters tối ưu SIMD/AVX2 |
| **Tốc độ Render** | Chậm (15-25 FPS) | Siêu nhanh (60-120+ FPS) |
| **Hiệu quả Anti-Detect** | Kém (Dễ bị AI gom cụm cluster reup) | Cao (Phá vỡ pHash, SSIM, Chromaprint, Frame sequence) |

---

## 2. Các kỹ thuật Anti-Detection nâng cấp chuẩn hóa (2026-08-27)

### A. Temporal Head & Tail Trim (Đồng bộ A/V trước Speed Transform)
- **Cơ chế**: Cắt ngẫu nhiên $0.20\text{--}0.60\text{s}$ ở đầu (`trim_start_s`) và đuôi (`trim_end_s`) cho video có `duration >= 8.0s`.
- **Phá vỡ**: Frame Sequence Matching (không còn khớp frame 0 với video gốc).
- **Bất biến A/V**:
  $$audio\_tempo = \frac{speed\_factor}{pitch\_factor}$$
  - Đảm bảo hệ số co giãn thời gian của audio ($pitch\_factor \times audio\_tempo$) luôn khớp chính xác với hệ số co giãn thời gian của video ($speed\_factor$).
  - `atempo` phân rã thành chuỗi các stage $\in [0.5, 2.0]$.

### B. In-line Spectral Noise Floor & Adaptive Nyquist
- **In-line Noise Floor**:
  `aeval='val(ch)+0.0002*(random(0)-0.5)':c=same`
  - Bơm một lớp tạp âm vi mô ($\approx -40\text{dBFS}$) không nghe thấy bằng tai nhưng làm nhiễu hoàn toàn Spectrogram / AcoustID ngay cả khi TikTok gộp stereo về mono downmix.
- **Adaptive Nyquist Filter**:
  - High-pass: `highpass=f=50..70` (Hz).
  - Low-pass: $max\_safe\_f = \text{int}(target\_sample\_rate \times 0.45)$. Cutoff được tính theo sample rate đích ($44.1\text{k}$ hoặc $48\text{k}$), luôn nằm an toàn dưới tần số Nyquist.

### C. Sample-Peak Safety & Clamping Đích ($D_{out}$)
- **Thời lượng Đích**: $D_{out} = (trim\_end - trim\_start) / speed\_factor$.
- **Limiter & Clamping**:
  `alimiter=limit=0.95:level=disabled:asc=1:latency=1,apad=whole_dur={D_out},atrim=0:{D_out},asetpts=PTS-STARTPTS`
  - Giữ headroom an toàn chống clipping, bù padding nếu thiếu và loại bỏ triệt để phần đuôi thừa của Reverb/Chorus.

---

## 3. Auto-Aspect Detection & fit_pad cho Video Ngang 16:9 (Bảo toàn 100% Khung hình)

### A. Vấn đề của `fill_crop` với Video Ngang (16:9)
- Khi video nguồn là màn hình ngang ($DAR > 1.0$, ví dụ $1920\times 1080$), nếu áp layout `fill_crop` mặc định của màn hình dọc 9:16 ($1080\times 1920$), video sẽ bị phóng to kín chiều dọc và cắt mất tới 70% chiều ngang ở 2 bên $\rightarrow$ mất chủ thể, mất mặt người, cắt đứt logo/chữ/bản tin.

### B. Giải pháp Auto-Aspect (`fit_pad`)
1. **Tính Display Aspect Ratio ($DAR$) chuẩn xác**:
   - $DAR = \frac{\text{width} \times \text{SAR}_x}{\text{height} \times \text{SAR}_y}$ (hoán đổi width/height khi có `rotation` trực giao 90/270).
   - Tận dụng cơ chế autorotate mặc định của FFmpeg.
2. **Filter Graph chuẩn hóa Square-Pixel & Căn giữa**:
   - Nếu $DAR > 1.0$ (Video ngang) và layout không chỉ định `fit_black`:
     `scale=trunc(iw*sar/2)*2:ih,setsar=1,scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1`
   - Giữ nguyên 100% chi tiết hình ảnh, chữ, đồ họa với 2 viền đen letterbox trên dưới chuẩn TikTok/CapCut.
   - Video dọc ($DAR \le 1.0$) tiếp tục áp dụng `fill_crop` tràn viền.

---

## 4. Quản lý Batch Render & Trạng thái Nick
- **Máy thiếu ID (`MISSING_ID`)**: Vẫn render bình thường vào đúng `Folder Video`. Không chặn/skip render vì ID sẽ được nạp và sync sau vào workbook trước khi upload.
- **Tiến trình Supervisor nối tiếp (`tik4_then_tik5.py`)**: Nhận diện process cha PowerShell/Python thật (tránh bắt nhầm các tiến trình chẩn đoán/con của Hermes), tự động trigger batch kế tiếp khi batch trước đạt đủ 80/80 folder hợp lệ.
- **Dừng Cron khi hoàn tất**: Sau khi toàn bộ 80/80 folder đạt chuẩn, tự động dọn dẹp cron watchdog để tránh gửi báo cáo thừa.

