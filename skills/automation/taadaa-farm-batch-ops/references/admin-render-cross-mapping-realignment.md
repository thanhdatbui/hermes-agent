# Admin Render Cross-Mapping & 1-to-1 Misalignment Recovery

## Bối cảnh & Bản chất Lỗi (The 1-to-1 Trap)
Trong kiến trúc Farm Taadaa 8 Tik (cả Kibe lẫn Admin):
- **Cột D (Folder Video / Output Root)**: Thư mục chứa video thành phẩm mà bot nuôi nick trên thiết bị thực tế sẽ trỏ vào để upload (`D:\TIKTOK-videonuoinick` hoặc `D:\TIKTOK-videonuoinick-admin`). Trải dài từ 1..640.
- **Cột E (Source / Video Gốc)**: Thư mục chứa video gốc thô tải về từ các kênh YouTube Shorts/TikTok (`D:\video goc` hoặc `D:\video goc may 2`). Trải dài từ 1..640.
- **Quy tắc cốt lõi**: `Folder Video (Out)` và `Video Gốc (Src)` **KHÔNG HỀ TRÙNG NHAU 1-1** (trừ duy nhất Máy 1 Tik 1: Out 1 <- Src 1).
  - Ví dụ trên Admin:
    - Máy 202 Tik 1 (Row 1): Out = 9, Src = 2
    - Máy 203 Tik 1 (Row 1): Out = 17, Src = 3
    - Máy 201 Tik 2 (Row 2): Out = 2, Src = 81
    - Máy 203 Tik 6 (Row 6): Out = 22, Src = 403

## Bẫy Lập Trình (Pitfall)
Khi viết script worker render hàng loạt (như `run_admin_render_worker.py`), cấm tuyệt đối viết theo kiểu duyệt thư mục đĩa thô:
```python
# ❌ LỖI NGHIÊM TRỌNG: LẤY SRC_ID XUẤT THẲNG SANG OUT_ID CÙNG TÊN
for d in vg_root.iterdir():
    out_d = rr_root / d.name  # d.name là folder video gốc!
```
Hậu quả:
1. Video gốc `Src 2` (Gái xinh/Sự kiện) lại bị tống vào `Out 2` (vốn là của Máy 201 Tik 2 - Niche Bếp Việt).
2. Thư mục `Out 9` (Máy 202 Tik 1 cần video từ Src 2) bị bỏ đói, không có video để đăng.
3. Tất cả các slot từ Tik 2 đến Tik 8 bị rỗng đạn hoặc đăng sai niche, dẫn tới nick bị tụt view, chết đề xuất.

## Chuẩn Canonical: Render Theo Mapping Excel 8 Tik
Mọi worker render bắt buộc phải đọc trực tiếp cấu hình từ `Tik1.xlsx` .. `Tik8.xlsx`:
```python
# ✅ CHUẨN CANONICAL:
for slot in range(1, 9):
    wb = openpyxl.load_workbook(f"D:/OneDrive/TaadaaData/admin/Tik{slot}.xlsx", data_only=True)
    ws = wb["TaiKhoan"]
    for r in ws.iter_rows(values_only=True):
        m_id = int(r[0])
        out_id = int(r[3])  # Cột D: Folder Video Thành Phẩm
        src_id = int(r[4])  # Cột E: Folder Video Gốc
        niche = r[5]
        
        in_dir = vg_root / str(src_id)
        out_dir = rr_root / str(out_id)
        
        # Tham số CLI chuẩn hóa:
        # slot: 0..7 (tính theo (slot - 1) % 8)
        # machine-id: 0..79 (tính theo (m_id - 201) % 80 cho Admin)
```

## Quy Trình Phục Hồi & Realignment 2 Pha Khi Đã Lỡ Render 1-1
Nếu phát hiện hệ thống đã lỡ render nhầm dạng 1-1 từ `Src N` sang `Out N`, **KHÔNG ĐƯỢC XÓA BỎ LÀM LẠI TỐN CPU**, mà thực hiện di chuyển (realignment) qua thư mục trung gian `_realign_staging`:

1. **Xây dựng Sổ cái đối soát**:
   - `map_src_to_out[src_id] -> (slot, m_id, target_out, niche)`
   - `map_out_to_src[out_id] -> (slot, m_id, src_id, niche)`
2. **Phase 1 (Staging Isolation)**:
   - Quét tất cả folder có clip trong `rr_root`. Folder nào có `current_id != target_out` thì `shutil.move(rr_root / current_id, staging_root / target_out)`.
   - Việc chuyển hết vào Staging giúp giải phóng toàn bộ namespace folder 1..640, tránh ghi đè chéo hoặc xung đột file giữa các thư mục đang chuyển.
3. **Phase 2 (Atomic Return)**:
   - Chuyển từ `staging_root / target_out` về `rr_root / target_out`.
   - Nếu thư mục đích đã có sẵn video, kiểm tra số lượng clip để giữ bản đầy đủ nhất hoặc gộp an toàn.
   - Xóa bỏ `staging_root` sau khi hoàn tất.

## Cơ Chế Tự Động Phục Hồi Khi Reset Máy (Reboot Resilience)
Để worker render ngầm trên Admin tự động chạy lại sau khi reset máy mà không cần can thiệp thủ công:
1. **Điều kiện tiên quyết**: `AutoAdminLogon = 1` trên Windows (xác nhận qua `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon`).
2. **Kiến trúc Watchdog + VBScript Zero-Flicker**:
   - Tránh đăng ký Scheduled Task cấp SYSTEM hoặc lệnh yêu cầu tương tác UAC qua non-interactive SSH (dễ bị treo approval hoặc rớt quyền Interactive Desktop).
   - Dùng 1 watchdog Python nhẹ (`watchdog_admin_render.py`): kiểm tra liveness của `run_admin_render_worker.py` qua `psutil`. Nếu đang chạy thì thoát ngay O(1), nếu vắng mặt thì gọi launcher detached (`subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS`).
   - Bọc qua VBScript (`start_render_watchdog.vbs`) sử dụng `WScript.Shell.Run ..., 0, False` để triệt tiêu 100% cửa sổ console nhấp nháy trên màn hình máy Farm.
   - Đặt wrapper VBS vào thư mục Startup người dùng (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`) kết hợp watchdog định kỳ của Hermes để đảm bảo máy khởi động lại là worker tự hồi sinh và render đúng slot.
