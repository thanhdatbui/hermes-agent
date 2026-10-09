# Canary Random Swipes & Account Switch Mismatch Recovery

## 1. Lỗi `profile username still mismatched after switch`

### Triệu chứng
- Sau khi thực hiện flow chuyển tài khoản (Account Switcher), màn hình Profile của TikTok vẫn hiển thị username cũ (ví dụ: máy 58 vẫn hiện `khoa4597` thay vì chuyển sang `lamnhu3003`).
- Log báo lỗi: `profile username still mismatched after switch` và rơi vào trạng thái `manual-needed`.

### Nguyên nhân gốc rễ
1. **Settle time quá ngắn:** Thời gian chờ sau khi tap item tài khoản trong bottom sheet switcher (trước đây là 2.0 - 3.0s) chưa đủ để TikTok transition và nạp identity tài khoản mới trên một số máy S7 farm.
2. **Thiếu điều kiện auto-reconcile:** Hàm `_is_account_switcher_missing_expected_reason` trong `feed_swipe_smoke.py` chỉ kiểm tra chuỗi `account-switcher-missing-expected`. Khi switch bị mismatch, script không coi đây là trường hợp cần login recovery mà dừng phiên luôn.

### Cách khắc phục chuẩn
- **File:** `D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\feed_swipe_smoke.py`
- Mở rộng hàm `_is_account_switcher_missing_expected_reason(reason)` để nhận diện thêm `"profile username still mismatched after switch"`. Khi đó, script sẽ kích hoạt `_maybe_recover_missing_account_via_login` để nạp/đăng nhập lại nick mục tiêu.
- Tăng thời gian settle sau tap switch option lên `random.uniform(3.5, 5.0)`.

---

## 2. Quy chuẩn Canary Swipes Random (2–4 Swipes)

### Vì sao phải Random 2–4 Swipes?
- Cố định 2 swipes mỗi lần canary tạo footprint hành vi máy móc trên TikTok.
- Random 2–4 swipes giúp telemetry tự nhiên như người dùng thật, đồng thời vẫn bảo đảm canary test hoàn thành nhanh (< 90s).

### Giới hạn dải RecoveryTestSwipes trong Codebase
Đã được nâng từ range `[1..3]` lên `[1..4]` tại 2 vị trí:
1. `D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1`: `[ValidateRange(1, 4)] [int]$RecoveryTestSwipes`
2. `D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\multi_machine_feed_session.py`: `1 <= target <= 4` trong hàm `_session_targets`.

### Lệnh chạy Canary Test chuẩn (Random 2–4 Swipes)
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes (Get-Random -Minimum 2 -Maximum 5) -SkipAccountWorkbookSync -Run
```
*Ghi chú:* `Get-Random -Minimum 2 -Maximum 5` sinh ngẫu nhiên một trong các giá trị 2, 3, 4.

---

## 3. Kỷ luật phân vai Coordinator vs Worker khi nhận lệnh sửa code

- **Tín hiệu cảnh báo từ User:** *"Đang sửa trực tiếp hay gọi agent?"*
- **Quy tắc thực thi:** Khi user yêu cầu "Rồi sửa đi" hoặc giao task chỉnh sửa/mở rộng logic code, Coordinator ở session chính **CẤM TUYỆT ĐỐI** tự dùng `read_file`/`patch`/`write_file` hay chạy shell probe để sửa code.
- **Hành động bắt buộc:** Khóa scope thật nhanh (xác định file/hàm cần sửa) và lập tức dispatch worker qua `delegate_task(goal=..., context=...)` để worker thực hiện trong context riêng.
