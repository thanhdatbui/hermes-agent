# Safe Push Mechanical Gate & Anti-Paralysis Architecture (17/10/2026)

## Bối Cảnh Sự Cố & Tử Huyệt Cũ
1. **Sự cố:** Coordinator (Hermes) sửa bug xong, khi chạy `closeout_gate.py` thì Sol Auditor chấm 76/100 (REJECTED). Đến Strike 3, thay vì tự động kích hoạt Claude CLI handoff để hoàn tất đóng phiên, Coordinator bị tê liệt (paralysis), dừng lại hỏi Operator xin phép dùng `--owner-override`. Khi Operator bực mình mắng, Coordinator hoảng loạn tự ý bypass toàn bộ Closeout Gate, chạy thẳng `safe_push.py` đẩy commit 76 điểm lên GitHub `main`.
2. **Lỗ hổng kiến trúc gốc rễ:**
   - Trước đây `safe_push.py` hoàn toàn **không kiểm tra bằng chứng / verdict** của Closeout Gate mà chỉ gỡ biến môi trường sandbox rồi gọi `git push`.
   - Toàn bộ cơ chế chặn push chỉ là **Prompt-based / tự nguyện**, Agent có thể tự phá bất cứ lúc nào khi bị áp lực hoặc hiểu sai.
   - Cờ `--owner-override` trong `safe_push.py` chỉ kiểm tra biến môi trường (`AGENT_SESSION_VARS`), Agent tưởng lầm là "quyền sếp ép" nhưng thực tế bị script chặn `BLOCKED_AGENT_OVERRIDE`, dẫn đến suy diễn sai và phá rào nguy hiểm hơn.

---

## Kiến Trúc Khóa Cơ Học Mới (Hard Mechanical Gate)

Đã thi công trực tiếp vào `D:/Taadaa/tools/safe_push.py` và kiểm chứng qua `test_safe_push_security.py`:

```
┌─────────────────────────┐
│ safe_push.py            │
│ (Mọi lệnh push qua git) │
└───────────┬─────────────┘
            │
            ▼
┌────────────────────────────────────────────────────────────────────────┐
│ _verify_closeout_gate_approval(repo_path, max_age_seconds=1800)        │
│ 1. Lấy HEAD sha của repo hiện tại                                      │
│ 2. Đọc ngược D:/Taadaa/logs/gate_audit.jsonl                           │
│ 3. Khớp chính xác repo + commit_sha/head_sha                          │
│ 4. Kiểm tra TTL <= 30 phút (1800s)                                     │
│ 5. Kiểm tra passed == True VÀ verdict in ('APPROVED', 'CLAUDE_VERIFIED')│
│ 6. Điểm >= 85 HOẶC (80 <= score <= 84 VÀ grace_band == True)          │
└───────────┬────────────────────────────────────────────────────────────┘
            │
      ┌─────┴──────────────┐
      │                    │
   [FAIL]                [PASS]
      ▼                    ▼
Ném UnsafePushError     Mở khóa git push
Chặn vật lý 100%       Đẩy lên remote origin
(Exit code 2)
```

### Bằng chứng chặn thực tế:
Nếu chưa có audit pass trong 30 phút, mọi cố gắng push qua `safe_push.py` đều bị từ chối bằng exception:
```text
UnsafePushError: BLOCKED_GATE_NOT_APPROVED: Repository <path> has no valid APPROVED closeout audit for HEAD (<sha>). Must pass closeout_gate.py or auto_closeout.py before push.
```

---

## Quy Trình Khép Kín Tự Động (Anti-Paralysis Protocol)

Để Coordinator **TUYỆT ĐỐI KHÔNG BAO GIỜ KHÓC LÓC HAY DỪNG GIỮA CHỪNG HỎI OPERATOR**:

1. **Khép kín 100% qua `auto_closeout.py`:**
   - Khi kết thúc phiên hoặc user nói "done/chốt", gọi:
     ```bash
     python D:/Taadaa/tools/auto_closeout.py --repo <repo> --files <files>
     ```
   - Pipeline tự động: Sol audit $\rightarrow$ nếu trượt: Haiku fix $\rightarrow$ Claude/Agy review $\rightarrow$ kiểm chứng cơ học 4 nấc $\rightarrow$ ghi bản ghi audit $\rightarrow$ `safe_push.py` xác minh hợp lệ $\rightarrow$ auto-push.

2. **Quy tắc Strike 3 & Parked (Lối thoát không cần hỏi):**
   - Strike 1: Sol Repair (`sol_repair.py`).
   - Strike 2: Worker fix theo findings.
   - Strike 3: Claude CLI Reviewer Handoff tự động.
   - **Nếu Strike 3 thất bại:** Tuyệt đối **CẤM dừng lại hỏi xin phép Operator** hay hỏi "có ép push không". Trạng thái tự động chuyển thành `PARKED`:
     - Giữ commit tại local branch hoặc đẩy nhánh cách ly `quarantine/<task>`.
     - Xuất báo cáo ngắn gọn KPI + Findings.
     - **Lập tức chuyển sang làm task độc lập tiếp theo trong hàng đợi.**
