# Avatar Namespace Collision & Device Media Cache Drift

## 1. Hiện tượng & Vấn đề thực tế (2026-09-11)
Các tài khoản TikTok ở các ca/row khác nhau bị phát hiện trùng ảnh đại diện (avatar) với các account ở Row 1 đã hoạt động từ trước:
- `buithudung2011` (Máy 01, Row 5 - Tik5) dính avatar của `lipsellczaw` (Máy 01, Row 1 - Tik1) hoặc `khnh.vyyyy6` (Máy 05, Row 1 - Tik1 - "bà mập").
- `huehoafi23` (Máy 07, Row 5 - Tik5) dính avatar của account Row 1 khác.

## 2. Nguyên nhân gốc rễ (Root Cause)

### A. Xung đột Namespace trong `resolve_avatar_path`
Trong `scripts/tiktok_workflow/path_resolver.py`:
```python
def resolve_avatar_path(media_source_root: Path, folder_video: Any) -> Path:
    folder_value = _normalize_folder_video(folder_video)
    search_roots = [media_source_root, Path(r"D:\TIKTOK-videonuoinick"), Path(r"D:\video goc")]
    for root in search_roots:
        folder = root / folder_value
        candidates = [folder / name for name in AVATAR_NAMES if (folder / name).is_file()]
        if len(candidates) == 1:
            return candidates[0]
```
- **Quy luật Folder Output vs Nguồn**:
  - `Folder Video` (Output render tại `D:\TIKTOK-videonuoinick`): tính theo `(m-1)*8 + k`.
    - Máy 01, Slot 5 (Tik5) $\rightarrow$ `Folder Video = 5`.
    - Máy 07, Slot 5 (Tik5) $\rightarrow$ `Folder Video = 53`.
  - `video gốc` (Source tại `D:\video goc`):
    - Tik1: `1..80` (bằng số máy $m$). Máy 05 Row 1 $\rightarrow$ `video gốc = 5`. Máy 53 Row 1 $\rightarrow$ `video gốc = 53`.
    - Tik5: `321..400` ($320 + m$). Máy 01 Row 5 $\rightarrow$ `video gốc = 321`.
- **Hậu quả xung đột**:
  Khi tìm avatar cho nick Máy 01 Row 5 với `folder_video = 5`, nếu path resolver tìm vào `D:\video goc\5`, nó sẽ bốc trúng thư mục nguồn của Máy 05 Row 1 (`khnh.vyyyy6`), làm nick Row 5 bị gán nhầm avatar của Row 1 máy khác!

### B. Dính Cache MediaStore / Ảnh chụp cũ trên thiết bị Android
- Khi chạy nhiều tài khoản trên cùng 1 máy vật lý (Máy 01 có cả Row 1 `lipsellczaw` và Row 5 `buithudung2011`):
  - Row 1 đã up avatar từ trước, file ảnh từng push vào `/sdcard/DCIM/Camera/avatar.jpg` hoặc `/sdcard/Download/avatar.jpg`.
  - Nếu trước khi up avatar cho Row 5, script không dọn sạch các file ảnh cũ và cache MediaStore, TikTok Media Picker khi mở lên sẽ hiển thị tile đầu tiên là ảnh cũ của Row 1.
  - Thao tác tap mù tile đầu tiên làm nick Row 5 nhận lại chính avatar của Row 1 cùng máy.

## 3. Quy tắc phòng ngừa & Xử lý chuẩn
1. **Khóa chặt đường dẫn avatar từ Render Output (`path_resolver.py`)**:
   Avatar chuẩn của nick bắt buộc resolve duy nhất từ thư mục render:
   `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`.
   Tuyệt đối **KHÔNG** fallback duyệt mù sang `D:\video goc\<Folder Video>`.
   Trong `scripts/tiktok_workflow/path_resolver.py`:
   - `search_roots` chỉ duyệt qua `[media_source_root, Path(r"D:\TIKTOK-videonuoinick")]`.
   - Bỏ hoàn toàn `Path(r"D:\video goc")` khỏi `search_roots`.
   - Nếu không tìm thấy avatar trong output folder hợp lệ, raise `PathResolverError(f"Avatar file not found in folder: {media_source_root / folder_value}")`.
   - Lệnh verify unit test: `pytest tests/test_tiktok_workflow.py -k test_resolve_avatar -p no:cacheprovider`.
2. **Dọn sạch thiết bị trước khi push avatar**:
   `adb shell rm -f /sdcard/DCIM/Camera/avatar* /sdcard/Download/avatar* /sdcard/_ss*.png`
   Sau khi push file mới vào máy, kích hoạt re-scan:
   `adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/DCIM/Camera/avatar.jpg`
