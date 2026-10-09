# Popup Registry & Fail-Closed Invariants for Farm Recovery

## 1. Môi trường Thực thi Canary Test (Clean Python Env)
Khi chạy Canary test từ terminal của Hermes Agent (trực tiếp hoặc qua subagent):
- Hermes tự động truyền `PYTHONPATH` và `VIRTUAL_ENV` trỏ tới `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`.
- Gói `PIL` trong venv của Hermes thiếu binary compiled `_imaging.pyd`, gây crash `ImportError: cannot import name '_imaging' from 'PIL'`.
- **Cú pháp chuẩn khi chạy Canary trên Windows Farm:**
  ```bash
  env -u PYTHONPATH -u VIRTUAL_ENV powershell.exe -ExecutionPolicy Bypass -Command "$env:PYTHONPATH=''; $env:VIRTUAL_ENV=''; powershell.exe -ExecutionPolicy Bypass -File 'D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1' -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Python 'C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe' -Run"
  ```

---

## 2. 3 Bất Biến (Invariants) Khi Đăng Ký Handler Trong `BENIGN_POPUP_REGISTRY`

### A. Độ ưu tiên (Priority) độc nhất tuyệt đối (No Collision)
- Mọi entry trong `BENIGN_POPUP_REGISTRY` qua `RegistryEntry(name, priority, detector, dismisser, enabled, source)` BẮT BUỘC có priority là số nguyên độc nhất.
- Hiện dải priority từ 70 đến 98 đã phủ kín. CẤM trùng priority với handler có sẵn (sẽ gây non-deterministic ordering hoặc silent shadowing).
- Slot an toàn cho dialog modal mới: `69` hoặc `99`.

### B. Bắt buộc trường `selector` trong `PopupDismissResult`
Khi dismisser trả về kết quả thành công `dismissed=True`, BẮT BUỘC phải truyền trường `selector`:
```python
return PopupDismissResult(
    dismissed=True,
    reason="clicked_da_hieu_rewards_policy",
    before_attempt={"action": "click_da_hieu_rewards_policy"},
    popup_closed=True,
    selector={"action": "allowlist_dismiss", "popup_type": "<popup_name>"},
)
```
Nếu thiếu `selector` hoặc không có `popup_type`, caller phía sau (`_apply_popup_dismiss_result`) sẽ nhận `popup_type=None`, làm kích hoạt nhầm cơ chế retry guard hiểu là kẹt `manual-needed` / `known TikTok screen` và freeze phiên.

### C. Fail-Closed Dual-Keyword Detection
Đối với popup dialog modal chính sách / thông báo (như Case 123):
- Detector phải kiểm tra đồng thời cả 2 điều kiện:
  1. Từ khóa nội dung chính sách (`"chính sách phần thưởng"` hoặc `"chính sách vật phẩm ảo"`).
  2. Từ khóa nút xác nhận đóng (`"đã hiểu"` hoặc `"got it"`).
- Không được dùng `or` giữa từ khóa nội dung và nút đóng để tránh false-positive trên video feed thường.
