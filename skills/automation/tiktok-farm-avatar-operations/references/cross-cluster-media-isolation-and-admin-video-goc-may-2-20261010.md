# Cấm Sao Chép Chéo Avatar Kibe Sang Admin & Cách Ly Kho Media (2026-10-10)

## 1. Operator Correction & Bối cảnh Sự cố
- **Phản ứng của Operator:** *"Là sao? Tự nhiên lấy của kibe ném qua admin!!?"*
- **Sự cố:** Coordinator thấy kho `D:\TIKTOK-videonuoinick-admin` trên trạm Admin chỉ có 167/640 folder có `avatar.jpg`, vội vàng nén toàn bộ 640 avatar từ trạm Kibe (`D:\TIKTOK-videonuoinick`) thành file `.tar` ném sang Admin và giải nén đè vào `D:\TIKTOK-videonuoinick-admin`.
- **Hậu quả suýt xảy ra:** Làm ô nhiễm chéo ngách toàn bộ 80 máy (201-280) của cụm Admin. Kênh Admin đang đăng học sinh tiểu học (Folder 1) suýt bị đổi thành avatar thanh niên đeo kính râm ôm mèo reaction hài hước của Kibe!

---

## 2. Invariant Cách Ly Kho Media Giữa Hai Cụm Kibe & Admin
Hai cụm máy chủ Kibe và Admin vận hành **hai kho nội dung hoàn toàn độc lập**, tuyệt đối không dùng chung hay copy đè qua lại:

| Thuộc tính | Cụm Kibe (Máy 1 - 80) | Cụm Admin (Máy 201 - 280) |
|---|---|---|
| **Kho Video Gốc (Raw)** | `D:\video goc` | `D:\video goc may 2` |
| **Kho Media Nuôi (Render/SSOT)** | `D:\TIKTOK-videonuoinick` | `D:\TIKTOK-videonuoinick-admin` |
| **Sổ cái Workbook** | `D:\OneDrive\TaadaaData\kibe\Tik1..8.xlsx` | `D:\OneDrive\TaadaaData\admin\Tik1..8.xlsx` |
| **Config Runtime** | `config-machine-62.yaml` / `kibe.yaml` | `config-admin.yaml` / `admin.yaml` |
| **Trích xuất Avatar** | `_make_avatar.py` đọc `D:\video goc` | `_make_avatar.py` đọc `D:\video goc may 2` |

**CẤM TUYỆT ĐỐI:**
- CẤM sao chép đè file `avatar.jpg` hoặc folder media từ Kibe sang Admin (`TIKTOK-videonuoinick-admin`).
- CẤM sao chép đè từ Admin về Kibe.
- Mỗi cụm chỉ được trích xuất avatar độc bản từ **chính kho video gốc của cụm đó**.

---

## 3. Kiến Trúc Phân Giải Đường Dẫn Runtime Trên Admin

### A. Phân giải Avatar (`path_resolver.py`):
```python
def resolve_avatar_path(media_source_root: Path, folder_video: Any, video_goc: Any = None) -> Path:
    if video_goc is not None:
        goc_value = _normalize_folder_video(video_goc)
        if goc_value:
            for goc_root in (Path(r"D:\video goc"), Path(r"D:\video goc may 2")):
                goc_folder = goc_root / goc_value
                candidates = [goc_folder / name for name in AVATAR_NAMES if (goc_folder / name).is_file()]
                if len(candidates) == 1:
                    return candidates[0]
```
- Trên máy chủ Admin, `D:\video goc` không tồn tại (`exists: False`).
- `D:\video goc may 2` tồn tại (`exists: True`).
- Khi workbook đã khóa cứng `video_goc = folder_video`, bot runner tự động bốc avatar chuẩn từ `D:\video goc may 2\<folder>\avatar.jpg`.
- Nếu không có ở kho gốc, runner fallback sang `search_roots`:
  - `D:\TIKTOK-videonuoinick` không tồn tại trên Admin.
  - Runner bốc từ `D:\TIKTOK-videonuoinick-admin` (chính là `media_source_root` trong `config-admin.yaml`).

### B. Python Runtime & Công cụ Trích xuất trên Admin (`_make_avatar.py`):
- `DEFAULT_SOURCE_ROOT` tự động nhận diện `D:\video goc may 2` khi folder này tồn tại.
- **Python Runtime:** Python mặc định của hệ thống Admin thiếu thư viện `cv2` (OpenCV).
- **BẮT BUỘC** gọi python runtime đã pin của runner:
  `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe D:\Taadaa\Tiktok-video\scripts\_make_avatar.py <folder> --source-root "D:\video goc may 2"`
- Lệnh này chạy độc lập trên Admin, trích xuất tức thì <5s, sinh `avatar.jpg` đúng nhân vật/video của cụm Admin.

---

## 4. Quy Trình Cứu Vãn Khi Phát Hiện Bị Ô Nhiễm Chéo (Reversion Runbook)
Nếu phát hiện một session trước lỡ copy đè avatar từ Kibe sang Admin:
1. Quét danh sách các folder có avatar gốc trong `D:\video goc may 2`.
2. Khôi phục đè toàn bộ avatar gốc từ `D:\video goc may 2` sang `D:\TIKTOK-videonuoinick-admin`.
3. Xóa bỏ (`unlink()`) các file `avatar.jpg` trong `D:\TIKTOK-videonuoinick-admin` ở các folder không thuộc `video goc may 2` (loại bỏ tàn dư Kibe).
4. Xác minh hash MD5 giữa `D:\TIKTOK-videonuoinick-admin\<folder>\avatar.jpg` và `D:\video goc may 2\<folder>\avatar.jpg` khớp 100%.
