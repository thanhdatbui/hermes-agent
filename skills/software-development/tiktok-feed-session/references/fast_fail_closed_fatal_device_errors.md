# Fast Fail-Closed for Fatal Device Errors in Multi-Machine Feed Session

## 1. Ngữ cảnh & Nguyên tắc
Trong luồng `multi_machine_feed_session.py`, khi một thiết bị gặp sự cố vật lý, mất kết nối ADB, hoặc rớt router proxy hoàn toàn:
- Không được phép để worker thread tiếp tục chạy các hook phụ thuộc ADB (như follow hook, upload hook, clear cache hook), vì ADB sẽ hang, retry hoặc chờ timeout tối đa (lên đến 2100s).
- Không được release lock hay chuyển sang trạng thái thành công/bỏ qua — BẮT BUỘC giữ nguyên hiện trường trạng thái lock `blocked` để operator có thể sử dụng `python D:/Taadaa/tools/inspect_machine.py <N>` để điều tra.
- Worker thread phải trả về ngay lập tức để giải phóng slot trong `ThreadPoolExecutor` cho các máy tiếp theo trong đợt chạy.

## 2. Các Lỗi Fatal Unrecoverable Cần Nhận Diện
- `"device is offline or ADB/USB disconnected"`
- `"device not found"` / `"not found in adb devices"`
- `"required router proxy is unreachable"` / `"ping probe failed"`

## 3. Hành Vi Bắt Buộc Khi Xử Lý Lỗi Fatal (Claude Review Hardened)
1. **Trạng thái trả về & Khởi tạo an toàn**:
   - Khởi tạo mặc định `goal_completed: bool = False` (safe fail-default).
   - `final_status="blocked"`
   - `blocker_type`:
     + `focus-device-issue` (đối với lỗi offline, mất ADB, không tìm thấy thiết bị).
     + `proxy-vpn` (đối với lỗi router proxy unreachable, ping probe failed).
2. **Chuẩn hóa nhận diện lỗi chống False-Positive**:
   - `_is_fatal_device_error(error_text)` BẮT BUỘC dùng `.lower()` và đối soát với tuple các cụm từ cụ thể:
     `"device offline"`, `"device is offline"`, `"adb/usb disconnected"`, `"device not found"`, `"not found in adb devices"`, `"required router proxy is unreachable"`, `"ping probe failed"`, `"adb server connection failed"`, `"adb transport lost"`.
   - TUYỆT ĐỐI CẤM dùng từ `"offline"` đơn lẻ vì dễ dính false-positive từ log ứng dụng ("user went offline", "offline cache").
3. **Bảo tồn Lock trong khối `finally:`**:
   - Bắt buộc bọc `try/except Exception: pass` riêng cho lệnh `lease.set_status("blocked")` và khối `_write_blocked()`, đảm bảo exception từ lease không làm đứt đoạn luồng ghi evidence handoff hoặc suppress lỗi gốc.
   - Thiết bị luôn được giữ lock `blocked` đủ 1h để operator inspect.
4. **Bỏ qua ADB Hooks (Side-Effect Free)**:
   - Ngắt ngay luồng, không chạy `_run_follow_hook`, `_run_upload_hook`, hoặc `_run_clear_cache_hook` trên thiết bị đã mất kết nối.
   - Upload hook chỉ kích hoạt ở session 3 và `ShiftUploadLedger` chỉ ghi nhận khi subprocess upload thực tế hoàn tất thành công. Việc ngắt sớm khi device fatal không để lại side-effect sai lệch ledger.
5. **Môi trường Test Pytest**:
   Khi chạy test trong repo `tiktok-luot nuoi acc`, luôn set PYTHONPATH:
   ```bash
   PYTHONPATH="D:/Taadaa/tiktok-luot nuoi acc/python_runner;D:/Taadaa/automation-core/src" /d/Taadaa/python-envs/automation/Scripts/python.exe -m pytest <test_file> -v
   ```
