# Watchdog / Farm Alert Incident Response Contract

## 1. Không Bao Giờ Tường Thuật Lại Báo Cáo
Khi User hoặc Cronjob ném bản tin báo cáo (watchdog report / batch alert) vào chat:
- **CẤM TUYỆT ĐỐI:** Tóm tắt, dịch lại, viết văn phân tích hay giải thích lại nội dung text đã có trong tin nhắn.
- **BẮT BUỘC:** Coi đây là trigger sự cố (Incident Trigger). Chạy ngay điều tra kỹ thuật $O(1)$ tại hiện trường:
  1. Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` để kiểm tra thiết bị online thật hay mất USB thật.
  2. Mở trực tiếp `run_manifest.json` và `log.jsonl` tại `D:/Taadaa/runtime/<cluster>/live/<date>/<run_id>/` để bóc tách root cause thật.
  3. Phân loại dứt khoát: Lỗi vật lý (sụt nguồn, tuột cáp) vs Lỗi phần mềm (socket hang, preflight retry bug, popup chưa dismiss).
  4. Nếu là bug phần mềm: Tự động kích hoạt quy trình sửa chữa (L1 dispatch worker hoặc L2 surgery theo ngân sách), không ngồi chờ User ra lệnh.

## 2. Invariant Protection: Chống Lật Ngược Thành Quả (Anti-Regression Flip-Flop)
Khi phát hiện máy bị chờ lâu hoặc timeout trong chuỗi retry ADB:
- **Case 162 Invariant:** `connection_wait_timeout >= 20.0s`, `connection_retry_attempts >= 3`, `ADB_ONLINE_ATTEMPTS >= 5` trong `python_runner/flows/multi_machine_feed_session.py` là THÔNG SỐ VÀNG để chống sụt áp / micro-drop USB Hub.
- **CẤM:** Hạ timeout hoặc số lần retry của `child_adb` để "cho đỡ ngâm deadline" khi máy rớt cáp thật. Hạ timeout sẽ giết oan các máy micro-drop tạm thời ở session sau, tạo thành vòng lặp regression giữa các session.
- Khi máy rớt cáp thật làm cạn deadline 50 phút: Đó là hành vi fail-closed đúng của hệ thống. Xử lý bằng cách cắm lại phần cứng hoặc kiểm tra trạng thái thiết bị liveness, không sửa lùi thông số bảo vệ.

## 3. Quy Chuẩn Điều Phối Khi Gọi Claude CLI
Khi điều phối Claude CLI (`claude -p`):
1. **Tránh Hook Session-Start:** Không dùng `cat file | claude -p -` trong thư mục git có uncommitted changes. Dùng direct argument `claude -p "<prompt>"` hoặc chạy từ thư mục sạch / truyền `--bare`.
2. **Hạn mức Turns tối thiểu:** Khi giao task lập Plan hoặc Review, bắt buộc `--max-turns >= 15` (tránh đặt 6 turns khiến model cạn turn khi đang inspect codebase).
3. **Evidence Presence Verification:** Kiểm tra output của Claude CLI trước khi báo cáo. Nếu Claude chưa trả về kết quả hoặc bị chặn, báo cáo trung thực hiện trạng, CẤM tự chém gió hay phân trần thay cho Claude.
