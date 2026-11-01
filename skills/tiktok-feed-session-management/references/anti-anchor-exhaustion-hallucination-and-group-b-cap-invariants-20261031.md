# Khế ước Chống Ảo Giác Cạn Anchor, Cơ Chế Bỏ Qua Lỗi UI Hàng Con & Khóa Cứng Trần Quota Nhóm B (2026-10-31)

## 1. Bản Chất Ảo Giác "Hết Nick Trong Anchor" & Bác Bỏ Giả Thuyết Ngu Xuẩn
- **Sự cố thực tế:** Máy 12 (hoặc bất kỳ máy nào) đang follow trong danh sách của Anchor được một số lượt (vd: 11 lượt), sau đó script tự động kết thúc hoặc văng sang Mode 1 gõ search từng nick.
- **Bản chất sai lầm nghiêm trọng (Ảo giác của Coordinator / Script):** Tự suy diễn chủ quan là *"Anchor hết nick"* trong khi thực tế tài khoản Anchor của farm có hàng trăm Following/Followers nội bộ.
- **Nguyên nhân gốc rễ trong code (`mode2_follow_followers.py`):**
  - Khi follow một nick con trong danh sách của Anchor, nếu gặp phản hồi `outcome == "manual"` (điển hình: `MANUAL_REVIEW: verify row sau tap không xác định` do UI RecyclerView của TikTok giật/reload trễ khiến dump UI không tìm thấy đúng dòng vừa tap):
  - Code cũ dại dột kích hoạt:
    ```python
    else:  # manual
        res.status = "MANUAL_REVIEW"
        res.reason = reason or "..."
        failed = True
        break  # <--- BỊ ĐỤNG CHỖ NÀY: VĂNG KHỎI VÒNG LẶP CỦA ANCHOR!
    ```
  - **Hậu quả:** Chỉ vì 1 nick con bị lỗi nhận diện UI, script lập tức `break` đánh sập toàn bộ vòng lặp của Anchor, vứt bỏ toàn bộ hàng trăm nick con còn lại phía sau của Anchor đó. Sau đó, engine thấy Mode 2 bị lỗi UI nhưng nick không bị phạt nhả (`follow_failed = False`), liền kích hoạt chế độ `mode2_degraded = True` và đá máy sang Mode 1 gõ search từng nick bằng tay.
- **Quy tắc bất biến mới:**
  - Nếu chỉ là lỗi verify row không xác định trên 1 nick con đơn lẻ: BẮT BUỘC ghi log warning, ghi nhận `res.details['skipped_row_manual_reasons']` và gọi `continue` để cuộn/duyệt các nick con tiếp theo trong Anchor cho tới khi gom đủ quota.
  - CẤM TUYỆT ĐỐI `break` văng khỏi Anchor khi gặp lỗi UI cục bộ của 1 hàng con.

---

## 2. Điểm Nghẽn Timeout & Khập Khiễng Tốc Độ Giữa Mode 2 vs Mode 1
- **Tốc độ Mode 2 (Ăn theo Anchor):** 35 – 45s / 1 lượt follow. Chạy 20 lượt chỉ mất ~13 – 15 phút $\rightarrow$ Timeout 20 phút (1.200s) là ĐỦ.
- **Tốc độ Mode 1 (Gõ tìm kiếm thủ công từng UID):** 70 – 90s / 1 lượt follow (do phải vuốt feed, gõ search, ngâm video 15s, refresh 3.5s, delay giãn cách 8-25s).
- **Hệ quả kẹp thời gian:** Khi Mode 2 bị văng sớm (mới ăn 11 nick mất ~12 phút), thời gian còn lại của session chỉ còn 8 phút. Mode 1 chỉ kịp gõ thêm 5 nick là chạm Hard Deadline 20 phút và reserve 90s $\rightarrow$ Ép máy đóng phiên ở 16 lượt và nuốt mất thông tin search not-found trong báo cáo.
- **Quy tắc:** Bắt buộc tối ưu để máy ăn trọn quota ngay trong Mode 2 tại Anchor, tránh để rơi vào bẫy nghẽn deadline của Mode 1.

---

## 3. Khóa Cứng Trần Quota Nhóm B (Max Volume): Tối Đa 20 Lượt/Phiên & 40 Lượt/Ngày
- **Nguyên nhân lệch trần cũ:** Trong `follow_state.py`, nhóm Cohort Veteran có `core_cap = 40`. Sau nhiều ca chạy sạch, thuật toán tăng tiến $+2$ tự động đẩy `active_ceiling` của nick lên 25–30 lượt/phiên.
- **Quy tắc khóa cứng Nhóm B (Máy chẵn):**
  ```python
  effective_core_cap = min(core_cap, 20) if _safe_int(self.machine, 1) % 2 == 0 else core_cap
  cap = max(1, min(40, min(effective_core_cap, target_cap)))
  ```
- **Hạn mức chuẩn:**
  - **Trần phiên Nhóm B:** Kịch kim là **20 lượt / phiên**.
  - **Dải random ngẫu nhiên:** Thu hẹp chuẩn xác trong dải bám trần hẹp $[cap - 2, cap] = [\mathbf{18}, \mathbf{20}]$ lượt.
  - **Tổng trần ngày:** 2 phiên trong ngày cộng lại **tuyệt đối không vượt quá 40 lượt / ngày**.
