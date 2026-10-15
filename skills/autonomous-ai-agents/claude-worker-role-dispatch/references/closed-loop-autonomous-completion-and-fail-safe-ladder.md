# Closed-Loop Autonomous Completion & 4-Tier Fail-Safe Ladder (16/10/2026)

## 1. Sự Cố Kẹt 27 Vòng Vô Tận & Đứt Gãy Strike 3 Hand-off
- **Bối cảnh:** Trong phiên thẩm định Closeout Gate, Coordinator lặp lại 27 vòng từ 00:00 đến 06:00 sáng để cày điểm Sol High từ 82 lên 86 điểm, sa vào bẫy Goodhart tối ưu hóa số liệu vô nghĩa (cắt tỉa từng byte diff, đo microseconds, viết test zombie escalation...).
- **Chỉ thị của Operator:**
  > *"Vấn đề t cần là tự động hoá chứ k phải fail r báo blocked khóc lóc. Nếu claude worker hết quota thật thì sao?"*
- **Nguyên nhân Hand-off đứt gãy:**
  1. `closeout_gate.py` chỉ print `[REVIEWER_HANDOFF_TRIGGERED]` ở stderr chứ không tự động dispatch `claude_worker.py`.
  2. `claude_worker.py` gặp `stale_quota` (>2h) tự động fallback sang `ag_cli.py` và bị timeout.
  3. Coordinator rơi vào bại não (paralysis), quay lại spawn Worker `delegate_task` lặp đi lặp lại 27 lần thay vì thi công dứt điểm.

---

## 2. Kỷ Luật Tự Động Hóa Tuyệt Đối (Anti-Paralysis Invariant)
- **CẤM BÁO BLOCKED / KHÓC LÓC VÌ LỖI CODE HOẶC CẠN QUOTA:**
  * Báo `BLOCKED` chỉ hợp lệ khi gặp lỗi vật lý ngoài đời thực (sập nguồn trạm điện farm, rơi cáp ADB, vỡ màn hình, mất mạng ISP) hoặc thao tác tốn tiền thật/xóa database cần User phê duyệt.
  * Mọi lỗi code, test failure, gate rejection, hay cạn quota BẮT BUỘC phải tự động giải quyết đến **DONE** bằng cách nhảy tầng qua Thang Cứu Hộ 4 Tầng.
- **CẤM DỪNG LẠI HỎI XIN PHÉP:**
  * Khi chạm Strike 3, Coordinator BẮT BUỘC tự động chuyển giao cho Claude CLI / Antigravity CLI. CẤM hỏi "anh có muốn gọi Claude CLI không?", CẤM dùng `clarify` để đùn đẩy trách nhiệm.

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

### Cơ chế chi tiết từng tầng:
1. **Tầng 1 — Claude CLI (`claude_worker.py --role worker`):**
   - Đảm nhận Strike 3 Hand-off.
   - Bắt buộc prompt in-place: `"Directly edit in place in the current repository without creating any worktrees. Do not touch other uncommitted files."`
   - Mở đầu bằng động từ mệnh lệnh (`Add...`, `Fix...`, `Refactor...`).
2. **Tầng 2 — Antigravity CLI (`ag_cli.py fix`):**
   - Tự động kích hoạt khi Claude gặp `hit your session limit` hoặc `fh >= 85%`.
   - Quản lý xoay vòng 7 profiles Google Pro tại `D:/Taadaa/agy_profiles`, model `gemini-3.8-flash-high`.
3. **Tầng 3 — Coordinator L2 Emergency Surgery:**
   - Khi diff nhỏ ($O(1) \le 30$ dòng, $\le 2$ files): Coordinator tự sửa trực tiếp, test mocked/offline < 30s, commit `[L2-surgery]`. Không cần xin phép.
4. **Tầng 4 — Van an toàn Subagent:**
   - Chỉ dùng khi task lớn (> 30 dòng) và cả Claude CLI lẫn AG CLI đều cạn kiệt tài nguyên.

---

## 4. Trần 3 Vòng Closeout Gate & Cải Tổ Severity-Based
- **Trần tối đa 3 vòng review:**
  * Vòng 1 & 2: `sol_repair.py` tự động đề xuất patch $O(1)$ và áp dụng.
  * Vòng 3: Claude CLI / AG CLI tự động giải quyết dứt điểm.
  * Sau vòng 3: Nếu không còn `BLOCKER`, tự động thông qua và push git. CẤM chạy vòng thứ 4.
- **Severity-based Gate:** Đổi cổng chặn từ `Score >= 85` (vùng nhiễu) sang `BLOCKER == 0`. Các góp ý kiến trúc / micro-optimization xếp vào `MAJOR`/`NIT` và không chặn closeout.
