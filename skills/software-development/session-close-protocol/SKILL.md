---
name: session-close-protocol
description: "Use when the user says 'chốt phiên', 'chốt', 'done', 'wrap up', asks whether the current deliverable is done, or requests closeout. Runs closeout_gate.py (Sol Web/OmniRoute :20129) scoped with --files; REJECTED/<85 enters a remediation loop (not BLOCKED) until APPROVED>=85 exit 0, then auto commit/push/verify remote SHA. Progress questions remain status-only."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [session-close, review, git, handoff, taadaa]
    related_skills: [taadaa-farm-ops-rules, verification-evidence, concurrent-workspace-safety]
---
# Session-close protocol

> **Canonical policy precedence:** Follow `D:\Taadaa\HERMES_SUBAGENT_RULES.md` marker `CANONICAL-POLICY-PRECEDENCE-2026-10-05`; this skill implements that policy and must not override it.

References:
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

## Kỷ luật bảo toàn logic người dùng (No-Regression Contract)
- **Tuyệt đối không đảo ngược yêu cầu tùy biến của User khi đóng phiên**:
  - Khi user yêu cầu một quy tắc logic cụ thể (ví dụ: *mật khẩu ChatGPT bắt buộc tạo theo mật khẩu Gmail, cấm hardcode*), Agent tuyệt đối KHÔNG được quay lại code cũ hay ghi đè lên các quy ước này trong quá trình commit/closeout.
  - Phải kiểm tra git diff (`git diff HEAD~N`) để đảm bảo logic user yêu cầu vẫn được bảo toàn nguyên vẹn trước khi push.
  - Fail-fast ngay nếu phát hiện thiếu tham số cấu hình tùy biến của user, tuyệt đối không dùng giá trị mặc định tùy tiện.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
