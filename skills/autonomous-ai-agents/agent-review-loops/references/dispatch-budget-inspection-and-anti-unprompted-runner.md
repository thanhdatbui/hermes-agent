# Dispatch Budget Verification & Anti-Unprompted-Runner

## 1. Bản chất sự cố bộ đếm Dispatch 10/10
- **Nguyên nhân kép:**
  1. Khi sửa file cấu hình hoặc guard trên đĩa (ví dụ nâng trần dispatch lên 15 hay 20), tiến trình Daemon chạy nền của Hermes (`pythonw.exe`) KHÔNG tự nạp lại code vào RAM nếu chưa được restart.
  2. Biến đếm `dispatch_count` trong plugin guard được lưu trữ theo Session ID hiện tại. Nếu session đó đã dispatch đủ 10 lần trước đó, trạng thái RAM vẫn nhớ là đã kịch trần.
- **Cách verify chuẩn xác 100%:**
  * Gọi trực tiếp 1 lệnh probe: `delegate_task(goal="Kiểm tra dispatch", context="TASK_KIND: INVESTIGATE\nBUDGET: <= 3 calls")`.
  * Nếu trả về `delegation_id` và `dispatched` -> Budget ĐÃ ĐƯỢC MỞ THÀNH CÔNG.
  * Nếu trả về `[COORDINATOR GUARD - DISPATCH BUDGET EXHAUSTED]` -> Vẫn kẹt trong RAM.

## 2. Hard Invariant: "Kiểm tra lại" là lệnh Read-Only O(1)
- **Sai lầm chết người:** Khi User yêu cầu "kiểm tra lại", "check lại", "coi lại", Coordinator tự ý kích hoạt Claude Code CLI chạy ngầm sửa code hoặc can thiệp repo.
- **Quy tắc tuyệt đối:**
  * Lệnh kiểm tra là READ-ONLY O(1).
  * CHỈ chạy 1 lệnh probe inspect/delegate_task để xem trạng thái và trả lời ngay kết quả cho User.
  * CẤM TUYỆT ĐỐI gọi Claude Code CLI, cấm sửa code, cấm can thiệp git khi User chỉ bảo kiểm tra.
  * Claude Code CLI CHỈ được kích hoạt khi đang ở task Fix Code được duyệt hoặc User trực tiếp ra lệnh "sửa đi", "làm đi".
