# Python Environment Shadowing & Popup Registry Invariants

## 1. Hermes Subprocess Python Environment Shadowing (PIL `_imaging` Crash)

### Hiện tượng
Khi Coordinator hoặc Worker subagent chạy lệnh canary hoặc script Python qua terminal / PowerShell:
```text
Traceback (most recent call last):
  File "D:\Taadaa\tiktok-luot nuoi acc\python_runner\run_tiktok.py", line 37, in <module>
    from flows.calibrate_screens import calibrate_screens
  File "D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\calibrate_screens.py", line 10, in <module>
    from PIL import Image, UnidentifiedImageError
  File "C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL\Image.py", line 95, in <module>
    from . import _imaging as core
ImportError: cannot import name '_imaging' from 'PIL'
```

### Nguyên nhân gốc rễ
Process của Hermes Agent tự động inject các biến môi trường:
- `PYTHONPATH=C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`
- `VIRTUAL_ENV=C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv`

Khi tiến trình con (PowerShell / Python) được khởi chạy, Python nạp gói `PIL` từ thư mục venv của Hermes thay vì site-packages gốc của Python 3.12 (`C:\Users\Kibe\AppData\Local\Programs\Python\Python312\Lib\site-packages`), gây xung đột C-extension binary compiled (`_imaging.pyd`).

### Giải pháp chuẩn (Clean Env Invocation)
Khi gọi canary test hoặc script farm từ Hermes terminal hoặc subagent:
1. **Trong MSYS Bash / Terminal:** Dùng `env -u PYTHONPATH -u VIRTUAL_ENV`:
   ```bash
   env -u PYTHONPATH -u VIRTUAL_ENV powershell.exe -ExecutionPolicy Bypass -Command "$env:PYTHONPATH=''; $env:VIRTUAL_ENV=''; powershell.exe -ExecutionPolicy Bypass -File 'D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1' -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Python 'C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe' -Run"
   ```
2. **Trong PowerShell script / wrapper:**
   ```powershell
   $env:PYTHONPATH = ""
   $env:VIRTUAL_ENV = ""
   ```
3. **Trong Python subprocess:**
   ```python
   clean_env = os.environ.copy()
   clean_env.pop("PYTHONPATH", None)
   clean_env.pop("VIRTUAL_ENV", None)
   subprocess.run([python_bin, ...], env=clean_env)
   ```

---

## 2. Quy Chuẩn Bắt Buộc Khi Thêm Handler Vào `BENIGN_POPUP_REGISTRY`

### Invariant A: Độ ưu tiên (Priority) độc nhất tuyệt đối (No Collision)
- Mọi handler đăng ký vào `BENIGN_POPUP_REGISTRY` qua `RegistryEntry(name, priority, detector, dismisser, enabled, source)` BẮT BUỘC phải có `priority` dạng số nguyên độc nhất.
- CẤM trùng lặp priority với bất kỳ handler nào đã có (dải 70–98 hiện đã phủ kín).
- Trước khi đăng ký, kiểm tra `[e.priority for e in BENIGN_POPUP_REGISTRY]`. Các slot khả dụng: 69 hoặc 99. Trùng priority gây non-deterministic ordering hoặc shadowing ngầm.

### Invariant B: Bắt buộc điền `selector` trong `PopupDismissResult`
Khi dismisser trả về `dismissed=True`, BẮT BUỘC phải cung cấp tham số `selector`:
```python
return PopupDismissResult(
    dismissed=True,
    reason="clicked_da_hieu_rewards_policy",
    before_attempt={"action": "click_da_hieu_rewards_policy"},
    popup_closed=True,
    selector={"action": "allowlist_dismiss", "popup_type": "<popup_name>"},
)
```
*Hậu quả nếu thiếu:* Downstream caller (`_apply_popup_dismiss_result`) nhận `popup_type=None`, làm kích hoạt cơ chế retry guard hiểu nhầm là kẹt `manual-needed` / `known TikTok screen` và dừng phiên sai.

### Invariant C: Fail-Closed Dual-Keyword Detection
Đối với các dialog modal chính sách/thông báo mới xuất hiện (như Case 123 - Chính sách Phần thưởng & Vật phẩm ảo):
- Detector phải kiểm tra đồng thời cả 2 điều kiện:
  1. Từ khóa nội dung chính sách (`"chính sách phần thưởng"` hoặc `"chính sách vật phẩm ảo"`).
  2. Từ khóa nút xác nhận đóng (`"đã hiểu"` hoặc `"got it"`).
- Tuyệt đối không chỉ match từ khóa chính sách đơn lẻ vì có thể trùng nội dung video/caption trên feed.
