# Dynamic Healing Row Selection (Cơ chế Chọn Row Dưỡng Sinh Động)

## 1. Vấn đề của Lịch Chọn Tĩnh (Static Hardcoding)
- Trước đây: Ca tối Ngày 3 và 3 ca Ngày 4 gán cứng luân phiên `healing_row` giữa Row 3, 4, 5, 6.
- Bị lỗi **kẹp ca liên tiếp** (Row 3 chạy tối 20h, sáng 6h lại chạy tiếp Row 3).
- Bị **mù dữ liệu**: Bỏ rơi Row 2 dù Row 2 vừa bị nhả follow nhiều hôm trước và đang cần được cứu.

## 2. Nguyên tắc Tính Điểm Động (Dynamic Scoring)
1. **Luật Chống Kẹp Ca (Anti-Consecutive Invariant):**
   - Loại trừ `last_row` vừa chạy ở ca trước: $R \in \{1..8\} \setminus \{\text{last\_row}\}$.
2. **Thứ tự Ưu tiên:**
   - **P0 (Khẩn cấp nhất — Trọng số 50):** Tỷ lệ nick trong Row bị nhả follow (`FOLLOW_FAILED` / circuit breaker). Cần đi dưỡng sinh `0 follow` để rửa cờ phạt.
   - **P1 (Chống bỏ đói — Trọng số 1.0):** Số giờ kể từ lần cuối Row đó được nuôi (`hours_ago`).
   - **P2 (Nhóm non — Trọng số 10):** Tỷ lệ nick chưa đủ 10 video cần tích lũy.
3. **Fail-safe Fallback:**
   - Nếu lỗi đọc DB/runtime, fallback về danh sách tĩnh `[3, 4, 5, 2, 6, 1, 7, 8]` sau khi đã lọc bỏ `last_row`.
