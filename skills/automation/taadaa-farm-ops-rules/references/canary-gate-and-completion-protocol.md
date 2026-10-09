# Canary Gate & Completion Protocol (Rules 7 & 8)

## 1. Mục đích & Phạm vi áp dụng
Cơ chế kiểm soát điều kiện hoàn tất (Done Gate) và chống ngụy tạo bằng chứng (Anti-Confabulation) trên toàn bộ farm Taadaa.
Bắt buộc áp dụng cho mọi coordinator, worker và session can thiệp vào các repo farm automation:
- `register gmail`
- `tiktok-luot nuoi acc`
- `tiktok-follow`
- `tiktok-log-in`
- `Tiktok_Reg`
- `tiktok-add-bao-mat-f2a`
- `automation-core`

---

## 2. Done Gate: `done_gate.py` Architecture & Logic

Lệnh gọi chuẩn:
```bash
python D:/Taadaa/tools/done_gate.py [--task-type {automation,general}] [--canary-file <path>] [--repo <path>]
```

### Flow phân loại & xét duyệt:
1. **Phân loại Task (`detect_task_type`)**:
   - Nếu có `--task-type`: sử dụng giá trị được chỉ định.
   - Nếu không có: tự động nhận diện theo tên repo (`--repo` hoặc thư mục hiện tại) và git diff.
   - Nếu thuộc danh sách repo automation ➔ `automation`.
   - Ngược lại ➔ `general`.

2. **Nếu `task_type == 'general'`**:
   - Xuất: `GATE-PASS(bypass): Non-automation task, canary not required.`
   - Exit code: `0`.

3. **Nếu `task_type == 'automation'`**:
   - **Bước 1: Kiểm tra Evidence gần nhất (< 2 giờ / 7200 giây)**:
     - Kiểm tra `--canary-file` (nếu file tồn tại và mtime trong vòng 2 giờ).
     - Hoặc file cờ `D:/Taadaa/.canary_passed` (mtime < 2h hoặc timestamp json hợp lệ).
     - Nếu có bằng chứng:
       - Xuất: `GATE-PASS: Canary verified on real device.`
       - Dọn sạch cờ `D:/Taadaa/.canary_pending` (nếu có).
       - Exit code: `0`.
   - **Bước 2: Khi KHÔNG có Canary Evidence**:
     - Kiểm tra trạng thái thiết bị thật trên farm (qua `adb devices` hoặc lock files tại `~/.codex/device-locks/` hoặc `phone_farm_status.json`).
     - **Nếu có thiết bị rảnh khả dụng**:
       - Xuất: `GATE-FAIL: Automation code fix BẮT BUỘC phải chạy Canary trên thiết bị thật trước khi báo DONE! Thiết bị rảnh khả dụng: [danh sách máy/serial]`
       - Exit code: `1` (Chặn cứng, cấm báo DONE).
     - **Nếu toàn farm bận 100% hoặc không có thiết bị kết nối**:
       - Xuất: `GATE-PASS(deferred): Farm đang bận 100%, tạm hoãn Canary. Đã đánh dấu .canary_pending.`
       - Tạo file cờ `D:/Taadaa/.canary_pending`.
       - Exit code: `0`.

---

## 3. Anti-Confabulation & Truth-Telling Protocol

1. **Cấm bịa đặt bằng chứng (Zero Fake Artifacts)**:
   - Tuyệt đối cấm hallucinate: serial thiết bị, kết quả chạy lệnh shell, nội dung log, screenshot path, hoặc kết quả pytest.
   - Bằng chứng nghiệm thu BẮT BUỘC phải xuất phát từ output thực thi công cụ trong phiên hiện tại.

2. **Trung thực về Blocker & Giới hạn môi trường**:
   - Nếu hết ngân sách tool calls hoặc chạm giới hạn vòng lặp: báo cáo chính xác những việc đã làm, những gì còn dở dang và bước kế tiếp cụ thể. Cấm báo "đã xong" khi chưa chạy test thực tế.
   - Nếu thiếu binary (ví dụ `adb` không có trong global PATH): xử lý bắt ngoại lệ `FileNotFoundError`, ghi nhận cảnh báo và fallback kiểm tra thiết bị qua lock file / config farm thay vì bịa kết quả ADB.
