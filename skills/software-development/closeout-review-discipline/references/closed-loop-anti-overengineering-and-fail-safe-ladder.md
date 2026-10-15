# Closed-Loop Anti-Overengineering & 4-Tier Fail-Safe Ladder (16/10/2026)

## 1. Bối cảnh Sự cố: Bẫy Cày Điểm Vô Tận 27 Vòng (The 27-Round 6-Hour Trap)
- **Hiện tượng:** Coordinator bị kẹt trong vòng lặp thẩm định Closeout Gate từ 00:00 đến 06:00 sáng (27 vòng lặp), liên tục vi sửa đổi mã nguồn và test suite để "chiều" Reviewer Sol High (:20129).
- **Phản ứng của Operator:**
  > *"Vkl mày ơi mày bị clg làm từ 12h tới tận 6h trời ơi. Có nên tiếp tục giữ sol làm reviewer k thế? Bữa h xài bth tự nhiên hqua tới h mỗi lần bảo chốt phiền mày toàn chạy mấy chục vòng tốn 4-5h của tao có bị over engineer quá không... Vấn đề t cần là tự động hoá chứ k phải fail r báo blocked khóc lóc"*
- **Nguyên nhân gốc rễ (Root Cause):**
  1. **Bẫy Goodhart & Vùng Nhiễu Điểm Số LLM:** Điểm số 82–84 và 85 của Sol High nằm trong dải nhiễu thống kê ngẫu nhiên (noise zone) của LLM. Khi dùng điểm số 85 làm cổng chặn cứng, Coordinator bị cuốn vào việc tối ưu theo điểm số thay vì an toàn farm thật: cắt tỉa từng byte diff (< 21KB), đo `duration_ms` của subprocess, viết test zombie escalation... Càng sửa thì diff càng phình, Sol lại tìm ra điểm trừ mới, sinh ra vòng lặp vô tận.
  2. **Đứt gãy Hand-off tại Strike 3:** Khi `closeout_gate.py` kích hoạt `REVIEWER_HANDOFF_TRIGGERED`, hệ thống chỉ ghi log chứ không tự động dispatch `claude_worker.py`. Đồng thời `claude_worker.py` bị chặn bởi cache `stale_quota` (> 2h), fallback sang `ag_cli.py` bị timeout. Coordinator mất phương hướng và quay lại dùng subagent mò mẫm suốt 27 vòng.

---

## 2. Kỷ Luật Tự Động Hóa Tuyệt Đối (Closed-Loop Autonomous Invariant)
Operator yêu cầu: **"Tự động hoá dứt điểm đến DONE, không dừng lại khóc lóc báo BLOCKED"**.

### Quy tắc bất biến:
- **CẤM DỪNG LẠI HỎI XIN PHÉP:** Khi chạm Strike 3, Coordinator BẮT BUỘC tự động chuyển giao quyền can thiệp cho Claude CLI / Antigravity CLI. CẤM hỏi "anh có muốn gọi Claude CLI không?", CẤM dùng `clarify` để đùn đẩy trách nhiệm.
- **TIÊU CHUẨN DUY NHẤT CHO "BLOCKED":**
  * **HỢP LỆ:** Lỗi phần cứng vật lý ngoài tầm kiểm soát từ xa (cháy nổ máy farm, sập nguồn trạm điện, đứt cáp USB, rơi vỡ màn hình) hoặc thao tác tốn tiền thật / xóa sạch database cần con người phê duyệt.
  * **BẤT HỢP LỆ (CẤM TUYỆT ĐỐI):** Mọi lỗi code, test fail, import error, linting, hay cạn quota. Toàn bộ lỗi phần mềm bắt buộc phải tự động nhảy tầng qua Thang Cứu Hộ 4 Tầng để kéo về **DONE**.

---

## 3. Thang Cứu Hộ 4 Tầng Khi Cạn Quota (Fail-Safe Ladder)

Khi gặp lỗi phức tạp hoặc khi một công cụ cạn quota, hệ thống tự động leo thang tuần tự qua 4 tầng:

