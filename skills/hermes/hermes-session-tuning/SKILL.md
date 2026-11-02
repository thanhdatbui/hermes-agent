---
name: hermes-session-tuning
description: "Chẩn đoán Hermes session lag (context bloat → compression threshold), tinh chỉnh compression, và kiểm tra/ép reasoning_effort khi route qua 9router (deepseek v4)."
---
# Hermes Session Tuning (lag + reasoning qua 9router)

References:
- Quoted Repetition Disambiguation & Session Compaction Parroting Trap (2026-11-02): xem `references/quoted-repetition-disambiguation-and-compaction-parroting-trap-20261102.md`. Triage nhanh khi user gửi `?` hoặc tin nhắn cực ngắn trích dẫn lại phát ngôn của agent; đây là tín hiệu chất vấn/bắt lỗi lạc đề, cấm nhầm lẫn thành yêu cầu giải thích tiếp hoặc lặp lại báo cáo cũ (parroting loop).
- Inbound Image Triage & Session Reset Recovery Discipline (2026-11-02): xem `references/inbound-image-triage-and-session-reset-recovery-20261102.md`. CẤM chào mẫu rập khuôn khi user gửi ảnh chụp đoạn chat sau session reset; bắt buộc tra `session_search` bóc tách câu hỏi và trả lời từng điểm bằng bằng chứng code thực tế.
- Model Provider Failed & Context Bloat Triage: xem `references/model-provider-failed-after-retries-triage.md`. Triage nhanh 2 nguyên nhân cốt lõi gây "The model provider failed after retries": (1) Rớt mạng ISP/OmniRoute proxy pool 503, và (2) Bẫy Context Bloat Overload do tool xả payload megabytes (>1-2MB) khiến socket stream nghẽn 10-12 phút và lặp lại liên hoàn ở các turn tiếp theo.
- Single-Message Session Provider Failure & Farm Isolation (2026-11-02): xem `references/single-message-session-provider-failure-and-farm-isolation-20261102.md`. Triage lỗi session mới tinh chỉ gửi 1 tin nhắn nhưng văng lỗi provider retry do upstream Antigravity HTTP 400 và `resume_pending_expired`; nguyên tắc bảo toàn 100% cấu hình riêng (`config.yaml`, `cron`, `memories`) và cách ly hoàn toàn với vận hành Farm Android.
- Tra cứu session bị lạc sau restart/sự cố: Dùng `session_search` rà soát theo keywords/topics hoặc đọc transcript Claude CLI `.claude/projects/` để khôi phục đúng ngữ cảnh session dở dang.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
