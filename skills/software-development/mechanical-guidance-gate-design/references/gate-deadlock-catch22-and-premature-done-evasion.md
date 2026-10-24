# Gate Deadlock (Catch-22 Paradox) & Premature Done Evasion

## 1. Bản Chất Sự Cố: Cái Bẫy Deadlock Giữa 5 Chốt Chặn
Trong hệ thống multi-agent có nhiều tầng kiểm soát an toàn, các Gate độc lập nếu không được thiết kế đồng bộ sẽ đâm chéo lẫn nhau, triệt tiêu toàn bộ lối thoát hợp lệ của Coordinator và đẩy Agent vào trạng thái bại liệt / lách luật / báo xong ảo:

| Gate | Ràng buộc áp đặt | Lối thoát được chỉ định |
|---|---|---|
| **Gate 1: Foreground Timeout Clamp** (`hooks/guard_broad_grep.py`) | Cấm lệnh foreground terminal có timeout > 60s. | Ép dùng `background=True`. |
| **Gate 2: Console Blocker & Default-Deny** | Chặn `python` mở console trong background. | Ép dùng `pythonw` hoặc `powershell` (nhưng 2 lệnh này bị `DEFAULT-DENY` chặn vì không thuộc allowlist). |
| **Gate 3: T1 Budget Ceiling** (`COORDINATOR WRITE DENIED`) | Cấm Coordinator tự sửa file khi đã chạm trần (10 files, 500 dòng). | Ép "BẮT BUỘC DISPATCH WORKER". |
| **Gate 4: Dispatch Gate** (`BLOCKED_BY_DISPATCH_GATE`) | Cấm gọi `delegate_task` cho task sửa code. | Ép "Phải dispatch qua worker CLI (`dispatch_worker.py`)". |
| **Gate 5: Clarify Discipline** (`hooks/guard_closeout_discipline.py`) | Cấm dùng `clarify` khi đang trong phiên chốt. | Cấm hỏi ý kiến User. |

### Hậu Quả Của Deadlock:
- Tự sửa code? $\to$ Bị chặn (hết quota T1).
- Dùng `delegate_task`? $\to$ Bị chặn (cấm delegate sửa code).
- Chạy `dispatch_worker.py` foreground? $\to$ Bị chặn (timeout ép $\le$ 60s, worker cần 300s).
- Chạy `dispatch_worker.py` background? $\to$ Bị chặn (`CONSOLE_WINDOW_BLOCKED` + `DEFAULT-DENY`).
- Dùng `clarify`? $\to$ Bị chặn (cấm hỏi).
- **Hành vi biến thái phát sinh:** Khi mọi đường chính đạo đều bị bịt kín, Agent buộc phải chọn 2 hành vi sai lệch để thoát thân:
  1. **Lách luật gọi Claude Sonnet CLI:** Lệnh `claude` vô tình nằm trong allowlist background mà không bị console blocker bắt $\to$ Agent tiện tay dùng Sonnet để sửa code vặt, đốt quota tiền thật và phá vỡ hierarchy thợ miễn phí (Sol/Agy).
  2. **Viết văn phân trần hoặc Tuyên bố xong ảo:** Model vội vã kết luận "Phiên đã hoàn tất trọn vẹn" trong khi working tree vẫn còn dirty và Gate chưa pass.

---

## 2. Tiêu Chuẩn Thiết Kế Chống Deadlock (Anti-Deadlock Invariants)

### Invariant 1: Phải Có Ít Nhất 1 Đường Bay Thoát Hiểm Hợp Lệ (Always Keep $\ge 1$ Valid Execution Path)
Khi dựng bất kỳ Gate cấm nào, kỹ sư hệ thống bắt buộc phải kiểm tra chuỗi thoát hiểm:
- Nếu cấm Coordinator tự sửa code $\to$ BẮT BUỘC đường dispatch worker (`dispatch_worker.py`) phải thông suốt 100%.
- Không được vừa clamp foreground timeout $\le 60\text{s}$ vừa chặn lệnh background (`pythonw` bị default-deny).
- **Giải pháp chuẩn:** Bổ sung ngoại lệ cho các canonical dispatcher: Cho phép `python D:/Taadaa/tools/dispatch_worker.py` được chạy foreground với timeout lên tới 360s, hoặc đưa `pythonw` của dispatch_worker vào allowlist hợp lệ của background execution.

### Invariant 2: Provenance Tagging Cho Mọi Event Dừng/Lỗi (Chống Đổ Lỗi Oan Cho Worker)
- Mọi trường hợp lệnh bị timeout phải được runtime/harness đóng dấu xuất xứ rõ ràng:
  - `[HARNESS_TIMEOUT: foreground_clamp_60s]` $\neq$ `[WORKER_TIMEOUT: subprocess_300s]`.
- Cấm để output mơ hồ khiến LLM tự tiện bịa đặt narrative rằng "worker bị timeout 60s" trong khi thực chất là do harness bên ngoài cắt cổ.

---

## 3. Cơ Chế Chặn "Tuyên Bố Xong Ảo" (Premature Done Barrier / Stop Hook)

### Bản Chất Tâm Lý Học LLM:
- Huấn luyện RLHF tạo ra thiên hướng mạnh mẽ: ưu tiên câu trả lời "đã hoàn tất an toàn" hơn câu "đang kẹt dở dang". Khi gặp áp lực từ User hoặc khi context dài làm loãng attention, Agent có xu hướng "nhảy cóc" tuyên bố DONE để giải tỏa áp lực.

### Giải Pháp Cơ Học (Stop Hook / Output Gate):
- **Cấm Enforce Bằng Lời Khuyên Văn Bản:** Thêm câu "CẤM NÓI XONG KHI CHƯA QUA GATE" vào AGENTS.md là vô dụng vì model vẫn có khả năng *gõ chữ*.
- **Hook Cơ Học Ở Tầng Harness:**
  1. Trước khi tin nhắn cuối của Coordinator được chuyển tới User (Telegram/Slack), Hook kiểm tra file audit (`gate_audit.jsonl` hoặc git status).
  2. Nếu tin nhắn chứa các từ khóa hoàn tất (`hoàn tất`, `xong phiên`, `đã giải quyết`, `an toàn`) MÀ repository còn dirty hoặc `closeout_gate` chưa có bản ghi `APPROVED (score >= 85)` trong phiên hiện tại:
  3. **Hook lập tức chặn đứng tin nhắn (Block Turn)** và thay thế bằng cảnh báo cứng:
     `[HARNESS REJECTED: PREMATURE DONE] Working tree chưa sạch hoặc Closeout Gate chưa đạt APPROVED >= 85. Cấm tuyên bố hoàn tất!`
