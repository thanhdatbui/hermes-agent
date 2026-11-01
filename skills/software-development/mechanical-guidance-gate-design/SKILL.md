---
name: mechanical-guidance-gate-design
description: "Use when designing mechanical gates to prevent agent loops."
---
# Mechanical Guidance Gate Design (Anti-Whining & Action Mandate)

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
> - `references/cowboy-patch-interceptor-and-anti-memory-fallacy-20261101.md`: Chốt chặn cơ học PreTool intercept trên patch/write_file thay thế lời hứa kỷ luật suông của LLM; bắt buộc chặn đứng Coordinator tự ý sửa code trực tiếp ngoài unified_patch_pipeline để triệt hạ lỗi thiếu import/cú pháp.
> - `references/gate2-monolith-scope-window-and-anchor-text-invariants-20261031.md`: Chuẩn hóa Gate 2 Monolith theo Claude CLI: cơ chế Scope Window 2 tầng (--anchor symbol + --anchor-text dòng duy nhất), phá vỡ bẫy span_len > 150 dòng cho các hàm điều phối lớn (150-600 dòng); bắt buộc gắn EXACT_ANCHOR_TEXT sau skill injection để prompt không bị ghi đè.
> - `references/mechanical-precheck-gate-for-code-reuse.md`: Cơ chế cơ giới hoá S0 Precheck ép tự động đối soát logic và tiêm context vào Planner để chống chế lại bánh xe.
> - `references/os-state-invariants-vs-heuristic-regex-gate-theater-20261030.md`: Phân biệt OS-level state invariants (git diff, exit code, blacklist) vs regex gate theater; chuẩn hóa Action Card và cơ chế Advisor.
> - `references/autonomous-farm-mailbox-harvesting-and-meta-auth-traps-20261031.md`: Chống bại liệt xin xỏ khi farm có sẵn 800+ mail, cơ giới hóa tự động đọc OTP qua Microsoft Graph API O(1) và kỹ thuật đối soát antifraud Meta/Muse AI.
> - `references/mechanical-remediation-vs-discipline-promises-and-stale-carryover-20261031.md`: CẤM văn mẫu kỷ luật suông; chuyển hóa mọi sự cố thành vá cơ học (code patch O(1) + test chống hồi quy); triệt tiêu lỗi Dashboard Stale Carryover Delta đầu ngày mới.
> - `references/serial-to-machine-o1-lookup-and-contextual-guidance-anti-loop-20261031.md`: Triệt tiêu vòng lặp Agent loay hoay: cấm placeholder vô nghĩa <N>, tự động phân giải serial qua farm_db.get_machine_by_serial, loại bỏ guidance lệch ngữ cảnh (cấm xúi inspect_machine khi tìm code), và auto-rewire lệnh đọc ADB an toàn.
> - `references/scoped-transaction-pipeline-and-anti-paralysis-architecture-20261031.md`: Kiến trúc Scoped Transaction triệt tiêu Over-Engineering và Bại liệt hệ thống: loại bỏ bẫy snapshot 500 file untracked/rác tại S0, cách ly receipt logs ra khỏi Git tree, tầng thi công trực tiếp O(1) qua apply_patch, miễn trừ Canary ép buộc cho repo tooling, và Smart Machine Guidance trong Guard Bulkhead.
> - `references/mechanical-interceptor-vs-prompt-gate-theater-20261031.md`: Chốt chặn cơ học Mechanical Interceptor thay thế Prompt-based Gate Theater: bài học Coordinator tự suy diễn làm tay gây sự cố mạng/proxy; tích hợp sàn timeout worker >= 300s và chốt chặn ép buộc

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
