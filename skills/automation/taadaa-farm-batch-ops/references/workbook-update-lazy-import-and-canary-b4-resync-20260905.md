# Workbook Update Lazy-Import Fallback & Canary B4 Re-sync (2026-09-05)

## 1. Triệu chứng & Bối cảnh Sự Cố (Máy 69)
- **Bối cảnh:** Runner upload TikTok (`Tiktok-video`) đã hoàn tất toàn bộ chu trình đăng video: push media, gõ caption, bấm Post, và đã verify thành công trên profile grid (`unique_tiles = 4`, `media_fingerprint_gate = VERIFIED_SUCCESS`).
- **Triệu chứng crash:** Khi chuyển sang state `UPDATE_WORKBOOK`, runner crash:
  ```
  [ERROR] scripts.tiktok_workflow.state_machine: Handler workflow error (attempt 1): [WORKBOOK_UPDATE_FAILED] UPDATE_WORKBOOK: Workbook update failed: No module named 'automation_core.workbook'
  ```
- **Hậu quả:** Task bị đánh dấu FAILED dù video thực tế đã lên profile, khiến con trỏ `Video Đã Đăng` trong workbook Excel (`tik3.xlsx`) không được cập nhật từ 3 lên 4.

## 2. Nguyên nhân Gốc
Trong `scripts/tiktok_workflow/account_source.py:321`:
```python
def update_video_number(self, video_number: int) -> bool:
    ...
    from automation_core.workbook import atomic_workbook_update
```
- **Lazy import không có fallback:** Module `automation_core.workbook` được import trễ ngay trong method ghi workbook. Nếu runner chạy dưới interpreter hoặc sub-environment chưa có `automation-core/src` trong `sys.path`, lệnh import văng `ModuleNotFoundError`.
- **Thiếu preflight import check:** Runner không kiểm tra tính sẵn sàng của hàm ghi workbook ở giai đoạn PREFLIGHT/INIT, khiến sự cố chỉ phát tác ở bước cuối cùng sau khi đã đăng xong video.

## 3. Khắc Phục Chuẩn & Lệnh Canary B4

### A. Fallback Import trong `account_source.py`
Bọc import `atomic_workbook_update` với fallback giải quyết path hoặc atomic save dự phòng:
```python
try:
    from automation_core.workbook import atomic_workbook_update
except (ImportError, ModuleNotFoundError):
    import sys
    from pathlib import Path
    core_src = Path("D:/Taadaa/automation-core/src")
    if core_src.exists() and str(core_src) not in sys.path:
        sys.path.insert(0, str(core_src))
    try:
        from automation_core.workbook import atomic_workbook_update
    except (ImportError, ModuleNotFoundError):
        # Fallback openpyxl atomic update qua tempfile
        import tempfile
        import shutil
        def atomic_workbook_update(path, func, backup=True, lock_timeout=30):
            p = Path(path)
            temp_dir = Path(tempfile.gettempdir())
            temp_path = temp_dir / f"wb_temp_{p.name}"
            shutil.copy2(p, temp_path)
            func(temp_path)
            if backup:
                backup_path = p.with_suffix(f".bak_{int(time.time())}.xlsx")
                shutil.copy2(p, backup_path)
            shutil.move(str(temp_path), str(p))
```

### B. Lệnh Canary B4 Hoàn Tất Cập Nhật Workbook
Khi video đã được verify trên profile grid nhưng chưa ghi workbook, chạy lệnh canary B4 có chỉ định đúng video number:
```bash
cd D:/Taadaa/Tiktok-video && PATH="$PATH:/c/Program Files (x86)/xiaowei/tools" python -m scripts.tiktok_workflow --config "D:\Taadaa\Tiktok-video\config.example.yaml" --workflow-workbook "D:\OneDrive\TaadaaData\kibe\tik3.xlsx" --single-device ce12160c386c913101 --video-number 4 --no-dry-run
```
State machine sẽ nhận diện profile grid đã có 4 video, xác nhận post thành công và thực thi ghi nhận vào workbook.
