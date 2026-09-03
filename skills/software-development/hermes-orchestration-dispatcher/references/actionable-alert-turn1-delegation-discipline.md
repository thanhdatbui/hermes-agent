# Actionable Alert Turn-1 Delegation Discipline

## 1. Nguyên Tắc Điều Phối Turn-1 Cho Farm Alert
Khi nhận bất kỳ tin nhắn Farm Alert nào (e.g. `[FARM ALERT: MÁY N] DỪNG PHIÊN`):
1. **Turn 1 BẮT BUỘC gọi `delegate_task` ngay lập tức**:
   - Model worker: `ag-worker` (qua OmniRoute).
   - Role: `leaf`.
   - Context: Truyền đầy đủ 4 trường từ alert:
     - `inspect_cmd`: `python D:/Taadaa/tools/inspect_machine.py <N>`
     - `flow_file`: đường dẫn file flow phụ trách
     - `log_path`: đường dẫn file log chạy
     - `canary_cmd`: lệnh canary test
2. **Coordinator giữ trạng thái sạch (Read-only / Coordinate-only)**:
   - CẤM Coordinator tự mở file lớn, tự patch code hoặc tự chạy loop test trên session chính.
   - CẤM dùng `adb shell input tap/keyevent` để giải phóng màn hình tạm bợ.
3. **Khi Worker Hoàn Tất**:
   - Coordinator chỉ thực hiện: kiểm tra kết quả worker trả về -> chạy canary verification test lại máy N -> tiến hành quy trình chốt phiên 6 Gate.
