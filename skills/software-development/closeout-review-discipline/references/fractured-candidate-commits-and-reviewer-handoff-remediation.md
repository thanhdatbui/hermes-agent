# Fractured Candidate Commits & Reviewer Handoff Remediation

## Context & The 15/10/2026 Incident

Trong phiên xử lý lỗi watchdog và chốt phiên:
1. **Bẫy Fractured Commits (`HEAD~1` Trap):**
   - Khi trải qua nhiều vòng sửa đổi và thử nghiệm, repo đẻ ra một chuỗi commit vụn vặt (`HEAD~3`, `HEAD~2`, `HEAD~1`).
   - Khi chạy `closeout_gate.py --base HEAD~1`, gate chỉ trích xuất diff của duy nhất 1 commit trên cùng (chỉ gồm 1-2 test cases hoặc 1 dòng log).
   - Reviewer (Sol High / OmniRoute :20129) chấm điểm trượt thảm hại (38-52/100) với phản hồi:
     *"Diff chỉ chứa file test / cosmetic reformatting, không có production code diff — thiếu sót nghiêm trọng"*.
   - Mặc dù bản sửa lỗi chính nằm ngay ở commit phía dưới, reviewer hoàn toàn không thấy được bức tranh tổng thể vì diff bị chia cắt.
   - **Quy tắc bắt buộc**: Trước khi chạy `closeout_gate.py`, PHẢI squash toàn bộ các commit sửa đổi của phiên về đúng 1 commit candidate duy nhất trên đỉnh `origin/master` (`git reset --soft origin/master && git commit ...`) hoặc chỉ định `--base origin/master` với working tree sạch.

2. **Cơ chế Strike 3 / 4 Consecutive Rejections (Reviewer Handoff):**
   - Khi cổng Closeout Gate đạt 4 lần từ chối liên tiếp trên cùng `scope_hash`, trigger kích hoạt:
     `[REVIEWER_HANDOFF_TRIGGERED: 4 consecutive rejections reached for scope_hash=...]`
   - **Kỷ luật:** CẢ Coordinator, Worker VÀ Sol Repair ĐỀU PHẢI DỪNG LẠI. Không tiếp tục đoán mò hay dispatch lung tung.
   - Bàn giao quyền tự sửa (self-remediate) cho Claude Code CLI (`claude -p "..." --allowedTools "Bash,GlobTool,GrepTool,FileEditTool"`), khoanh vùng đúng danh sách file được phép sửa.
   - **Lưu ý Quota Gate:** Nếu Claude CLI bị chặn bởi cơ chế kiểm soát quota do cache cũ (`stale_quota` > 2h), cần làm mới cache quota hoặc truyền file quota hợp lệ qua biến môi trường trước khi chạy.
