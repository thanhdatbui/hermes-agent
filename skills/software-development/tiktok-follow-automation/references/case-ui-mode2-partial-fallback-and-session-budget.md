# Case UI: Mode 2 Anchor Partial Fallback to Mode 1 & Session Budget

## Vấn đề thực tế
Khi chạy follow TikTok theo Mode 2 (follow follower của anchor Tik1/Tik2):
- Mỗi phiên chọn ngẫu nhiên tối đa 3 anchor Tik1/Tik2, mỗi anchor cuộn tối đa 40 lần (sau 5 lần cuộn liên tiếp không thấy nick farm mới thì dừng anchor).
- Nếu cả 3 anchor đều hết nick farm mới hoặc dừng sớm, Mode 2 có thể chỉ follow được một phần quota (ví dụ 4, 7, 12 lượt) trong khi budget ngẫu nhiên của phiên là 15-20 lượt.
- Code cũ có bug logic: chỉ fallback sang Mode 1 khi `len(res.mode2_followed) == 0`. Dẫn đến khi Mode 2 follow được > 0 lượt nhưng chưa đủ budget phiên thì hệ thống ngắt phiên luôn, không gọi Mode 1 để bù phần còn thiếu.

## Nguyên tắc xử lý (Partial Fallback Contract)
1. **Budget ngẫu nhiên theo phiên:**
   - Budget mỗi phiên được roll ngẫu nhiên trong khoảng `[budget_per_session_min, budget_per_session_max]` (mặc định 10-20, trần ngày 40).
2. **Partial Fallback sang Mode 1:**
   - Khi Mode 2 kết thúc, nếu `not res.follow_failed` và `rem_budget = session_budget - len(res.followed) > 0`:
     - Tự động chuyển `mode = "both"` để kích hoạt Mode 1 (Search & Follow trực tiếp UID nội bộ từ `taikhoan_run_safe.xlsx`).
     - Ghi nhận `mode2_fallback_to_mode1 = True` và lý do fallback: `anchors_exhausted` (nếu Mode 2 = 0) hoặc `budget_unfilled` (nếu Mode 2 follow dở dang).
   - Mode 1 chỉ nhận quota còn lại (`rem_budget`), follow cho đến khi đủ target phiên thì dừng.
3. **Cấm fallback khi dính lỗi chặn (FOLLOW_FAILED):**
   - Nếu ở bất kỳ bước nào TikTok không nhận follow (profile không đổi trạng thái hoặc bị nhả follow): dừng ngay lập tức, ngắt toàn bộ phiên, cấm nhảy sang Mode 1 để tránh làm hỏng trust tài khoản.
