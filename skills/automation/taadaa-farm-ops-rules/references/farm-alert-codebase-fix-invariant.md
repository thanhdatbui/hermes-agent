# INVARIANT: FARM ALERT PHẢI VÁ CODEBASE, CẤM CHỮA NGỌN QUA ADB/SHELL

## 1. Bản chất vấn đề
Khi nhận được `[FARM ALERT: MÁY N]`, nguyên nhân lỗi thường rơi vào 2 nhóm:
1. **Lỗi logic / UI:** Màn hình kẹt popup mới, đổi layout, element không tìm thấy.
2. **Lỗi hạ tầng / mạng / kết nối:** ADB transport bị nghẽn (socket hang), lệnh probe mạng (`ip addr show wlan0`, `dumpsys connectivity`) timeout, proxy transient unreachable.

## 2. Quy tắc CẤM TUYỆT ĐỐI (Anti-pattern)
- **CẤM** gõ lệnh terminal thủ công như `adb reconnect`, `adb shell input`, `python set_proxy_farm_adb.py` để làm máy chạy được tạm thời rồi chạy canary test báo pass.
- Việc này chỉ "chữa ngọn", không giúp 80-160 máy khác tự vượt qua khi gặp cùng hiện tượng ở các ca sau.

## 3. Quy trình bắt buộc khi nhận Farm Alert
1. **Trích xuất hiện trường:** Chạy `python D:/Taadaa/tools/inspect_machine.py <N>`.
2. **Xác định file flow / module phụ trách:** Đọc đúng file trong `python_runner/` hoặc `automation-core`.
3. **VÁ CODEBASE TẬN GỐC (BẮT BUỘC):**
   - Viết logic bắt ngoại lệ (exception handling), tự động timeout + retry hợp lý.
   - Nếu là lỗi ADB transport hang / probe timeout: viết logic auto-reconnect (`adb reconnect`) và auto-retry ngay trong hàm executor/probe của script Python.
   - Nếu là lỗi UI/popup: bổ sung handler vào dismiss/recovery flow.
4. **Kiểm thử Canary:** Chỉ chạy lệnh canary test sau khi code mới đã được đưa vào codebase.
5. **Báo cáo:** Phải có code diff cụ thể chứng minh script đã tự xử lý được lỗi đó.
