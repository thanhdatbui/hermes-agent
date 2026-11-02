# Multi-Session Ownership & Single-Writer Discipline

## 1. Bản Chất Vấn Đề
Khi có nhiều session (hoặc nhiều Coordinator/Agent) cùng chạy trên hệ thống Farm Taadaa, việc hai bên cùng lao vào sửa cùng một module, script hoặc công cụ hạ tầng (như `canary_runner.py`, `canary_plan.py`, `tools/`) sẽ dẫn đến:
- **Race Condition / Git Conflict:** Đè mất diff của nhau, gây dirty working tree và gãy pipeline ở khâu Precheck (Gate 1/S0).
- **Phân mảnh ngữ cảnh (Context Loss):** Session sau không nắm được root cause hoặc bản vá dở của session trước, dẫn tới việc chắp vá lung tung hoặc xóa bỏ các thay đổi quan trọng đang được thử nghiệm.
- **Bại liệt điều phối (Coordination Paralysis):** Cả hai session cùng chờ nhau nhả lock hoặc cùng cố đẩy PR/commit gây fail Closeout Gate liên tục.

## 2. Nguyên Tắc Single-Writer Monopoly (Độc Quyền Thi Công)
- **Kiểm tra trước khi can thiệp:** Khi User thông báo hoặc nghi ngờ đang có session khác đang làm việc trên cùng một phạm vi (`"Đang có session khác cx đang sửa..."`):
  1. **LẬP TỨC DỪNG MỌI THAO TÁC GHI:** Tuyệt đối CẤM tự ý `patch`, `write_file`, hoặc dispatch worker sửa code trên repo/file đó.
  2. **Tra cứu Git Log / Status O(1):** Kiểm tra xem session kia đã commit/push chưa, hoặc working tree có đang bị sửa đổi dở dang hay không (`git status --short`, `git log -3 --oneline`).
  3. **Nhường quyền dứt điểm:** Để nguyên vẹn quyền thi công và chốt phiên (Closeout Gate) cho session đang nắm context. Session hiện tại chỉ đứng ở vai trò quan sát hoặc phục vụ các task độc lập khác hoàn toàn ngoài scope.

## 3. Khi Nào Được Tiếp Nhận Handoff?
Session hiện tại CHỈ ĐƯỢC PHÉP tiếp tục hoặc can thiệp vào file khi và chỉ khi:
1. Session trước đã chốt phiên chính thức (`Closeout Gate APPROVED`) và commit/push thành công lên remote.
2. User ra lệnh rõ ràng chuyển giao quyền: *"Session kia xong/hỏng rồi, mày vào sửa tiếp đi"*.
3. Đã `git pull` đồng bộ working tree sạch sẽ và verify focused test trước khi bắt đầu S0 của pipeline mới.
