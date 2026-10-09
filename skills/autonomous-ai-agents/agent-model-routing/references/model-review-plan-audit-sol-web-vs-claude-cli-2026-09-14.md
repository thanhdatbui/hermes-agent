# Benchmark Review / Plan Audit vs Troubleshooting & Thiết Lập Model Review (14/09/2026)

## 1. Bối cảnh & Phát hiện then chốt

Trong các buổi đánh giá năng lực LLM cho Phone Farm Taadaa, cần phân định rạch ròi giữa 2 lớp bài test:
- **Lớp 1: Troubleshooting / Incident Problem Solving (Giải toán)**: Đưa log lỗi, diff bug, phân tích root cause, đề xuất giải pháp kỹ thuật.
- **Lớp 2: Review / Plan Audit Gate (Thẩm định kế hoạch)**: Đưa 1 bản Implementation Plan hoặc Patch Contract do Worker nộp. Model đóng vai trò Gác cổng (Gatekeeper) duyệt `APPROVED` hoặc bác `REJECT`, kiểm tra kỷ luật 5 Gates và Farm Invariants.

## 2. Kết quả đối đầu Claude CLI vs ChatGPT Web 5.6 Sol

### Lớp 1: Problem Solving (Phân tích lỗi farm)
- **Claude CLI (62/100 - Rớt vai Farm Architect)**: Nhìn code theo góc nhìn App Developer thông thường, dễ dính bẫy Invariant nặng (xem `pm clear com.zhiliaoapp.musically` là hợp lý để clean state, không hiểu việc xóa data làm chết hàng loạt nick TikTok nuôi).
- **Sol Web (88/100 - Pass Senior)**: Bảo vệ state và token nuôi nick rất vững, nhận diện được `pm clear` tạo 20x authentication pressure, phân tích lock per-device.
- **Triage sự cố 15 acc ban**: Claude CLI đạt 91/100 (tốc độ bắt smoking gun nạp nhầm session file cũ cực nhanh, action plan cụ thể từng lệnh grep/awk); Sol đạt 75/100 (phản biện tốt không sycophancy, nhưng thiếu phân tích pattern dãy số tuần tự).

### Lớp 2: Review / Plan Audit (Thẩm định Plan của Worker gài bẫy 5 Gates)
- **Claude CLI (96/100 — Top-tier Lead Gate Auditor)**: 
  - Kỷ luật thép, thẳng tay `VERDICT: REJECT`.
  - Bắt trọn 4/4 bẫy: Cấm quét đĩa O(N) `os.walk`, cấm tap mù `540 960`, đập tan bẫy overengineering 5 class Factory, ép anchor monolith phải có `grep count == 1` và focused test `<30s`.
  - Remediation cực kỳ cụ thể: chỉ định file test `pytest tests/... -x -q`, quy định 5 dòng context.
- **Sol Web (91/100 — Senior Architectural Auditor)**:
  - Bắt đúng bản chất "speculative architecture" và "test inflation".
  - Nhận diện tốt ranh giới trừu tượng (abstraction boundary), nhưng remediation mang tính quy trình vĩ mô hơn là lệnh bash cụ thể.

## 3. Đặc thù Quota & Cơ chế Failover của ChatGPT-Web trên OmniRoute (:20129)

- Provider `chatgpt-web` (`cgpt-web`) dùng session token từ cookie trình duyệt (`__Secure-next-auth.session-token`), không tính phí token/USD.
- Quota: Giới hạn theo sliding window ~30-50 messages / 3 giờ (với model Sol thinking cao). Khi chạm trần trả HTTP 429.
- Payload limit: Nếu prompt quá lớn sẽ dính HTTP 413. Cần gửi focused diff $\le 300$ dòng thay vì paste monolith nguyên file.
- **Cơ chế Failover pool 5 acc**: Máy trạm có 5 tài khoản Web active. OmniRoute tự động xoay account khi gặp 429, tạo dung lượng thực tế ~150-200 lượt review/ngày.

## 4. Cấu hình Chuỗi Combo `review` trên OmniRoute (:20129) (Đã chốt 14/09/2026)

Sol Web khôn hơn Terra Codex rõ rệt ở tầng reasoning và bảo vệ Invariant farm. Do đó Sol Web được đặt ở **Tier 0** làm Reviewer chính. Đồng thời **loại bỏ hoàn toàn Gemini Pool** khỏi chuỗi review do thiếu tư duy phản biện:

1. **Tier 0 (Chốt chặn chính):** `chatgpt-web/gpt-5.6-sol-high` (ChatGPT-Web pool 5 acc)
2. **Tier 1:** `gpt-5.6-terra-high` (Codex Farm pool)
3. **Tier 2:** `ag-opus-pool` (Claude Opus 4.6 Thinking trên pool 78 acc)
4. **Tier 3:** `oc/nemotron-3.5-lightning-free` (Opencode)
5. **Tier 4:** `openrouter/nvidia/nemotron-3-super-120b-a12b:free` (NVIDIA 120B)
6. **Tier 5:** `oc/muse-spark-1.3-contributor-free`
7. **Tier 6:** `oc/muse-spark-1.2-contributor-free`
*(Đã gỡ sạch `ag-gemini-pool-3`)*
