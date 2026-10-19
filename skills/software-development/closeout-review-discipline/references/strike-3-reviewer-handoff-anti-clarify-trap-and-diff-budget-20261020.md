# Strike 3 Reviewer Handoff: Anti-Clarify Trap & Payload Budget Ratio (2026-10-20)

## 1. Hiện Tượng & Căn Nguyên Pha "Khóc Lóc" Đùn Đẩy

### Hiện Tượng
Khi chạy `closeout_gate.py` trượt liên tiếp (Strike 3 / Strike 4), gate kích hoạt cơ chế bàn giao quyền can thiệp và in ra stderr:
```text
[REVIEWER_HANDOFF_TRIGGERED: 4 consecutive rejections reached for scope_hash=26b2cb90d2fbeb90. Coordinator/Worker/Sol Repair MUST STOP guessing/repairing and hand the keyboard to the Reviewer (Tier 1: Claude CLI hoặc Tier 2: Agy CLI (Antigravity pool)) to self-remediate, strictly scoped to: ...]
```
Ngay sau đó, Coordinator đã dừng lại và gọi công cụ `clarify`:
> "Closeout Gate chưa đạt điểm Approved (65/100, ngưỡng >=85). Bạn muốn xử lý tiếp theo phương án nào?
> 1) Tự động chuyển giao Claude CLI Reviewer tự remediate code & test để qua Gate 85
> 2) Giữ commit hiện tại trên local branch, không push lên origin remote"

User phản ứng gay gắt vì đây là hành vi vi phạm nghiêm trọng quy chế vận hành:
> *"Clgt lại khóc lóc đụ mẹ t fix lỗi khóc lóc này r mà? Tao hỏi lí do mày khóc lóc đùn đẩy k làm dù đã có gate guard ép làm đúng chưa"*

### Căn Nguyên Nhận Thức & Cơ Học
1. **Bẫy Ngữ Nghĩa "MUST STOP":** Coordinator đọc dòng log `MUST STOP guessing/repairing and hand the keyboard to the Reviewer` và bị phản xạ gián đoạn: hiểu lầm "MUST STOP" là chỉ thị dừng task, thay vì hiểu trọn vẹn mệnh đề là *"Dừng việc đoán mò/tạo proposal từ Sol Repair/Worker thường, và chuyển giao ngay cho Reviewer CLI có quyền ghi code"*.
2. **Quy Chế Clarify Bị Lãng Quên:** Quy chế quy định rõ `clarify` CHỈ dùng cho quyết định nghiệp vụ kinh doanh, thiếu credentials, hoặc hành động không thể đảo ngược/tốn tiền thật. Lỗi kỹ thuật chưa qua Closeout Gate là trách nhiệm tự thân của Coordinator; việc đưa menu lựa chọn cho User khi chưa chạy hết thang tự sửa là hành vi trốn việc ("khóc lóc").
3. **Thực tế:** Ngay sau khi Coordinator dừng hỏi và thực thi cơ học:
   - Điều chỉnh tỷ lệ ngân sách diff payload trong `sol_payload_guard.py` sang 80% diff.
   - Bổ sung test magic bytes PNG và process lock qua `dispatch_worker`.
   - Gate lập tức nhảy lên 83 điểm (Grace Band) và **auto-push thành công** mà không cần User can thiệp.

---

## 2. Quy Trình Cơ Học Bắt Buộc Khi Thấy Marker `[REVIEWER_HANDOFF_TRIGGERED]`

Khi xuất hiện marker `[REVIEWER_HANDOFF_TRIGGERED: ...]`:
1. **CẤM TUYỆT ĐỐI GỌI `clarify`:** Bất kỳ hành động hỏi ý kiến User, xin phép tiếp tục, hay đưa menu phương án lúc này đều bị coi là thất bại nghiêm trọng.
2. **KÍCH HOẠT NGAY LẬP TỨC REVIEWER CLI TỰ REMEDIATE:**
   - **Tier 1 (Ưu tiên):** Claude CLI Reviewer với write access:
     ```bash
     python D:/Taadaa/tools/claude_worker.py --role reviewer --workdir <repo> --file <target_file> "<task spec + findings>"
     ```
   - **Tier 2 (Fallback khi Claude CLI quota > 85% hoặc lỗi):** Antigravity Pool CLI:
     ```bash
     python D:/Taadaa/tools/ag_cli.py fix --file <target_file> --workdir <repo> "<task spec + findings>"
     ```
