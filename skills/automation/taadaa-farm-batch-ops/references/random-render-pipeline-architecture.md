# Kiến Trúc Pipeline Render Random Chống Trùng Lặp (Tiktok-video)

Repo nguồn: `D:/Taadaa/Tiktok-video`
Các file nòng cốt:
- `scripts/randomize_profile.py`: Sinh profile biến thiên tất định theo seed và slot tài khoản.
- `scripts/random_ffmpeg_builder.py`: Dựng chuỗi lệnh FFmpeg filter complex (geometry, visual, DSP audio).
- `scripts/test_random_pipeline.py`: Bộ 45 test case kiểm định tính bất biến và ranh giới tham số.

---

## 1. Cơ Chế Xử Lý Hình Học & Visual (So sánh với Tool chợ / AI Magician)

Các tool MMO phổ thông (như AI Magician / AI 魔术师) thường zoom/crop tĩnh hoặc xoay ngẫu nhiên dẫn đến việc hở viền đen 4 góc hoặc vỡ tỉ lệ khung hình. Pipeline nội bộ giải quyết bằng toán học:

### A. Overscan & Chống Hở Viền Khi Xoay (Exact Geometry)
- Khi xoay một góc $\theta$ (`rotation_deg` trong khoảng `[-0.20, -0.05]` hoặc `[0.05, 0.20]`, chủ động né `0` bằng `_sample_split_range`), khung hình bị co lại ở các góc.
- Pipeline tính toán độ phóng đại tối thiểu cần thiết để không bao giờ thấy viền đen:
  $$\text{req\_x} = \frac{(W + 2|dx|)\cos\theta + (H + 2|dy|)\sin\theta}{W}$$
  $$\text{req\_y} = \frac{(H + 2|dy|)\cos\theta + (W + 2|dx|)\sin\theta}{H}$$
  $$\text{effective\_zoom} = \max(\text{zoom}, \text{req\_x}, \text{req\_y})$$
- Tọa độ crop được ép chẵn tuyệt đối: `2 * floor(...)` để tương thích hoàn toàn với chuẩn màu subsampling `yuv420p` của H.264/HEVC.

### B. Biến Thiên Màu Tránh Vùng Chết (Split-Range Sampling)
- Hàm `_sample_split_range` chia đều xác suất vào 2 khoảng âm sâu hoặc dương cao, loại bỏ hoàn toàn vùng cận 0 hoặc 1.0 (trung tính):
  - Brightness: `[-0.05, -0.035]` hoặc `[0.035, 0.05]`
  - Contrast: `[0.91, 0.935]` hoặc `[1.065, 1.12]`
  - Saturation: `[0.90, 0.955]` hoặc `[1.045, 1.13]`

### C. Bộ Lọc Kép Unsharp + Luma Noise Động
- Không dùng noise thô làm mờ video. Kết hợp:
  1. `unsharp_primary` (5:5): Tăng độ sắc nét cạnh biên.
  2. `unsharp_clarity` (13:13): Tăng độ trong trẻo (clarity) cho toàn khung hình.
  3. `noise=c0s=N:c0f=t+u:c0_seed=SEED`: Vi nhiễu luma thay đổi theo thời gian và seed tất định.

### D. Dynamic GOP Size (Perceptual Hash Killer)
- `visual["gop_size"] = rng.choice((30, 60, 90, 120, 150))`.
- Thay đổi chu kỳ I-frame/Keyframe làm lệch hoàn toàn cấu trúc gói tin container và thuật toán perceptual hash khung hình của TikTok/Douyin.

---

## 2. Kỹ Thuật Xử Lý Âm Thanh DSP (Audio Fingerprint Disruption)

Các thuật toán quét bản quyền/trùng lặp âm thanh của TikTok, Meta và YouTube dựa vào Chromaprint, AcoustID và Phổ quang (Spectrogram). Pipeline áp dụng các kỹ thuật DSP phòng thu:

### A. Đảo Pha Stereo (Phase Inversion) - Khắc Tinh Của Thuật Toán Hash
- Lệnh: `pan=stereo|c0=c0|c1=-1*c1`.
- Kỹ thuật: Đảo ngược cực pha của kênh âm thanh bên phải.
- Hiệu quả:
  - Người dùng nghe loa điện thoại hoặc tai nghe vẫn nghe bình thường (stereo imaging mở rộng nhẹ).
  - Thuật toán quét tổng hợp phổ (mono sum / acoustic fingerprint) bị triệt tiêu năng lượng sóng âm giữa 2 kênh, làm sụp đổ hoàn toàn mã băm fingerprint so với bản gốc.

### B. Định Tuyến Voice Profile Theo Slot Nick Farm
- `assign_voice_profile(profile, slot)`:
  - Phân bổ theo `slot % len(VOICE_PROFILES)`: `treble`, `normal`, `bass`.
  - Mỗi profile có dải EQ chuyên biệt:
    - `treble`: Cắt sub-bass (`120Hz: -1dB`), boost mid-high (`4kHz: +2dB`, `8kHz: +1dB`). Pitch factor: `[1.008, 1.025]`.
    - `bass`: Boost low (`100Hz: +2dB`), giảm mid (`3kHz: -1dB`). Pitch factor: `[0.980, 0.994]`.
    - `normal`: Pitch factor `[0.990, 1.012]`.
- Giúp các tài khoản khác nhau trên cùng một máy khi đăng cùng tệp video gốc sẽ có phổ âm thanh hoàn toàn độc lập.

### C. Chống Quét Tần Số & Noise Floor
- Highpass (`50 - 70Hz`): Gạt tạp âm rumble.
- Lowpass (`14.5k - 17kHz`): Bọc dưới ngưỡng an toàn Nyquist.
- In-line noise floor: `aeval='val(ch)+0.0002*(random(0)-0.5)':c=same` chèn nền nhiễu siêu vi vô hình vào sóng âm.
- Không gian âm thanh: 2-voice light chorus (`chorus=0.5:0.9:...`) + subtle reverb ngẫu nhiên (50% xác suất).

### D. Chuẩn Hóa Âm Lượng Công Nghiệp
- `loudnorm=I=-16:LRA=11:TP=-3.0` (chuẩn EBU R128 phát sóng).
- Kết hợp `alimiter=limit=0.95:level=disabled:asc=1:latency=1` chống hiện tượng clipping/méo tiếng sau khi EQ và boost âm.

---

## 3. Điểm Khác Biệt Cốt Lõi So Với Tool Crack Thương Mại
1. **An toàn hệ thống:** Không chạy binary `.exe` lạ trên máy Windows farm, tránh nguy cơ trojan/backdoor.
2. **Tự động hóa hoàn toàn:** Nhận batch từ script cha (`run_tikX_random_render.ps1`), render hàng trăm video theo hàng đợi tự động.
3. **Tính toán tất định (Deterministic & Traceable):** Profile render gắn chặt theo seed và slot, cho phép kiểm tra lại và phân tích nguyên nhân nếu có nick bị quét.
