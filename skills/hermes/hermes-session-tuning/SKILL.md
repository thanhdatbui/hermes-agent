---
name: hermes-session-tuning
description: "Chẩn đoán Hermes session lag (context bloat → compression threshold), tinh chỉnh compression, và kiểm tra/ép reasoning_effort khi route qua 9router (deepseek v4)."
---
# Hermes Session Tuning (lag + reasoning qua 9router)

References:
- Inbound Image Triage & Session Reset Recovery Discipline (2026-11-02): xem `references/inbound-image-triage-and-session-reset-recovery-20261102.md`. CẤM chào mẫu rập khuôn khi user gửi ảnh chụp đoạn chat sau session reset; bắt buộc tra `session_search` bóc tách câu hỏi và trả lời từng điểm bằng bằng chứng code thực tế.
- Model Provider Failed & Context Bloat Triage: xem `references/model-provider-failed-after-retries-triage.md`. Triage nhanh 2 nguyên nhân cốt lõi gây "The model provider failed after retries": (1) Rớt mạng ISP/OmniRoute proxy pool 503, và (2) Bẫy Context Bloat Overload do tool xả payload megabytes (>1-2MB) khiến socket stream nghẽn 10-12 phút và lặp lại liên hoàn ở các turn tiếp theo.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
