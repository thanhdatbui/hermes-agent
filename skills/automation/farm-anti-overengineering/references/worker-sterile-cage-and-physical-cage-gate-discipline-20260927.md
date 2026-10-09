# Kỷ luật Lồng Vô Trùng Worker & Cổng Nghiệm Thu Vật Lý (Physical Cage Gate)

*Cập nhật ngày 27/09/2026 sau ca Luna Over-Engineering & Timeout 1200s*

---

## 1. Bệnh lý Over-Engineering của Worker (Luna / GPT series)
- Khi Worker nhận task mở, nhiều file hoặc thiếu ranh giới cứng:
  - Tự vẽ kiến trúc đa tầng P1/P2/P3, session lease, lock distributed, fsync atomic.
  - Tự gọi các vòng review lòng vòng (REJECT 58 -> MINOR 74 -> MINOR 76).
  - Tê liệt phòng thủ (Defensive Paralysis) khi thấy repo dirty, chạy đọc dạo cháy ngân sách và timeout 1200s.

---

## 2. Giải pháp: Lồng Vô Trùng 4 Tầng (Sterile Cage)

```
[Gemini Coordinator]
       │
       ▼ Lớp 1: Cấp Patch Contract O(1) + Tiêm Phân Vai Rõ Ràng (Prompt Gate)
       │
       ▼ Lớp 2: Git Worktree Sạch (Triệt tiêu nỗi sợ Dirty Repo)
       │
       ▼ Lớp 3: Hard Hook guard_dispatch_contract.py (Chặn Đa File + Ép Sol Plan)
       │
[Luna / Gemini Worker Thi Công]
       │
       ▼ Lớp 4: Cổng Nghiệm Thu Vật Lý (D:/Taadaa/tools/cage_gate.py)
```

---

## 3. Quy tắc Dispatch cho Coordinator

### A. Anti-Multi-File Gate (Chặn Gộp Việc):
- **1 task = DUY NHẤT 1 file code nghiệp vụ, Budget <= 30 dòng, Focused Test < 30s.**
- Hook `guard_dispatch_contract.py` sẽ **chặn vật lý ngay lập tức** (`[HARD GATE #3 - MULTI-FILE BLOCKED]`) nếu phát hiện $\ge 2$ file code trong 1 lệnh `delegate_task`.

### B. Cưỡng Chế Sol Plan & Fallback Valve:
- Mọi task sửa code phải có `SOL_PLAN_ID`.
- Hook tự động gọi `sol_planner.py` sang Sol Web (:20129) để lấy kế hoạch.
- Nếu Sol offline/timeout/refusal: Tự động kích hoạt `SOL_FALLBACK: <lý do>` cho phép Coordinator tự lập contract.

### C. Tiêm Bản Phân Vai Khóa Mõm Worker:
```text
[PHÂN CHIA TRÁCH NHIỆM]:
- Coordinator chịu 100% rủi ro an toàn và kiến trúc repo. Đó KHÔNG PHẢI việc của Worker.
- Worker là thợ vặn ốc: Chỉ sửa đúng file chỉ định <= 30 dòng để pass FOCUSED_TEST.
- CẤM tạo file mới, CẤM tạo file .md, CẤM refactor/đổi tên hàm.
- CẤM chạy git status, git log, git checkout. Chỉ chạy git diff trên file được giao.
- Có lo ngại ghi vào dòng NOTE rồi BẮT BUỘC LÀM TIẾP, CẤM dừng lại xin phép.
```

---

## 4. Nghiệm Thu Vật Lý Bằng `cage_gate.py`

Sau khi Worker hoàn thành, Coordinator BẮT BUỘC chạy script kiểm tra khách quan (Approved 96/100 từ Senior Reviewer):
```bash
python D:/Taadaa/tools/cage_gate.py --target-file <file> --test-cmd "<test_cmd>" --base <SHA>
```

- **Exit code 0 (APPROVED):** Nhận diff và merge.
- **Exit code 1 (REJECTED):** Sửa ngoài scope / vượt quá 30 dòng / test fail $\rightarrow$ Yêu cầu worker sửa lại đúng 1 lần. Lần 2 vẫn fail $\rightarrow$ Coordinator tự làm.
- **Exit code 2 (GATE_ERROR):** Lỗi môi trường git / worktree.
