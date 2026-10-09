# Sol Repair First-Responder Monopoly, 3-Strike Integration & Claude CLI Policy Audit (Incident 2026-10-09)

## 1. Bối Cảnh Incident: Coordinator Mắc Tật Tự Ý Dispatch Worker Khi Gate Reject
Trong phiên làm việc tại repo `automation-core`, Closeout Gate trả về `Verdict: REJECTED` (82/100 điểm).
- **Hành vi sai lầm của Coordinator:** Thay vì chạy ngay công cụ chuyên dụng `sol_repair.py` (:20129) để tạo đề xuất bản vá O(1), Coordinator lại tự động dispatch Worker Gemini.
- **Hậu quả:** Worker Gemini tiêu tốn hết ngân sách 15 tool calls mà không sửa được gì, chạm timeout 600s làm kẹt cả phiên làm việc 10 phút.
- **User can thiệp gắt gao:** *"lí do mày đéo tuân thủ gọi sol repair? mày chỉ đc phép làm khi sol repair hỏng thôi đkm. gọi claude cli tư vấn cho mày tuân thủ con mẹ mày"*.

---

## 2. Bản Thiết Quân Luật Được Claude Code CLI Phê Duyệt (VERDICT: APPROVED)

Sau 3 vòng thẩm định khắt khe của **Claude Code CLI (Sonnet)**, chính sách điều phối Closeout Remediation đã được chuẩn hóa và khóa chặt tại 4 file: `SOUL.md`, `HERMES_SUBAGENT_RULES.md`, `TIERED_WORKFLOW.md`, và `closeout_gate.py`:

```
                    [ CLOSEOUT GATE: REJECTED (< 85) ]
                                    │
                                    ▼
                      [ KIỂM TRA STRIKE COUNTER ]
                    (Đọc gate_audit.jsonl cùng scope)
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
       [ STRIKE 1 HOẶC STRIKE 2 ]              [ STRIKE 3 ]
                    │                               │
                    ▼                               ▼
    [ SOL REPAIR ĐỘC QUYỀN VÁ TRƯỚC ]      [ REVIEWER HAND-OFF ]
       (First-Responder Monopoly)          Coordinator, Worker VÀ
    python tools/sol_repair.py O(1)        Sol Repair ĐỀU PHẢI STOP!
                    │                               │
                    ▼                               ▼
      [ HẬU KIỂM NUMSTAT <= 30 DÒNG ]       Trao bàn phím cho
          (Enforcement thật)               CLAUDE CODE CLI (Sonnet)
                    │                      tự đọc finding & tự sửa.
         ┌──────────┴──────────┐
         ▼                     ▼
     [ PASS TEST ]       [ SOL FAIL / CRASH /
           │              TEST FAIL / NUMSTAT > 30 ]
           │                   │
           ▼                   ▼
    [ RERUN GATE ]     [ FALLBACK WORKER ]
                       (Chỉ khi có bằng chứng cứng)
                               │
                               ▼
                        [ RERUN GATE ]
```

---

## 3. Các Điều Khoản Cốt Lõi Khắc Cốt Ghi Tâm

### Điều 1: Độc Quyền Phản Ứng Đầu Tiên (First-Responder Monopoly)
- Khi Closeout Gate trả về `REJECTED`, hành động đầu tiên của Coordinator **BẮT BUỘC 100%** là chạy `sol_repair.py` (:20129).
- CẤM TUYỆT ĐỐI tự ý dispatch Worker mò mẫm hay làm Emergency Surgery L2 trong pha Remediation khi Sol Repair chưa hỏng.

### Điều 2: Điều Kiện Fallback Sang Worker Toàn Diện (Chống Treo Vô Hạn)
Coordinator **CHỈ ĐƯỢC PHÉP** fallback sang Worker khi và chỉ khi có 1 trong 4 bằng chứng khách quan:
1. `sol_repair.py` exit code != 0, crash exception trace, hoặc timeout.
2. `sol_repair.py` trả về `valid: false` (không tạo được patch giải quyết finding).
3. Patch của Sol khi áp dụng vi phạm trần cứng `git diff --numstat > 30` dòng.
4. Patch của Sol khi áp dụng làm FAIL focused test.

### Điều 3: Khóa Cứng Strike 3 Ở Cả Code Lẫn Policy
- Khi trượt 3 lần liên tiếp trên cùng `scope_hash`, `closeout_gate.py` phát tín hiệu `[REVIEWER_HANDOFF_TRIGGERED]`.
- **CẢ Coordinator, Worker VÀ Sol Repair ĐỀU PHẢI STOP** — nghiêm cấm lách luật tiếp tục gọi Sol Repair ở Strike 3+.
- Trong code `closeout_gate.py`:
  ```python
  if not passed and getattr(args, "auto_repair", False) and not reviewer_handoff_triggered:
      # Chỉ kích hoạt auto-repair khi Strike 3 chưa bị kích hoạt!
  ```
- Coordinator bàn giao trực tiếp quyền can thiệp cho **Claude Code CLI** (`claude -p`) làm Reviewer-with-write-access.

---

## 4. Bài Học Kỹ Thuật Khi Viết Patch Contract Cho Policy Monolith (Từ Claude Sonnet Audit)
1. **Tránh bẫy eval của Bash:** Khi truyền prompt chứa backticks (`` ` ``) vào CLI qua bash, bash sẽ cố thực thi chuỗi đó dưới dạng command substitution. Bắt buộc phải lưu nội dung proposal ra file `.md` rồi yêu cầu CLI đọc file trực tiếp.
2. **Tránh bẫy Tautological Test:** Khi viết validator script cho chính sách mới, **CẤM assert sự tồn tại của `OLD_STRING`** (vì nó chỉ chứng minh chưa ai sửa file). BẮT BUỘC phải assert sự tồn tại của `NEW_STRING` với `count == 1` duy nhất trên đĩa sau khi đã patch.
3. **Mọi giới hạn O(1) phải có Enforcement thật:** Nhãn "O(1)" không thể chỉ là văn bản mô tả. Bắt buộc gắn liền với lệnh kiểm tra cứng `git diff --numstat <= 30 dòng` ngay sau khi áp proposal của Sol.
