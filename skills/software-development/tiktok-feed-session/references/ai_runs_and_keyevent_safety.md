# AI-Runs Resolution & ADB Keyevent Safety Rules

## 1. Xử lý đường dẫn `.ai-runs/latest/summary.txt`
- Thư mục `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs` lưu các phiên chạy theo dạng timestamp (`YYYYMMDD-HHMMSS`), **không có thư mục hay symlink tên `latest`**.
- **CẤM TUYỆT ĐỐI**: Dùng `find`, `os.walk`, `glob(recursive=True)`, `grep -rn` quét sâu đĩa hoặc `.ai-runs` vì số lượng file rất lớn sẽ gây TIMEOUT 900s và làm kiệt quệ session.
- **Cách lấy run mới nhất (non-recursive, tức thì)**:
  ```python
  import os
  base = "D:/Taadaa/tiktok-luot nuoi acc/.ai-runs"
  runs = sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and not d.startswith('.')])
  if runs:
      latest_dir = runs[-1]
      latest_summary = os.path.join(base, latest_dir, "summary.txt")
      # Hoặc summary của máy cụ thể:
      # machine_summary = os.path.join(base, latest_dir, f"machines/machine_{machine_id}/{latest_dir}/summary.txt")
  ```

## 2. Quy tắc an toàn khi gọi ADB `input keyevent` trong `feed_swipe_smoke.py`
- Mọi thao tác gửi keyevent bằng `ctx.adb.shell(["input", "keyevent", ...])` (ví dụ Back `4`/`BACK`, Wake `224`, Home `3`/`HOME`):
  1. **BẮT BUỘC có timeout tường minh**: Không bao giờ gọi `ctx.adb.shell(["input", "keyevent", "4"])` mà thiếu timeout (ví dụ `timeout=ctx.timeout("adb_seconds", 5)` hoặc `timeout=5`).
  2. **BẮT BUỘC bọc trong `try / except`**:
     ```python
     try:
         ctx.adb.shell(["input", "keyevent", "4"], timeout=ctx.timeout("adb_seconds", 5))
     except Exception as exc:
         if hasattr(ctx, "logger"):
             ctx.logger.log(
                 device_id=getattr(ctx, "device_id", ""),
                 account=getattr(ctx, "account", ""),
                 step="adb_keyevent_back",
                 action="keyevent_back_timeout_ignored",
                 result="warning",
                 extra={"error": str(exc)},
             )
     ```
  3. **Lý do**: Khi thiết bị lag, ADB daemon có thể phản hồi chậm hoặc timeout. Nếu không bọc `try/except`, ngoại lệ `ADBError` hoặc `TimeoutExpired` sẽ văng ra ngoài, làm gián đoạn và crash toàn bộ feed session của máy đang chạy.
