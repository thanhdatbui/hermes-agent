---
name: farm-anti-overengineering
description: Kỷ luật thực thi chống over-engineering và cấm viết lại script canonical trên Taadaa Farm.
---

# Farm Anti-Overengineering Discipline

## 1. Nguyên Tắc Cốt Lõi (Invariants)
- **Cấm viết lại script Canonical:** Luôn tái sử dụng các công cụ chuẩn (`inspect_machine.py`, `admin_ssh.py`, `run_avatar_batch_3accs.py`, `do_logout_account.py`, `tiktok_login_v1.py`). Cấm đẻ script ad-hoc.
- **Tiêu chuẩn Gate chuẩn O(1) & Chống Bureaucratic Theater:**
  - Gate chỉ đo sự kiện quá trình thật sự (`tool_called == "browser_vision"`), tuyệt đối không dùng proxy nội dung (text OCR để đoán pixel ảnh).
  - Một predicate duy nhất (~15 dòng code), fail-closed với đúng 1 lệnh hành động duy nhất, cấm thông điệp mắng mỏ gây vòng lặp khóc lóc / tê liệt.
  - Tách rời 100% Phiên Vận Hành (không có code delta) khỏi Closeout Code Review: tự động PASS trong < 0.2s, cấm quét commit cũ, cấm gọi Sol Repair sửa code ma.
- **Budget điều phối Worker:**
  - Tối đa 1 file code, diff <= 30 dòng, 1 focused test < 30s.
  - Ngân sách <= 15 calls. Nếu trong 3 turn đầu không tìm thấy anchor rõ ràng -> BẮT BUỘC ABORT, không đốt budget mò mẫm.
  - Không tự ý mở rộng Scope: Khi gặp lỗi kẹt, chỉ giải quyết đúng blocker tại chỗ; không tự chế thêm wrapper, không tự refactor kiến trúc khi chưa có yêu cầu.

## 2. Thang Leo Thang Khi Kẹt (Escalation Ladder)
- **L0:** Retry TRANSIENT (mạng, timeout, rớt kết nối) tối đa 2 lần.
- **L1:** Re-dispatch Worker với scope chia nhỏ và Patch Contract O(1).
- **L2 (Emergency Surgery):** Coordinator tự sửa tối đa 1 file <= 30 dòng kèm 1 test focused < 30s khi đủ điều kiện.
- **L3 (BLOCKED):** Đánh dấu BLOCKED kèm bằng chứng thực tế (log/OCR/diff), chuyển sang task độc lập khác.
- **L4 (Clarify):** Chỉ dùng khi cần quyết định nghiệp vụ, thiếu credentials hoặc thao tác tốn phí tiền thật.

## 3. Tài Liệu Tham Khảo (References)
- Kỷ Luật Thiết Kế Gate Chuẩn O(1) & Tách Rời Phiên Vận Hành Khỏi Closeout Review: [`references/o1-gate-discipline-and-closeout-operational-decoupling.md`](references/o1-gate-discipline-and-closeout-operational-decoupling.md)
- Toàn bộ hồ sơ quy tắc và case study lịch sử: [`references/historical-anti-overengineering-archive.md`](references/historical-anti-overengineering-archive.md)
- Bounded Review Loop: [`references/claude-cli-bounded-review-loop.md`](references/claude-cli-bounded-review-loop.md)
- Script Codification vs Memory: [`references/script-codification-vs-memory-hygiene-and-concise-reporting-20261002.md`](references/script-codification-vs-memory-hygiene-and-concise-reporting-20261002.md)
