# Closeout Remediation Monopoly and Dispatch Audit Truth

## 1. First-Responder Monopoly trong Closeout Remediation (Strike 1 & 2)
- **Quy tắc bất biến:** Khi chạy Closeout Gate (`closeout_gate.py`) và nhận điểm < 85 (REJECTED):
  - **Strike 1 & 2:** BẮT BUỘC **Sol High** (`python D:/Taadaa/tools/sol_repair.py` qua cổng `:20129`) ĐỘC QUYỀN tạo patch proposal $O(1)$ đầu tiên (First-Responder Monopoly).
  - Coordinator áp dụng proposal này và hậu kiểm `git diff --numstat <= 30` dòng.
  - **CẤM TUYỆT ĐỐI** Coordinator tự ý dispatch Worker (Haiku CLI qua `dispatch_worker.py`, subagent Gemini pool, hay Agy CLI) hay kích hoạt L2 Emergency Surgery trong Closeout Remediation khi Sol Repair vẫn còn sống.
- **Điều kiện duy nhất để Fallback Worker:**
  - `sol_repair.py` bị exit != 0, crash hoặc timeout.
  - Proposal trả về có `valid: false`.
  - Proposal sửa vượt ngân sách (`numstat > 30` dòng).
  - Patch của Sol áp dụng làm fail focused test offline.
- **Strike 3 Hand-off:**
  - Nếu trượt 3 lần liên tiếp trên cùng `scope_hash`, CẢ Coordinator, Worker VÀ Sol Repair ĐỀU PHẢI DỪNG LẠI, kích hoạt chuyển giao quyền can thiệp cho Claude CLI theo quy định.

## 2. Anti-Hallucination: Điều tra nhật ký Dispatch & Quota Spike
- **Bối cảnh sự cố:** Khi tài khoản Claude bị nhảy vọt hạn mức (% trong block 5h hoặc tuần), Coordinator không được đoán mò hoặc ghép đôi sai lệch giữa các tiến trình diễn ra cùng khung giờ.
- **Quy tắc đối soát log `D:/Taadaa/logs/dispatch.jsonl`:**
  - Kiểm tra chính xác trường `file`, `workdir`, `category`, `reason` và `exit_code`.
  - `dispatch_worker.py` là cổng điều phối cho các task fix code thông thường (Tier 1: Haiku CLI, Tier 2: Agy CLI).
  - Closeout Gate (`closeout_gate.py`) chạy độc lập qua reviewer API Sol High (:20129), hoàn toàn KHÔNG gọi `dispatch_worker.py` trong luồng chuẩn.
  - Tuyệt đối không nhầm lẫn giữa việc gọi Haiku để sửa file công cụ (`claude_quota_guard.py`) với luồng thẩm định chốt phiên của repo nghiệp vụ.
