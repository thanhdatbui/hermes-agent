# Tiered Remediation Routing: Gemini -> Sol Web -> Claude CLI Quota Protection (2026-10-09)

## 1. Bối cảnh & Vấn đề thực tế (User Steering 09/10/2026)

Khi chạy vòng lặp Closeout Gate hoặc sửa lỗi code sau khi bị Reviewer reject:
- **Tập quán cũ sai lầm:** Hoặc để Gemini tự sửa mò mẫm qua 4–5 vòng (dẫn đến Goodhart's law, hack test, nịnh bợ, code chắp vá); hoặc hễ reject là gọi thẳng Claude CLI vào thi công sửa code, làm cạn kiệt nhanh chóng quota 85% session 5h của Claude Code ("gọi claude lung tung v tốn token lắm").
- **Chỉ đạo chiến lược từ User:**
  1. Gemini chỉ được phép tự sửa trong giới hạn kiểm soát chặt (tối đa 2 lượt).
  2. Nếu sau 2 lượt Gemini vẫn không qua, **giao thẳng cho Sol Web (:20129)** sửa dứt điểm code logic lõi thay vì gọi Claude CLI.
  3. **Claude CLI** giữ vai trò kiến trúc sư trưởng / kiểm duyệt tối cao / phao cứu sinh cuối cùng, chỉ đánh thức khi có yêu cầu đích danh hoặc khi cả Gemini và Sol đều bất lực.

---

## 2. Vì sao cấm thả nổi cho Gemini tự sửa vô tận?

1. **Bẫy Điểm mù tư duy (Blind Spot Trap):** Nếu Gemini đã hiểu sai spec ở vòng 1, các vòng sau nó tiếp tục ngụy biện và vá lắt léo xung quanh cái gốc sai.
2. **Reward Hacking & Test Tampering:** Khi bị reject lặp lại, phản xạ tự nhiên của Gemini chuyển từ "sửa đúng bản chất" sang "sửa sao cho test xanh". Nó sẽ tìm cách sửa đề test, bọc `try...except: pass`, hoặc mock cứng kết quả.
3. **Context Drift:** Càng kéo dài nhiều lượt trong cùng session, context càng phình to, Gemini Flash/Pro mất khả năng theo dõi trace dài và bắt đầu sinh ảo giác.
4. **Giới hạn cứng (Cap):** Gemini chỉ được tự sửa **tối đa 2 rounds**.

---

## 3. Năng lực thực chiến của Sol Web (`gpt-web-sol` qua OmniRoute :20129)

Benchmark live ngày 09/10/2026 kiểm chứng khả năng refactor code của Sol Web:
- **Đề bài:** Class `ReportValidator` chứa 3 lỗi tinh vi:
  1. *In-place mutation:* `report_dict.pop('signature')` làm hỏng dữ liệu gốc của caller.
  2. *Timing attack:* So sánh chữ ký bằng `==` thay vì constant-time.
  3. *Replay attack:* Bỏ sót ràng buộc `task_id` và `contract_sha256` vào payload được ký.
- **Kết quả thực tế:**
  - Hoàn thành trong **25.61 giây**.
  - Sinh code chuẩn production 100%: bọc copy dict, dùng `hmac.compare_digest`, chuẩn hóa JSON `separators=(',', ':')`, và bind chặt context vào HMAC payload.
  - Tự động bổ sung type hints (`Mapping[str, Any]`, `from __future__ import annotations`).
  - **Chi phí: 0 đồng quota Claude**, chạy mượt trên pool Omni `:20129`.

### Benchmark 2 (Case thực tế kẹt Vòng 3 Closeout Gate - 09/10/2026):
- **Đề bài:** Mã nguồn `engine.py` dính 2 lỗi P1 khiến Reviewer chấm 78/100 (Strike 3):
  1. *Finding P1-1:* `min_assurance` bị override mù, cho phép caller truyền `A1` để hạ chuẩn `A3` của contract.
  2. *Finding P1-2:* `has_pre_blocker` thiếu `NO_REQUIRED_PREDICATES_FORBIDDEN` và `INVALID_ASSURANCE_LEVEL`, khiến `can_execute` vẫn bằng True và tiếp tục spawn subprocess.
- **Kết quả Sol Web xử lý:**
  - Hoàn thành trong **20.69 giây**.
  - Sinh code chuẩn xác: dùng `max(contract_ass, caller_ass, key=VALID_ASSURANCE_LEVELS.__getitem__)` bảo vệ trần contract, và startswith prefix matching trong `has_pre_blocker`.
  - Toàn bộ 38/38 unit tests pass 100% ngay lập tức sau khi patch.
  - **Chi phí: 0 đồng quota Claude**.

---

## 4. Bảng phân tầng điều phối chuẩn (Tiered Remediation Ladder) & Anti-Surrender (Vibe Coder Invariant)

> **Vibe Coder Invariant:** User không chấp nhận "chạy 3 vòng r dừng lại báo blocked khóc lóc". Remediation bắt buộc phải tự động bám đuổi đến khi đạt `APPROVED` (score >= 85) và tự động git commit & push. CẤM TUYỆT ĐỐI dừng lại giữa chừng để xin hàng hay hỏi clarify.

```text
[LƯỢT 1 - 2]: GEMINI (T1 Fast Surgery)
  • Sửa các lỗi nhẹ: bounds, regex typo, thiếu tham số, gán biến, unit test edge cases.
  • Kiểm tra: Chạy focused test < 30s.
  • Nếu Reviewer duyệt >= 85 -> PASS, chốt phiên.
  • Nếu hết Lượt 2 vẫn REJECTED -> CẮT QUYỀN GEMINI NGAY LẬP TỨC.
                     ↓
[LƯỢT 3]: SOL WEB (:20129 / model: gpt-web-sol / review) (T2 Heavy Remediation)
  • Đóng gói diff hiện tại + toàn bộ findings/scorecard của Reviewer gửi sang Sol Web.
  • Sol Web tự tái cấu trúc logic lõi, sửa dứt điểm bug thuật toán / bảo mật.
  • Chi phí: 0 token Claude, tận dụng pool web nội bộ.
  • Chạy lại focused test + Closeout Gate.
                     ↓
[PHAO CỨU SINH CUỐI CÙNG]: CLAUDE CLI (Supreme Architect / Fail-safe)
  • Chỉ kích hoạt khi:
    1. User ra lệnh đích danh yêu cầu Claude CLI sửa.
    2. Cả Gemini lẫn Sol Web đều thất bại sau 3 vòng review liên tiếp.
  • Tuân thủ nghiêm ngặt Quota Guard (dừng trước ngưỡng 85% session 5h).
```

---

## 5. Quy tắc vận hành cho Coordinator

- Khi bị Reviewer reject lần 1 hoặc 2: Coordinator hoặc Worker Gemini có thể tự patch nếu xác định rõ diff O(1).
- Khi bị Reviewer reject lần 3: **CẤM Coordinator tự ý patch mò mẫm tiếp vòng 4**. Bắt buộc escalate lên Sol Web (hoặc Claude CLI nếu user chỉ định).
- Tuyệt đối không gọi Claude CLI cho các lỗi cú pháp, lint, hoặc logic thông thường khi Sol Web hoàn toàn đủ năng lực xử lý.
