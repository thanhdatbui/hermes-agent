# Fail-Closed Semantic Fallback Invariant & Stale Proxy Readiness Fast Triage (Case UI-57)

## 1. Cạm bẫy Ép Trạng Thái `not_followed` trong Semantic Fallback (Regression Pitfall)
Khi bổ sung semantic fallback (quét text/desc `"Bạn bè"`, `"Friends"`, `"Nhắn tin"`, `"Message"`) để cứu các trường hợp `classify_button()` trả về `"unknown"`:
- **Anti-Pattern:**
  ```python
  if has_followed_btn and not has_follow_btn:
      return "followed"
  if has_follow_btn and not has_followed_btn:
      return "not_followed"  # <-- BẪY HỒI QUY NGHIÊM TRỌNG!
  ```
- **Hậu quả:**
  Khi profile đối phương hiển thị nút lạ/chưa rõ ràng (ví dụ: nút "Follow" đi kèm nhãn "Đang chờ duyệt", hoặc nút follow trong danh sách gợi ý tài khoản tương tự), `classify_button()` ban đầu trả về `"unknown"` để flow xử lý fail-closed an toàn (`MANUAL_REVIEW`). Nhưng nhánh `has_follow_btn` phía dưới ép trả về `"not_followed"`, khiến runner đánh giá nhầm là nick chưa follow, dẫn đến:
  1. Gãy unit test hồi quy `test_path_b_verify_duplicate_semantic_actions_are_manual` (assert `"unknown"` nhưng nhận `"not_followed"`).
  2. Gây dừng phiên nhầm với lỗi `FOLLOW_FAILED: TikTok không nhận follow sau reload`, đẩy nick vào cooldown oan uổng.
- **Quy tắc bất biến (Fail-Closed Invariant):**
  Semantic fallback CHỈ ĐƯỢC PHÉP xác nhận tích cực trạng thái `"followed"` khi có bằng chứng chắc chắn (`has_followed_btn and not has_follow_btn`). Mọi trường hợp còn lại (kể cả chỉ thấy `has_follow_btn`) BẮT BUỘC giữ nguyên kết quả gốc `return res` (`"unknown"`), để các tầng an toàn phía sau tiếp tục phán quyết fail-closed.

---

## 2. Stale Proxy Readiness Fast Triage (Pattern 3)
Khi chạy Canary mà runner dừng sớm ở tầng preflight với lỗi:
`BLOCKED: preflight device-lock/VPN fail-closed: proxy readiness timed out for <serial>`
- **Root Cause:**
  File `~/.codex/device-readiness/<hash>.json` kẹt trạng thái `state: "proxy_pending"` từ các phiên chạy hoặc reboot cũ nhiều ngày trước.
- **Xử lý O(1) ngay lập tức:**
  ```bash
  python -c "from automation_core.readiness import mark_proxy_state; mark_proxy_state('<serial>', 'proxy_ready')"
  ```
  Sau lệnh này, runner sẽ bỏ qua vòng lặp chờ 180s và vào thẳng phiên Canary thực chiến.
