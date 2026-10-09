# Infinite Remediation Anti-Bloat and Luna Fallback Lessons (2026-10-05)

## 1. Nguyên nhân Sự cố Vòng lặp Vô tận (Infinite Remediation Loop)
Trong các phiên làm việc ngày 05/10/2026, xuất hiện tình trạng Closeout Gate chạy lặp đi lặp lại hàng chục lần (kéo dài 2-4 tiếng không thể chốt phiên) với cùng một kịch bản:
1. **Gemini cạn quota -> Fallback sang Luna (`gpt-5.6-luna`):** Khi primary model Gemini hết quota, hệ thống tự động fallback sang Luna. Luna có xu hướng lập trình phòng thủ cực đoan (defensive over-engineering): viết thêm nhiều lớp helper, TOCTOU locks, validator dư thừa và mock tests đồ sộ.
2. **Diff phình to vượt trần Sol Web (24 KB):** Diff candidate phình từ vài dòng lên >70 KB, đỉnh điểm lên 92 KB (+612 / -70 lines trong `closeout_gate.py`). Khi diff > 24.000 bytes, gate tự động kích hoạt fallback sang Terra Codex (`cx/gpt-5.6-terra-high`).
3. **Bẫy "No-cap remediation" (Cấm dừng khi < 85):** Quy tắc điều phối cấm dừng khi điểm < 85 khiến Coordinator liên tục nhận feedback của Terra, lập contract và dispatch Luna sửa tiếp. Luna lại nhồi thêm code, khiến diff phình to hơn và điểm review tiếp tục tụt (76 -> 71 -> 62 -> 57).
4. **Vác rác chéo phiên (Cross-session Dirty Bleed):** Phiên làm việc chỉ sửa file Excel/Hashtag hoặc hỏi đáp lý thuyết (không sửa code) nhưng khi user ra lệnh "chốt phiên", Coordinator lại quét thấy file dirty dở dang của repo `tools` từ phiên trước và vác đi chạy gate, biến phiên sửa Excel thành phiên kẹt gate code.

## 2. Các chốt chặn bắt buộc (Mandatory Invariants)

### Chốt chặn 1: Trần cứng Remediation (Max 2 Rounds Hard Cap) & Vibe Coder Invariant
- Tuyệt đối CẤM vòng lặp remediation không trần ("no-cap").
- **Vòng 1:** Chạy Closeout Gate. Nếu Reviewer < 85 -> Cho Worker sửa ĐÚNG 1 LẦN theo concrete in-scope findings (micro-diff <= 15 dòng).
- **Vòng 2:** Chạy lại Closeout Gate. Nếu VẪN < 85:
  - **Vibe Coder Invariant (User chỉ đạo trực tiếp 05/10/2026):** User là *vibe coder*, không biết và không muốn AI ném lỗi kỹ thuật hay hỏi xin phép/đùn việc bắt user debug. CẤM dừng lại khóc lóc BLOCKED hay hỏi xin phép.
  - **Hành động tự động của AI:** Tự động rollback các hunk bôi lan man về baseline sạch; áp dụng giải pháp tối giản nhất (minimalist fix O(1)). Nếu đã thử tối giản mà test logic thật vẫn chặn, ghi nhận đúng evidence vật lý vào audit log và chuyển sang task độc lập khác mà không spam hỏi user. CẤM tự ý chạy vòng thứ 3 làm phình diff.

### Chốt chặn 2: Pre-Review Diff Budget Fail-Fast (<= 24 KB / <= 150 lines)
- Trước khi gửi payload lên OmniRoute (:20129):
  - Kiểm tra `len(diff_bytes) <= 24_000` và `numstat <= 150` dòng.
  - Nếu vượt quá: Gate phải fail-fast ngay lập tức tại local (`exit 1`), thông báo: `[Gate Fail-Fast] Diff quá lớn (>24KB). Vi phạm quy chuẩn phân rã task Gate 1. Cần revert code thừa hoặc tách task trước khi review.`
  - Không để payload tràn sang Terra Codex vì diff lớn khiến reviewer trừ điểm kiến trúc nặng nề.

### Chốt chặn 3: Ranh giới Không sửa code -> `CLOSEOUT_NOT_APPLICABLE`
- Khi user ra lệnh "chốt phiên", Coordinator bắt buộc đối soát Task Change Ledger:
  - Nếu task chỉ sửa Excel (`.xlsx`), file data (`.db`), log, config không code, hoặc hỏi đáp tư vấn: Báo cáo hoàn tất ngay, đánh dấu `CLOSEOUT_NOT_APPLICABLE`, KHÔNG chạy `closeout_gate.py`.
  - CẤM TUYỆT ĐỐI vác các file dirty dở dang của repo khác (`tools`, `Hermes`...) đi review hộ.
