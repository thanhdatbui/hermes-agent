# Auto-Login Recovery Signature & Screen Preservation Compatibility (2026-09-03)

## Bối cảnh & Hiện tượng
- **Hiện trường**: Khi chạy `multi-machine-feed-session` (hoặc `feed-session-smoke`), máy bị dừng phiên báo:
  `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
- Mặc dù hệ thống đã có luồng tự động phục hồi `_maybe_recover_missing_account_via_login` gọi `reconcile_tiktok_accounts.py` để login lại nick còn thiếu, quá trình reconcile vẫn kết thúc với `FINAL_BLOCKED` và không thể login nick vào máy.

## Root Cause
1. **Lệch Signature giữa `tiktok-log-in` và `Tiktok_Reg`**:
   - `D:\Taadaa\tiktok-log-in\login_runner\account_reconcile.py` gọi hàm:
     ```python
     login_ok = login_module.login_one_account(
         target.serial,
         target.machine,
         account,
         take_ss=True,
         update_tracking=False,
         preserve_current_screen=_can_preserve_current_tiktok_screen(adb_path, target),
     )
     ```
   - Trong khi `D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py` định nghĩa:
     ```python
     def login_one_account(device_id, stt, account, take_ss=False, update_tracking=True):
     ```
   - Lệnh gọi truyền tham số `preserve_current_screen` khiến Python văng ngoại lệ `TypeError: login_one_account() got an unexpected keyword argument 'preserve_current_screen'`.
   - `account_reconcile.py` catch `Exception` và gán `last_error`, khiến cả 2 lượt attempt đều thất bại và trả về `FINAL_BLOCKED` mà không thực sự thao tác trên máy.

## Quy tắc & Cách khắc phục chuẩn
1. **Kiểm tra Signature tương thích động trong `account_reconcile.py`**:
   ```python
   login_kwargs = {
       "take_ss": True,
       "update_tracking": False,
   }
   try:
       sig = inspect.signature(login_module.login_one_account)
       if "preserve_current_screen" in sig.parameters or any(
           p.kind == inspect.Parameter.VAR_KEYWORD
           for p in sig.parameters.values()
       ):
           login_kwargs["preserve_current_screen"] = _can_preserve_current_tiktok_screen(
               adb_path, target
           )
   except (ValueError, TypeError):
       pass
   login_ok = login_module.login_one_account(
       target.serial,
       target.machine,
       account,
       **login_kwargs,
   )
   ```
2. **Hỗ trợ `preserve_current_screen=False` trong `Tiktok_Reg/tiktok_login_v1.py`**:
   - Thêm `preserve_current_screen: bool = False` vào tham số của `login_one_account`.
   - Nếu `not preserve_current_screen`, gọi `open_app(device_id)`. Nếu `preserve_current_screen=True` (app TikTok đang mở ở màn hợp lệ sẵn có như auth/switcher), bỏ qua `open_app` để không làm mất màn hình hiện tại.
3. **Kiểm thử hồi quy (Regression Test)**:
   - Thêm unit test `test_legacy_login_provider_without_preserve_current_screen_succeeds` trong `tests/test_account_reconcile.py` để đảm bảo khi provider cũ không nhận tham số `preserve_current_screen`, reconcile vẫn gọi thành công và không bị dính `TypeError`.
