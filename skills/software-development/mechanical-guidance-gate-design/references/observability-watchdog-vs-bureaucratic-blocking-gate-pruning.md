# Observability Watchdogs vs Bureaucratic Blocking Gates & Local Hash Chain Pruning

## 1. Phân Định Dứt Khoát: Observability Watchdogs vs Bureaucratic Blocking Gates
- **Chỉ đạo thực tế của Operator:**
  *"Còn cái watchdog hook gate gì đó thì để theo dõi agent có vận hành hook đúng k ví dụ như gọi worker python thì nên giữ lại chứ"*
- **Observability Watchdogs (`gate_compliance_watchdog.py`) — BẮT BUỘC GIỮ LẠI:**
  - *Bản chất:* Là công cụ đo lường và kiểm toán thụ động (passive telemetry). Không đứng ở critical path để chặn ngang tiến trình, không gây timeout hay đóng băng phiên.
  - *Chức năng:* Chạy nền định kỳ (báo cáo 6h) quét các log audit (`dispatch_audit.jsonl`, `guard_scan_audit.jsonl`, `console_block_audit.jsonl`) để thống kê vi phạm thực tế của Agent:
    * Agent có lén tự sửa code thay vì gọi Worker CLI (`subagent_edit_blocked`).
    * Agent có quét root diện rộng (`GUARD_SEARCH_FILES_ROOT`, `GUARD_DANGEROUS_ROOT`).
    * Tỷ lệ timeout, quota burn.
  - *Giá trị vận hành:* Cung cấp bức tranh trung thực để Operator và Coordinator nhận diện điểm nghẽn, bổ sung rule/guidance, tối ưu token.
- **Bureaucratic Blocking Gates (`closeout_gate.py` cũ, `safe_push.py` cũ) — CẮT BỎ TRIỆT ĐỂ:**
  - Đứng ở cửa ngõ ngăn chặn, bắt LLM Reviewer chấm điểm văn học cảm tính 85/100.
  - Tự động kích hoạt `sol_repair.py` đi sửa code ma khi làm tác vụ vận hành (đổi bio, pin clip).
  - Tự trói chân nhau bằng thủ tục giấy tờ giả cầy (đòi record JSONL cũ).

---

## 2. Triệt Tiêu Ảo Tưởng "Blockchain SHA256 Hash Chain" Trong Local Log File
- **Cơ chế lỗi thời (Anti-pattern):**
  Trong `closeout_gate.py`, hàm `_read_last_chain_hash()` băm SHA256 từng dòng log để tạo chuỗi bất biến (`prev_chain_hash` + `self_hash`).
- **Điểm mù chí mạng:**
  - Toàn bộ Agent, Gate, Worker và Script đều chạy dưới cùng một quyền User OS (`Kibe`). Một file text nằm trên đĩa local thì bất kỳ tiến trình nào cũng có quyền đọc/ghi. Việc cài cắm thuật toán blockchain không hề tăng cường bảo mật mà chỉ tạo ra Security Theater.
  - **Sự cố thực tế:** Khi một tiến trình hoặc công cụ khác ghi một dòng JSON bình thường không có trường `self_hash` (hoặc log bị gián đoạn giữa chừng), `_read_last_chain_hash()` quăng `RuntimeError: Corrupted or unreadable audit chain`, làm sập toàn bộ các lệnh chốt phiên của cả Farm!
- **Nguyên tắc O(1) đúng đắn:**
  1. Ghi log JSONL append-only thuần túy.
  2. Khi đọc log ngược, dùng fallback an toàn (`last_obj.get("self_hash", "GENESIS")`). Nếu dòng cuối thiếu hash, tiếp tục quét ngược dòng trước đó hoặc trả về giá trị mặc định, tuyệt đối không quăng exception chặn đứng luồng vận hành.

---

## 3. Dọn Dẹp safe_push.py: Độc Lập Khỏi File Log Cũ
- **Nguyên tắc:** Lệnh `git push` là thao tác chuyển giao code lên remote.
- **Không phụ thuộc file log cũ:** Cắt bỏ hoàn toàn việc đọc ngược `gate_audit.jsonl` tìm `APPROVED` trong vòng 30 phút. Nếu file log bị xóa, lệch múi giờ hoặc corrupt, `safe_push.py` không được làm kẹt luồng deploy.
- **Kiểm tra trực tiếp tại thời điểm push (Just-In-Time):**
  - Chỉ kiểm tra syntax `python -m py_compile` cho các file `.py` nằm trong diff `origin/main...HEAD`.
  - Không đòi hỏi chữ ký HMAC, không đòi điểm số văn học của Reviewer.
