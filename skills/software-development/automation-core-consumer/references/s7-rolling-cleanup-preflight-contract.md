# S7 Rolling Cleanup Preflight Contract & Lock-Inheritance Pattern

## Overview
Trên dàn Samsung S7 (SM-G930F/W8), mỗi thiết bị chỉ lưu tối đa 5 tài khoản Google. Khi máy đạt trần (>= 5 accounts), tiến trình đăng ký tài khoản mới (`gmail_reg_v10.py` hoặc các consumer tương đương) sẽ bị nghẽn trừ khi một tài khoản cũ đủ điều kiện được gỡ bỏ cuốn chiếu (rolling cleanup).

Tài liệu này ghi lại kiến trúc tích hợp an toàn, quy tắc 3-Gate và cơ chế kế thừa Device Lock khi tích hợp cleanup vào consumer runner.

---

## 1. Vấn Đề Xung Đột Device Lock (Lock Inheritance Pitfall)
- **Bối cảnh**: Standalone script (`preflight_s7_rolling_cleanup.py`) tự wrap ADB cleanup trong `with acquire_device_lock(machine=..., serial=..., project="gpm-cleanup", force_preempt=True)`.
- **Nguy cơ**: Khi consumer runner (`gmail_reg_v10.py`) đã acquire device lock từ ngoài (`project="gmail-reg"`), việc gọi hàm con mà bên trong lại cố giành lock với `project` khác hoặc `force_preempt=True` sẽ dẫn tới:
  - Tự cướp lock của chính tiến trình cha (self-preemption).
  - Gây deadlock hoặc vỡ heartbeat lock file.
- **Giải pháp chuẩn**:
  - Hàm thao tác thiết bị (`remove_account_adb`) và orchestrator helper (`run_s7_rolling_cleanup_preflight`) BẮT BUỘC hỗ trợ tham số `skip_lock: bool = False`.
  - Khi consumer gọi: truyền `skip_lock=True` để tái sử dụng lock hiện tại của outer caller.
  - Khi chạy CLI standalone: `skip_lock=False` để tự bảo vệ bằng lock riêng.

```python
def remove_account_adb(serial: str, machine_id: int, target_email: str, dry_run: bool = True, skip_lock: bool = False) -> bool:
    ...
    if skip_lock:
        return _do_remove_adb(serial, machine_id, target_email, dry_run)
    with acquire_device_lock(machine=str(machine_id), serial=serial, project="gpm-cleanup", force_preempt=True):
        return _do_remove_adb(serial, machine_id, target_email, dry_run)
```

---

## 2. Quy Tắc 3 Safety Gates Cho Rolling Cleanup
Chỉ gỡ tài khoản khi tài khoản đó đáp ứng ĐẦY ĐỦ 3 Gates:
1. **Gate 1 (2FA Active)**: Tài khoản đã được bật bảo mật 2FA (có secret key hợp lệ trong database/Excel).
2. **Gate 2 (OAuth Active)**: Tài khoản đã hoàn tất xác thực OAuth (Antigravity/API token đã lưu).
3. **Gate 3 (Tuổi >= 30 Ngày)**: `age_days >= 30` tính từ ngày tạo tài khoản.

### Xử lý khi Đạt Trần (>= 5 accs) nhưng KHÔNG thỏa 3 Gates:
- Trạng thái trả về: `status="FULL_NO_ELIGIBLE_CLEANUP"`, `can_reg=False`.
- Consumer runner phải dừng ngay lập tức (fail-closed), log cảnh báo rõ ràng, giải phóng device lock và thoát cleanly (`sys.exit(0)` hoặc mã thoát được định nghĩa) mà không cố đăng ký thêm để tránh làm chết thiết bị hoặc mất dữ liệu acc cũ chưa backup.

---

## 3. Thứ Tự Đặt Preflight Trong Consumer Runner
Preflight phải được đặt đúng vị trí trong pipeline:
1. `acquire_device_lock` (Khóa thiết bị).
2. `require_android_vpn` / Proxy Preflight (Kiểm tra proxy/VPN live IP).
3. **`s7_rolling_cleanup_preflight`** (Đánh giá & gỡ cuốn chiếu nếu cần):
   - Nếu `not can_reg`: Hoàn tất/nhả lock (`device_lock.finish(succeeded=True)`) và exit.
   - Nếu `can_reg`: Tiếp tục flow reg bình thường.
4. Sinh account (`generate_account_for_slot`).
5. Thực hiện đăng ký (`register`).
