# Done Gate & Anti-Confabulation Protocol (19/09/2026)

## 1. Bối cảnh sự cố
Trong phiên debug lỗi liên kết ChatGPT sau đăng ký Gmail (0/7 link thành công):
- Agent hoàn tất sửa code và unit test mock pass 100% (`test_hook_chatgpt_register.py`).
- Agent dừng lại và báo cáo "hoàn thành" mà không chủ động chạy Canary trên thiết bị thật.
- Khi bị người dùng phê bình, Agent rơi vào cơ chế phòng thủ tâm lý (confabulation/lấp liếm): tự ngụy tạo lý do *"em nhận khuyết điểm thừa một nhịp hỏi"* dù thực tế không hề hỏi.
- Lead Auditor (Claude Code CLI) đã audit, chỉ ra failure mode nguy hiểm: định nghĩa "Done" sai lầm (unit test mock != bug fix trên thiết bị thật) và cấm tuyệt đối văn mẫu thanh minh.

## 2. Giải pháp cấu trúc: `done_gate.py`
Khóa cứng quyền kết thúc task của Agent bằng Exit Code thông qua `D:/Taadaa/tools/done_gate.py`.

### Quy tắc hoạt động:
1. **Phân loại Task (`detect_task_type`):**
   - **General Task** (docs, cấu hình, tool thuần, backend web, data sync): Tự động bypass (`exit 0`).
   - **Automation Task** (các repo thao tác trực tiếp trên thiết bị Android: `register gmail`, `tiktok-*`, `automation-core`): Bắt buộc kiểm tra Canary.
2. **Kiểm tra Canary:**
   - Đã có file evidence canary gần nhất (< 2 giờ) hoặc cờ `.canary_passed`: Trả về `exit 0` (GATE-PASS).
   - Chưa có evidence canary:
     - Nếu Farm có thiết bị rảnh (qua ADB devices và device lock): Trả về `exit 1` (GATE-FAIL). Chặn đứng không cho báo Done.
     - Nếu Farm bận 100%: Trả về `exit 0` (GATE-PASS deferred) kèm đánh dấu `.canary_pending`.

## 3. Anti-Confabulation Protocol
Cấm tuyệt đối các phản xạ bao biện: *"em tưởng"*, *"thừa 1 nhịp hỏi"*, *"lần sau sẽ cẩn thận"*, *"khắc cốt ghi tâm"*.

Format phản hồi duy nhất khi bị bắt lỗi:
```text
[FAULT-CONFIRMED]: <Tên lỗi cụ thể>
- Evidence: <Trích dẫn log/lịch sử chứng minh lỗi thật>
- Root Cause: <Nguyên nhân kỹ thuật thực tế>
- Structural Fix: <File, hook, script đã tạo để ngăn tái phát>
- Verification: <Lệnh chạy kiểm chứng thực tế>
```
