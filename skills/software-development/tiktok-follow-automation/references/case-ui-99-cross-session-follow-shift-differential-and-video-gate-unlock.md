# Case UI-99: Chênh Lệch Danh Sách Nhả Follow Giữa Phiên 1 & Phiên 2 Trong Cùng Ca (Cross-Session Shift Differential & Video Gate Unlock)

## 1. Hiện Tượng & Nghi Vấn Nghiệp Vụ (06/10/2026)
Trong cùng một ca chạy của một hàng nick (Row 6) gồm 2 phiên (Phiên 1 lúc 18h và Phiên 2 lúc 20h):
- Phiên 1 báo danh sách nhả follow gồm 10 máy: `M3, M23, M25, M35, M53, M55, M61, M65, M69, M76`.
- Phiên 2 báo danh sách nhả follow gồm 9 máy hoàn toàn khác: `M5, M17, M40, M44, M46, M58, M62, M70, M78`.
- Người vận hành đặt câu hỏi: *Tại sao cùng 1 ca chạy của 1 row, ở phiên 1 list máy nhả follow liền lại khác phiên 2? Nếu phiên 1 đã nhả thì ai cho phép phiên 2 chạy khi đã bị phạt cooldown?*

### Sai Lầm Điều Phối (Coordinator Pitfall):
- **Ngụy biện dưỡng sinh:** Tự suy diễn "dưỡng sinh đổi lịch giữa phiên 1 và phiên 2" hoặc "mỗi phiên có danh sách dưỡng sinh riêng".
- **Sự thật Invariant:** Dưỡng sinh (`organic-rest-day`) được tính băm cố định theo NGÀY (`hashlib.md5(f"{date_str}:{machine}:{row}").hexdigest() % 3 == 0`). Cả 2 phiên trong cùng một ca/ngày BẮT BUỘC có danh sách máy dưỡng sinh y hệt nhau (24 máy cố định).

---

## 2. Nguyên Nhân Kỹ Thuật Thực Tế (Root Causes)

Cơ chế chạy follow chéo liên phiên hoạt động dựa trên 2 tầng cổng tương tác:

### A. Tầng 1: Cooldown Suppression (Khóa máy đã nhả ở Phiên 1)
- Ở **Phiên 1**: 10 máy (`M3, M23, M25...`) có $\ge 6$ video nên đủ điều kiện chạy follow. Khi gặp đợt siết nhả anchor của TikTok, chúng dính `FOLLOW_FAILED: anchor @... bị nhả sau vuốt — dừng session`.
- Ngay khi nhả, hệ thống Fail-Closed đẩy nick vào **Progressive Cooldown (phạt nghỉ 3 ngày)**, ghi án phạt vào `follow_state_<m>_row_<r>.json`.
- Ở **Phiên 2**: Khi đến hook follow, `_run_follow_hook` kiểm tra `_is_account_follow_cooldown()`. Thấy 10 máy này đang chịu phạt cooldown từ Phiên 1, hệ thống **khóa an toàn ngay lập tức (Safe Skip)**:
  `status: "skipped", reason: "follow-released-daily-cooldown"`
- **Hệ quả:** Do bị khóa cooldown, 10 máy này **hoàn toàn không được khởi động subprocess follow ở Phiên 2** $\rightarrow$ Chúng không thể bị nhả tiếp ở Phiên 2, và được gom vào danh sách `Bỏ qua: Khác`.

### B. Tầng 2: Video Gate Unlock Sau Khi Upload (Mở cổng máy mới ở Phiên 2)
- Ở **Phiên 1**: 8 máy (`M5, M17, M40, M44, M46, M58, M62, M70`) có số clip ban đầu trên kênh là **5 video**.
- Theo **Dual Gate an toàn (`video_count >= 6`)**, ở Phiên 1 các máy này bị chặn hoàn toàn:
  `status: "skipped", reason: "under-6-videos-follow-disabled"`
  $\rightarrow$ Ở Phiên 1 chúng chưa từng chạy follow, nên không thể bị nhả ở Phiên 1.
- **Bước ngoặt trong Phiên 1:** Module Đăng Video chạy và **upload thành công 1 video mới** lên kênh của các máy này (ví dụ `M5` upload thành công lúc 18:46).
- Tiến trình sync metadata cập nhật workbook: `video_count` của các nick này **nhảy từ 5 lên 6**!
- Ở **Phiên 2**: Khi vào kiểm tra Dual Gate, hệ thống thấy `video_count = 6` (đã đủ điều kiện an toàn) $\rightarrow$ **mở cổng cho phép chạy follow lần đầu tiên trong ngày**.
- Khi vừa vào chạy Mode 2, chúng gặp đợt siết nhả anchor $\rightarrow$ bị ghi nhận `FOLLOW_FAILED` (nhả liền 0 lượt) ở Phiên 2.

*(Riêng `M78`: ở Phiên 1 bị fail bước lướt Feed nên chưa tới hook follow; sang Phiên 2 lướt Feed thành công nên mới chạy follow và dính nhả).*

---

## 3. Quy Trình Điều Tra & Đối Soát O(1) Cho Coordinator

Khi nhận câu hỏi về sự khác biệt kết quả giữa Phiên 1 và Phiên 2 trong cùng một ca:
1. **Tuyệt đối không đoán mò về dưỡng sinh hay lịch chạy.** Dưỡng sinh là bất biến trong ngày.
2. **Kiểm tra nhóm máy nhả Phiên 1 ở Phiên 2:**
   - Mở `follow_result.json` của Phiên 2: xác nhận có `reason == "follow-released-daily-cooldown"` hay không. Nếu có $\rightarrow$ máy đã được bảo vệ đúng thiết kế.
3. **Kiểm tra nhóm máy nhả Phiên 2 ở Phiên 1:**
   - Mở `follow_result.json` của Phiên 1: kiểm tra có bị `reason == "under-6-videos-follow-disabled"` hay không.
   - Mở dòng đầu `log.jsonl` ở cả 2 phiên: so sánh `extra["video_count"]` (P1 là 5, P2 là 6).
   - Mở `upload_result.json` ở Phiên 1: xác nhận máy có `status == "success"` trong phiên đăng video vừa rồi không.
