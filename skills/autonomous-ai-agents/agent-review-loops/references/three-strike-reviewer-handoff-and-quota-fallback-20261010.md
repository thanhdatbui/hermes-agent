# 3-Strike Reviewer Hand-off & Mid-Session Protocol (Updated 2026-10-10)

## 1. Bối cảnh & Hiện tượng Ping-Pong Review Loop
Khi Coordinator và Reviewer (Claude Code CLI / Sol High) chia vai cứng:
- **Coordinator/Worker:** Thợ code, có tâm lý "action bias" và quán tính sửa nốt ("chắc chỉ còn 1 lỗi nhỏ này").
- **Reviewer:** Luôn ở thế adversarial (tìm mọi kẽ hở từ string matching -> regex boundary -> process liveness).
Càng sửa các lỗi hiển hiện thì Reviewer càng soi sâu xuống các tầng thấp hơn, dễ dẫn tới việc Coordinator tiếp tục sửa mò vòng 4, 5, 6... gây lãng phí thời gian và token.

User đã thiết lập quy chuẩn bất biến:
> *"3 vòng k xong thì phải chuyển giao cho claude làm chứ, ủa t thiết kế v r mà alo?"*

## 2. Quy chuẩn 3-Strike Reviewer Hand-off
Quy tắc 3-Strike áp dụng cho **CẢ Closeout Gate LẪN Mid-Session Code Review**:

- **Strike 1 & Strike 2 (Standard Remediation):**
  Coordinator / Worker tiếp nhận finding của Reviewer, phân tích nguyên nhân gốc, sửa code/test trong phạm vi allowlist, chạy focused test < 30s, và gửi lại Reviewer chấm điểm.
- **Strike 3 (Reviewer Hand-off Trigger):**
  Khi cùng một candidate scope bị từ chối 3 lần liên tiếp:
  - **Mọi verdict không phải APPROVED/PASS rõ ràng đều tính là STRIKE** (bao gồm cả REJECT và UNRESOLVED do thiếu evidence).
  - **CẤM TUYỆT ĐỐI Coordinator tiếp tục đoán mò hoặc tự sửa ở vòng 4.**
  - **BẮT BUỘC DỪNG TỰ SỬA và CHUYỂN GIAO BÀN PHÍM cho chính Reviewer (Claude Code CLI):**
    ```bash
    claude -p "<task spec + finding history + exact allowlist>" \
      --dangerously-skip-permissions \
      --model sonnet
    ```
  - **Scope Lock bất biến:** Reviewer chỉ được sửa các file trong candidate scope đã định, cấm sửa lan man ra ngoài.
  - Reviewer tự đọc file, tự sửa theo tiêu chuẩn khắt khe của mình, tự chạy test, và tự nghiệm thu dứt điểm.

## 3. Van an toàn Quota Fallback (Claude Quota Protection)
Khi Claude Code CLI được giao bàn phím ở Strike 3 nhưng:
- Chạm ngưỡng **85% quota 5h** (theo skill `claude-limit-protection`), HOẶC
- Dính rate-limit, lockout, hoặc provider unavailable:
**CẤM ĐÓNG BĂNG TASK.** Bắt buộc kích hoạt Fallback ngay:
1. **Fallback 1 (Emergency Surgery L2):** Coordinator tự sửa nếu và chỉ nếu thỏa mãn đúng ngân sách O(1) (<= 2 files, <= 30 dòng diff, 1 focused test < 30s).
2. **Fallback 2 (Sol High :20129):** Điều phối sang Sol High vá thẳng theo Invariant "cấm Gemini mò 3 vòng, cấm BLOCKED bỏ dở".

## 4. Cơ chế Cưỡng chế Vật lý (Hard Guard Enforcement)
Để chống hiện tượng "quên luật" do prompt dilution hoặc cognitive overload:
- Hệ thống đếm streak độc lập trong sổ cái tamper-evident (`gate_audit.jsonl`).
- Tại Pre-tool Hook, khi phát hiện `reject_streak >= 3`:
  - Chặn đứng mọi lệnh dispatch review vòng 4.
  - Chuyển trạng thái session sang `HANDOFF_REQUIRED`.
  - Tự động spawn Claude Code CLI với `--dangerously-skip-permissions` để trao quyền trực tiếp.
