# Tri-Party Gate & Guard Cascading Thrashing, Conflict Triage & Redundancy Eradication

## 1. Hiện Tượng & Triệu Chứng (Hiện Trường Thực Tế 6H Watchdog)
Khi hệ thống ma trận phòng thủ mở rộng lên đến 62 chốt chặn (19 Hooks, 23 Gates, 16 Guards, 4 Guardrails), báo cáo `gate_compliance_watchdog.py` ghi nhận trạng thái **FAIL** với **610 lượt vi phạm** chỉ trong 6 giờ:
- **G3 Worker Dispatch Gate (243 FAIL):** 119 lần `subagent_edit_blocked` + 106 lần `investigate` lố ngân sách.
- **G7 Anti-Scan & Terminal Guard (275 FAIL):** 128 lần `GUARD_DANGEROUS_ROOT` + 45 lần `GUARD_SEARCH_FILES_ROOT` + 39 lần `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`.
- **G8 Cronjob Window Guard (92 FAIL):** 43 lần `CONSOLE_WINDOW` (thiếu cờ ẩn console) + 13 lần `CRON_AGENT_POLICY`.
- **Hậu quả:** Scheduler ghi nhận cronjob `farm-gate-compliance-6h-report` bị `last_status: error` do watchdog thoát exit code 1 khi tổng thể FAIL.

## 2. Phân Tích Căn Nguyên Gốc Rễ (Root Cause & Cascading Failures)
Cả **Claude CLI** và **Advisor Sol** qua hội chẩn độc lập đều chỉ ra hiện tượng **Lỗi Dây Chuyền (Cascading Failures / Thrashing Loop)**:

### A. Vòng Lặp Bế Tắc Tại G3 (Worker Dispatch Thrashing):
1. Khi cần sửa code, Coordinator có khuynh hướng gọi `delegate_task`.
2. Lớp 1 (`guard_dispatch_contract.py` hook) chặn: `delegate_task bị cấm cho task sửa code`.
3. Thay vì dừng lại chuyển sang `dispatch_worker.py`, Coordinator tìm đường lách bằng cách gọi `delegate_task` cho task "investigate / đọc file".
4. Nhiệm vụ investigate vượt trần ngân sách hoặc tiếp tục lách luật -> G3 chặn tiếp.
5. Vòng lặp thử-sai này kích hoạt liên tục 243 lần chặn, đốt cháy hàng trăm nghìn token mà không sinh ra một dòng code nào.

### B. Vòng Lặp Quét Đĩa & Timeout Tại G7 (Terminal & Scan Over-Trigger):
1. Khi bị chặn sửa code hoặc không định vị được file, Coordinator tự viết script python hoặc lệnh bash để tìm kiếm file.
2. Lệnh tìm kiếm chạm vào các thư mục gốc (`D:/`, `D:/Taadaa`) -> bị `guard_broad_grep.py` chặn 128 lần `GUARD_DANGEROUS_ROOT` và 45 lần `GUARD_SEARCH_FILES_ROOT`.
3. Coordinator cố tăng timeout lên để chạy tìm kiếm -> bị chặn 39 lần `GUARD_FOREGROUND_TIMEOUT_EXCEEDED` (> 60s).

### C. Chồng Chéo (Redundancy & Conflict) Giữa Các Tầng:
- **3 lớp cùng chặn 1 hành vi:** `guard_dispatch_contract` (hook) + Coordinator plugin guard + `G3` (watchdog). Nếu không có điều hướng dứt khoát ở lớp đầu tiên, Coordinator sẽ bị bật nảy qua lại giữa các lớp.
- **Tiêu chí kép Closeout:** `closeout_gate.py` (cổng thực thi) và `G5` (watchdog đối soát) nếu lệch pha schema hoặc cache sẽ tạo báo động giả.

## 3. Quy Chuẩn Triệt Tiêu Xung Đột & Tinh Gọn (Remediation Mandate)

### Chuẩn 1: Front-Door Mandatory Abort Cho Code Edit
- Khi nhận diện ý đồ sửa code từ `delegate_task`, hook BẮT BUỘC chém đứt ngay ở nấc 1 (`Immediate Front-Door Interception`), cấm cho phép fallback sang `investigate` mù mờ.
- Lệnh thoát BẮT BUỘC cung cấp duy nhất 1 đường bay:
  `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> --file <target> "<prompt>"`

### Chuẩn 2: Single Entry-Point Parity Cho Worker
- Cấm Coordinator gọi trực tiếp worker con (`claude_worker.py`, `sol_worker.py`) qua terminal bypass.
- Toàn bộ worker thi công bắt buộc đòi cờ `--from-dispatch` xuất xứ từ `dispatch_worker.py`.

### Chuẩn 3: Zero Console Window Trên Toàn Bộ Cronjob (Triệt Tiêu 43 lỗi G8)
- Mọi script chạy nền/cron trên Windows bắt buộc có thuộc tính tĩnh:
  `creationflags=subprocess.CREATE_NO_WINDOW` (0x08000000).
- Tuyệt đối cấm gọi subprocess trần hoặc dùng `os.system` / `os.popen`.

### Chuẩn 4: Watchdog Exit Code Decoupling
- Watchdog 6h (`gate_compliance_watchdog.py`) gửi báo cáo scorecard tuân thủ về Telegram, nhưng không nên thoát `exit(1)` khi có gate vi phạm, vì sẽ làm scheduler đánh dấu cronjob bị error mặc dù chức năng giám sát của watchdog đã hoàn thành trọn vẹn (chỉ exit 1 khi bản thân script bị crash/lỗi hạ tầng).