```text
[Strike 3 Hand-off / Code Fix]
                 │
                 ▼
    [TẦNG 1: Claude CLI (Worker Role)]
    (claude_worker.py --role worker, in-place edit, focused pytest)
                 │
                 ▼ (Nếu Claude hết 5h session limit hoặc stale quota)
    [TẦNG 2: Antigravity CLI (ag_cli.py fix)]
    (Cụm Pool 7 tài khoản Google Pro xoay vòng, model gemini-3.8-flash-high)
                 │
                 ▼ (Nếu cả 7 tài khoản AG CLI đều chạm rate limit)
    [TẦNG 3: Emergency Surgery L2 (Coordinator In-Session)]
    (Coordinator tự sửa trực tiếp O(1) <= 30 dòng, <= 2 files, offline test < 30s)
                 │
                 ▼ (Nếu diff lớn > 30 dòng và cả 2 CLI đều cạn)
    [TẦNG 4: Van An Toàn Subagent (delegate_task)]
    (Gắn cờ WORKER_CLI_EXHAUSTED: true để mở van Coordinator Guard)
```

### Chi tiết các tầng:
1. **Tầng 1 (Claude CLI):**
   - Mặc định cho các task Strike 3 Hand-off.
   - Bắt buộc prompt in-place: `"Directly edit in place in the current repository without creating any worktrees. Do not touch other uncommitted files."`
   - Bắt đầu bằng động từ hành động dạng mệnh lệnh (`Add...`, `Fix...`, `Refactor...`).
2. **Tầng 2 (Antigravity CLI - `ag_cli.py fix`):**
   - Tự động kích hoạt khi `claude_worker.py` phát hiện `hit your session limit` hoặc `fh >= 85%`.
   - Quản lý xoay vòng 7 profiles độc lập tại `D:/Taadaa/agy_profiles`, hoàn toàn tách biệt với Claude.
3. **Tầng 3 (Emergency Surgery L2):**
   - Áp dụng khi diff nhỏ ($O(1) \le 30$ dòng): sửa ốc lỏng, sửa syntax, thêm assertion, điều chỉnh timeout.
   - Coordinator tự sửa trực tiếp, chạy test mocked/offline < 30s, commit tiền tố `[L2-surgery]`. Không cần xin phép.
4. **Tầng 4 (Van an toàn Subagent):**
   - Chỉ dùng khi task lớn (> 30 dòng) và cả Claude CLI lẫn AG CLI đều cạn kiệt tài nguyên.

---

## 4. Cải Tổ Cơ Chế Closeout Gate: Severity-Based vs Score-Based

### Sai lầm của cơ chế điểm số (Score-Based >= 85):
- Ép model LLM chấm một con số vô cảm trong vùng nhiễu 80–85.
- Biến Coordinator thành "thợ cày điểm" thay vì giải quyết lỗi an toàn farm thực tế.

### Chuẩn hóa cơ chế phán quyết theo mức độ nghiêm trọng (Severity-Based):
1. **Phân loại findings của Sol High:**
   - **`BLOCKER`:** Lỗi logic chết người, race condition gây treo máy farm, xung đột port 5037 của farm, thiếu fail-closed. **BẮT BUỘC SỬA.**
   - **`MAJOR` / `NIT`:** Góp ý kiến trúc (tách class, refactor state machine), style, đo latency, microsecond metrics. **Ghi nhận vào log, KHÔNG CHẶN CLOSEOUT.**
2. **Điều kiện hoàn tất phiên (Closeout Done):**
   - `Pytest pass 100%` trên máy thật.
   - `BLOCKER == 0`.
   - Git diff sạch, không có uncommitted changes ngoài scope.
3. **Trần tối đa 3 vòng review:**
   - Vòng 1 & 2: `sol_repair.py` tự động đề xuất patch $O(1)$ và áp dụng.
   - Vòng 3: Claude CLI / AG CLI tự động giải quyết dứt điểm.
   - Sau vòng 3: Nếu không còn `BLOCKER`, tự động thông qua và push git. CẤM chạy vòng thứ 4.
