# Sol Repair First-Responder Monopoly & Strike 3 Hand-Off Architecture

## 1. Bối cảnh & Incident Mổ Xẻ (09/10/2026)
- **Sự cố:** Sau khi Closeout Gate chấm 82/100 (REJECTED), Coordinator vi phạm luật cứng, tự ý dispatch Worker Gemini subagent mò mẫm sửa code thay vì dùng công cụ chuyên dụng `sol_repair.py`. Worker cắn 15 calls rồi dính timeout 10 phút (600s) mà không sửa được dòng code nào.
- **Can thiệp của User:** User phản ứng gay gắt ("lí do mày đéo tuân thủ gọi sol repair? mày chỉ đc phép làm khi sol repair hỏng thôi"). Coordinator sau đó gọi `sol_repair.py`, Sol High tạo proposal O(1) trong 20s, apply và verify đạt ngay 88/100 APPROVED.
- **Thẩm định độc lập từ Claude Code CLI (Sonnet):**
  Claude Sonnet mổ xẻ và chỉ ra 5 xung đột cấu trúc cần khắc phục:
  1. Tách bạch vai trò Reviewer (`closeout_gate.py`) vs Repair Proposal Generator (`sol_repair.py`).
  2. Khóa chặt Strike 3: Coordinator, Worker và Sol Repair đều phải STOP khi trượt 3 lần liên tiếp, hand-off bàn phím cho Claude CLI.
  3. Bổ sung đầy đủ 4 điều kiện fallback sang Worker (exit!=0/crash/timeout, valid=false, numstat > 30, fail test).
  4. Khu biệt phạm vi cấm L2 chỉ trong pha Closeout Remediation.
  5. Hậu kiểm ngân sách O(1) cứng bằng `git diff --numstat <= 30` dòng thực tế.

---

## 2. Deterministic State Machine (Closeout Remediation)

```
                       [ USER RA LỆNH: "chốt phiên" / "done" ]
                                          │
                                          ▼
                         [ BƯỚC 1: Chạy closeout_gate.py ]
                     (Sol High chấm điểm độc lập qua :20129)
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
       [ VERDICT: APPROVED ]                         [ VERDICT: REJECTED ]
       (Score >= 85 / Exit 0)                         (Score < 85 / Exit 1)
                   │                                             │
                   ▼                                             ▼
          [ PUSH REMOTE & XONG ]                   [ BƯỚC 2: Kiểm tra Strike Counter ]
                                                 (Đọc audit chain: gate_audit.jsonl)
                                                                 │
                                     ┌───────────────────────────┴───────────────────────────┐
                                     ▼                                                       ▼
                       [ STRIKE 1 HOẶC STRIKE 2 ]                                       [ STRIKE 3 ]
                        (Lần trượt thứ 1 hoặc 2)                                 (Trượt 3 lần liên tiếp)
                                     │                                                       │
                                     ▼                                                       ▼
                      [ BƯỚC 3: SOL HIGH VÁ ĐỘC QUYỀN ]                         [ BƯỚC 4: CLAUDE CLI HAND-OFF ]
                      (Chạy tools/sol_repair.py ~20s)                             (Trao quyền bàn phím cho Claude)
                                     │                                                       │
                     ┌───────────────┴───────────────┐                                       ▼
                     ▼                               ▼                           Claude tự đọc code & finding
           [ SOL REPAIR THÀNH CÔNG ]       [ SOL REPAIR THẤT BẠI ]               Claude tự sửa & chạy test
          (Sinh patch hợp lệ, AST ok)     (Exit!=0, crash, numstat>30,                        │
                     │                           hoặc test fail)                              ▼
                     ▼                               │                              [ RERUN CLOSEOUT GATE ]
             Áp dụng patch O(1)                      ▼
             Hậu kiểm numstat <= 30          [ FALLBACK WORKER ]
             Chạy focused test <10s         (Dispatch Worker Gemini
                     │                      kèm contract thu hẹp)
                     ▼                               │
          [ RERUN CLOSEOUT GATE ]                    ▼
                                           Áp dụng patch Worker &
                                           chạy focused test <10s
                                                     │
                                                     ▼
                                          [ RERUN CLOSEOUT GATE ]
```

---

## 3. Bản Thiết Quân Luật (Operational Discipline Contract)

### Điều 1 — Độc quyền phản ứng đầu tiên (First-Responder Monopoly)
Khi Closeout Gate trả về `REJECTED`, hành động kế tiếp của Coordinator **BẮT BUỘC 100% PHẢI LÀ GỌI `sol_repair.py`**.
CẤM TUYỆT ĐỐI tự ý đoán mò, CẤM dispatch Worker/Gemini, CẤM dùng L2 trong pha Closeout Remediation khi Sol Repair chưa hỏng.

### Điều 2 — Điều kiện Fallback khách quan (Hard Evidence Fallback)
Coordinator **CHỈ ĐƯỢC PHÉP** fallback sang Worker khi và chỉ khi thỏa mãn 1 trong 4 điều kiện khách quan sau:
1. `sol_repair.py` trả về `exit code != 0`, crash exception trace, hoặc timeout process.
2. `sol_repair.py` trả về `valid: false` (không thể tạo patch cho finding).
3. Hậu kiểm `git diff --numstat` vượt quá trần $O(1)$ cứng: `> 30` dòng (tổng add + delete).
4. Patch của Sol khi áp dụng làm **FAIL focused test** hoặc gây lỗi hồi quy cú pháp.

### Điều 3 — Chốt chặn Strike 3 Reviewer Hand-Off (Tamper-Evident)
Khi audit chain ghi nhận `count_consecutive_rejections >= 3` trên cùng một `scope_hash`:
- CẢ Coordinator, Worker VÀ Sol Repair ĐỀU BỊ KHÓA CỨNG (phải dừng mọi hành động tạo patch/proposal).
- Nghiêm cấm chạy tiếp `sol_repair.py` ở Strike 3+.
- Hand-off quyền bàn phím trực tiếp cho **Claude Code CLI** (`claude -p` kèm allowlist hẹp và `--dangerously-skip-permissions`).
