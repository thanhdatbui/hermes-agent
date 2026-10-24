# Watchdog Anti-Spam and NO_EVIDENCE Discipline

## Bối Cảnh Sự Cố (Incident Context)
- Agent tạo cronjob `farm-gate-compliance-6h-report` (job_id: `6f3257d17875`) với lịch định kỳ `0 */6 * * *` và `deliver: telegram:-5373649734`.
- Ngay sau khi tạo, agent tự ý gọi `cronjob action='run'` để "test thông mạch" lúc 22:41.
- Do chế độ `no_agent: true`, Hermes lập tức thực thi script và chuyển phát toàn bộ stdout vào Telegram channel Farm Alert ngoài lịch định kỳ.
- Báo cáo in ra 15 dòng emoji wall và danh sách 8 Gate trắng trơn (`NO_EVIDENCE`, hợp lệ: 0, vi phạm: 0) mà không có bất kỳ thông tin hành động nào.
- Phản hồi từ User: *"Báo 6h 1 lần mà mày spam lắm thế?"*.

## 2 Quy Tắc Bắt Buộc (Invariants)

### 1. Cấm Tuyệt Đối `cronjob run` Vào Live Chat Để Test
- **Nguyên tắc:** Lệnh `cronjob action='run'` kích hoạt scheduler thực thi thật và chuyển phát output về đúng kênh `deliver`.
- **Hành vi cấm:** Tự ý bấm `run` để kiểm tra script có chạy được hay không sau khi tạo hoặc cập nhật cronjob trên live channel.
- **Hành vi chuẩn:** Kiểm thử script hoàn toàn offline qua CLI terminal local:
  ```bash
  python D:/Taadaa/tools/<watchdog_script>.py
  ```
  Nếu script in đúng format và exit 0 thì scheduler sẽ tự động chạy đúng tick tiếp theo theo cron expression.

### 2. Quy Chuẩn Đầu Ra Cho Watchdog Định Kỳ Khi NO_EVIDENCE
- **Silent Watchdog (Ưu tiên số 1):** Script trả về stdout rỗng và exit 0 khi không có vi phạm (`overall == 'NO_EVIDENCE'`). Hermes `no_agent: true` sẽ im lặng hoàn toàn, không gửi tin nhắn làm rác kênh.
- **Liveness Ping 1 dòng (Khi User yêu cầu duy trì báo cáo định kỳ):** Nếu user muốn biết watchdog vẫn đang hoạt động:
  - Khi `NO_EVIDENCE`: BẮT BUỘC rút gọn thành đúng 1 dòng trạng thái ngắn gọn:
    ```
    🛡️ *[WATCHDOG NAME — 6H REPORT]* ℹ️ Không phát sinh vi phạm (N files đối soát).
    ```
  - CẤM in danh sách chi tiết các Gate/bảng biểu/emoji wall khi không có sự kiện thực tế.
  - Khi có hoạt động thật (`PASS`, `FAIL`, `PARTIAL`): In chi tiết đầy đủ từng tiêu chí để phục vụ điều tra.
