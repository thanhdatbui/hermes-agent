# Quy Tắc Phân Loại Badge TikTok Farm Dashboard (Đề Xuất vs Tiềm Năng)

## 1. Bản Chất & Phân Định Hai Trạng Thái
Trên Dashboard TikTok Farm (`tiktok_dashboard.py`), các badge tăng trưởng phản ánh hai giai đoạn khác nhau trong vòng đời tài khoản:
- **`🔥 ĐỀ XUẤT` (Trending / Viral / Big Account)**:
  * Kênh đang bùng nổ tương tác mạnh trong ngày: $\Delta Follower \ge 20$ HOẶC $\Delta Tim \ge 50$.
  * Kênh cứng đã đạt quy mô lớn: $Follower \ge 1.000$ (kênh đủ điều kiện bật nhiều tính năng).
- **`🚀 TIỀM NĂNG` (High Engagement / Budding Potential)**:
  * Kênh "mầm non" mới nhú nhưng video có sức hút giữ chân người xem: $Tim \ge 50$ và $Follower \le 30$.
  * Tín hiệu tăng trưởng ban đầu: $\Delta Tim \ge 30$ nhưng chưa chạm ngưỡng bùng nổ của Đề Xuất.

## 2. Pitfall Nghiêm Ngặt: Overlap Điều Kiện Dẫn Tới 1 Nick Gán Cả 2 Badge
- **Lỗi thực tế**:
  ```python
  is_trending = (delta_f >= 20) or (delta_h >= 50) or (f_val >= 1000 and is_live)
  is_potential = (h_val >= 50 and f_val <= 30) or (delta_h >= 30)
  ```
  Khi một nick có $\Delta Tim \ge 50$, nó tự động thỏa mãn cả $\ge 30$, dẫn tới cả `is_trending` và `is_potential` đều bằng `True`. Giao diện render đồng thời `${trendBadge}${potentialBadge}` khiến user bức xúc vì 1 nick vừa được coi là "tiềm năng" vừa là "đề xuất".
- **Chuẩn Nghiệp Vụ Bắt Buộc (Mutual Exclusivity)**:
  Nick đã đạt chuẩn `🔥 ĐỀ XUẤT` thì TUYỆT ĐỐI KHÔNG ĐƯỢC coi là `🚀 TIỀM NĂNG`.
  ```python
  is_potential = not is_trending and ((h_val >= 50 and f_val <= 30) or (delta_h >= 30))
  ```
- **Nguyên tắc UI**: Một dòng tài khoản chỉ được hiển thị tối đa 1 nhãn tăng trưởng chính để giữ giao diện trực quan, rõ ràng cho người điều hành farm.
