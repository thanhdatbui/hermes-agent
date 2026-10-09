# Canary xác minh kế thừa parent device lock

## Khi dùng
Dùng khi một consumer upload/follow được gọi bên trong `multi_machine_feed_session` và cần chứng minh child không bị chặn bởi lock của parent.

## Quy trình chuẩn
1. Coordinator preflight O(1): map machine → serial từ workbook/source-config; kiểm tra ADB online, lock file và lịch. Chọn đúng một máy rảnh cách ca kế tiếp tối thiểu 60 phút. Nếu máy nằm trong active cohort thì pivot sang peer machine; không kill parent, không xóa lock, không takeover mù.
2. Worker acquire parent lock trước bằng `user_authorized=True`, `status="running"`, `project="tiktok-luot nuoi acc"`; giữ lock suốt child run.
3. Chạy đúng một live smoke dừng trước POST/upload thật. Cấm ADB tap/keyevent/swipe thủ công, cấm `pm clear`, cấm chạy batch.
4. Xác minh lock inheritance bằng artifact run mới: đọc `execution.log`, `report.json`, `checkpoint.json`; phải có literal `[LOCK-INHERIT]` hoặc log tương đương và không có `NEEDS_USER_DECISION` tại `ACQUIRE_LOCKS`. Exit code đơn lẻ không đủ.
5. Tách kết quả: `LOCK-INHERIT=CONFIRMED` không đồng nghĩa `UI-CANARY=SUCCESS`. Nếu UI fail sau khi inheritance đã chứng minh, báo `LOCK-INHERIT=CONFIRMED; UI-CANARY=FAILED/UNPROVEN`; không retry mù.
6. Trước teardown phải capture screenshot/XML hiện trường; sau đó mới release parent lease. Coordinator phải đọc lại artifact và kiểm tra path tồn tại trước khi báo thành công.

## Pitfall test offline
Nếu consumer import trực tiếp `acquire_device_lock` vào module scope, monkeypatch đúng symbol của consumer, ví dụ `state_machine.acquire_device_lock`; patch `automation_core.device_lock.acquire_device_lock` sẽ không tác động tới alias đã import.

## Báo cáo bắt buộc
- machine/serial, parent project, child command
- exit code, run_id
- exact log line chứng minh inheritance
- artifact paths: execution log/report/checkpoint/screenshot/XML
- trạng thái release parent lock
- phân loại `CONFIRMED`, `FAILED`, hoặc `UNPROVEN`