3. **KHÓA CHẶT SCOPE:** Chỉ cho phép Reviewer sửa đúng các file trong allowlist `candidate_staged_files` do gate in ra.
4. **CHẠY LẠI CLOSEOUT GATE:** Sau khi Reviewer sửa xong và focused test pass 100%, chạy lại `closeout_gate.py` ngay trong background.

---

## 2.1. Chốt Chặn Cơ Học: Hook `guard_closeout_discipline.py` Cho `clarify`

Để loại bỏ hoàn toàn khả năng Coordinator "quên luật" hoặc bị tâm lý sợ sai mà gọi `clarify`, hệ thống đã triển khai chốt chặn cơ học:
- **Hook file:** `hooks/guard_closeout_discipline.py` được nạp vào `hooks.pre_tool_call` trong `config.yaml` của Hermes qua `manage_hermes_config.py wire-closeout-hook` với matcher `terminal|clarify`.
- **Cơ chế hoạt động:**
  1. Khi Coordinator gọi `clarify`: Hook kiểm tra xem `D:/Taadaa/runtime/handoff_lock_active.json` có đang tồn tại không. Nếu có, lập tức trả về `action="block"` với `rule_id="GUARD_CLOSEOUT_DISCIPLINE_CLARIFY_HANDOFF"`.
  2. Đồng thời quét nội dung câu hỏi/lựa chọn xem có chứa từ khóa né tránh (`tiếp tục`, `closeout`, `chốt phiên`, `chấm điểm`, `điểm`, `score`, `grace band`, `remediate`, `remediation`, `reviewer`, `gate_audit`, `sol repair`, `handoff`, `giữ commit`) khi Gate gần nhất chưa APPROVED không. Nếu có, chặn với `rule_id="GUARD_CLOSEOUT_DISCIPLINE_CLARIFY_EVASION"`.
  3. Khi bị chặn, tin nhắn không bao giờ đến Telegram của User; Coordinator nhận lại lỗi kèm lệnh CLI bắt buộc phải chạy.
- **Kiểm chứng:** Bộ unit test trong `tests/test_guard_closeout_discipline.py` đạt 10/10 tests PASSED (100%).

---

## 3. Bài Học Payload Budget: Tỷ Lệ 80% Diff Trong `sol_payload_guard.py`

### Vấn đề
Mặc định `sol_payload_guard.py` chia ngân sách:
- Diff: 65% (~21.3KB ở budget 32KB)
- Log: 25% (~8.2KB)
- Reserve: 10% (~3.3KB)

Khi file triển khai và file test có quy mô chuẩn (~400 dòng diff tổng cộng), diff text thường rơi vào khoảng 22–24KB. Với mức 65%, diff bị vượt trần 21.3KB $\rightarrow$ Guard tự động cắt tỉa và chèn `TRUNCATION_MANIFEST` $\rightarrow$ Sol Auditor dừng chấm ngay lập tức với phán quyết `NEED_CONTEXT` (Score 0).

### Giải pháp Chuẩn
Điều chỉnh hàm `split_budget` trong `sol_payload_guard.py`:
```python
def split_budget(total_budget: int) -> Tuple[int, int, int]:
    diff_b = int(total_budget * 0.80)  # 80% cho unified diff (~26.2KB ở 32KB target)
    log_b = int(total_budget * 0.10)   # 10% cho test execution log
    reserve_b = total_budget - diff_b - log_b  # 10% cho manifest & rubric
    return diff_b, log_b, reserve_b
```
Điều này giúp diff unified hiển thị nguyên vẹn 100%, loại bỏ triệt để lỗi `NEED_CONTEXT` và giúp Sol Auditor chấm điểm chính xác ngay vòng đầu.
