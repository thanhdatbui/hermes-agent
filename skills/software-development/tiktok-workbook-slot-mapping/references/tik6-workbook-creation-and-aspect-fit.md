# Tik6 Workbook Creation, Mapping & Auto-Aspect Fit (2026-08-30)

## 1. Slot 6 Mapping Specifications
- **Slot Index**: Slot 6 (0-based `$Slot = 5` in PowerShell/Python launcher).
- **Workbook Target**: `D:\OneDrive\TaadaaData\kibe\Tik6.xlsx`.
- **Dải Output (`Folder Video`)**: `(máy - 1) * 8 + 6` $\implies 6, 14, 22, 30, ..., 638$.
- **Dải Nguồn (`video gốc`)**: `400 + máy` $\implies 401 .. 480$ (trong `D:\video goc`).
- **Nguồn ID & Device ID**:
  - `ID`: Dòng thứ 6 (Slot 6) của từng máy trong sheet `Tài Khoản` của `taikhoan_dat_v2_updated .xlsx`.
  - `device ID`: Lấy từ `PROXYgandienthoai.xlsx` / master.
  - `Kiểm Tra Dữ Liệu`: `"OK"` nếu có ID hợp lệ, `"MISSING_ID"` nếu trống.
  - `Video Đã Đăng`: Khởi tạo `0`.
- **Hashtag Pool & Niche**:
  - Truy vấn `state.db` theo `folder_num` (401..480) $\implies$ lấy `slug`.
  - Đối chiếu `data/niches_pool.txt` $\implies$ lấy `label` tiếng Việt (ví dụ: `kienthuc` $\rightarrow$ "Kiến thức", `congnghe` $\rightarrow$ "Công nghệ", `vlog` $\rightarrow$ "Vlog đời sống").
  - Gán Hashtag Pool chuẩn 9-13 tags.

---

## 2. Auto-Aspect Detection & `fit_pad` cho Video Ngang 16:9
- **Vấn đề**: Video nguồn gốc dạng ngang ($DAR > 1.0$, ví dụ $1920\times 1080$) khi render sang TikTok dọc 9:16 ($1080\times 1920$) bằng `fill_crop` sẽ bị crop mất tới 70% nội dung 2 bên.
- **Giải pháp chuẩn hóa**:
  1. Tự động tính $DAR = \frac{\text{width} \times \text{SAR}_x}{\text{height} \times \text{SAR}_y}$ (hoán đổi $w, h$ nếu có rotation trực giao 90/270).
  2. Nếu $DAR > 1.0$: Chuẩn hóa square-pixel `scale=trunc(iw*sar/2)*2:ih,setsar=1` rồi chuyển sang `scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1`.
  3. Giữ trọn vẹn 100% chi tiết hình ảnh, người, logo và chữ 2 bên.

---

## 3. Launchers & Watchdogs
- Launcher: `D:\Taadaa\Tiktok-video\run_tik6_random_render.ps1`
- Watchdog: `C:\Users\Kibe\AppData\Local\hermes\scripts\tik6_render_watchdog.py`
- Cronjob: `tik6-render-watchdog` (ID: `5c9fb6336b7b`, `every 60m`, `no_agent: true`).
