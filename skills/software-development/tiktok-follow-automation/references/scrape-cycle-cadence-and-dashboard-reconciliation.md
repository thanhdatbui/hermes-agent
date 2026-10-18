# Lệch Pha Chu Kỳ Scrape Web vs Ca Bot & Đối Soát Dashboard 1905

## 1. Bối Cảnh & Câu Hỏi Điển Hình Từ Operator
Khi Operator mở Dashboard :1905 vào sáng sớm (trước 07:00 AM), thường thấy hiện tượng:
- Dòng đối soát: `⚡ Tiến độ hôm nay: Bot +0 lượt (Web 📈 Tổng tăng: +6)`.
- Operator thắc mắc: *"Sao hôm qua web tăng mà bot không tăng? Tôi khóa không cho follow tự nhiên rồi mà nhỉ?"*.

## 2. Bản Chất: Lệch Pha Thời Gian Giữa Crawler Và Runner

### A. Chu kỳ cào dữ liệu Web toàn farm (`daily-tiktok-farm-tracker`)
- **Lịch chạy cố định:** **07:00 AM hàng ngày** (`0 7 * * *`).
- **Phạm vi:** Quét toàn bộ 1.200+ tài khoản trên toàn farm (cụm Kibe Máy 1-80 và cụm Admin Máy 201-280).
- **Lý do chỉ quét 1 lần/ngày:** Tiết kiệm băng thông proxy 4G và triệt tiêu nguy cơ bị TikTok rate-limit / cắm cờ checkpoint hàng loạt nick.

### B. Chu kỳ thực thi của Bot Follow (`follow_runner`)
- Bot chạy follow theo ca rải đều trong ngày:
  - **Ca 1 (Sáng):** 08:30 – 10:00 (Row 1, Row 7...)
  - **Ca 2 (Chiều):** 14:00 – 16:30 (Row 2, Row 8...)
  - **Ca 3 (Tối):** 19:30 – 21:30 (Row 3, Row 6...)
- **Hệ quả độ trễ đối soát (Reconciliation Latency):**
  - Mọi lượt bot bấm follow trong các ca Chiều và Tối của ngày $D$ (ví dụ: 18 lượt bấm lúc 14:03 và 15:51 ngày 17/10) diễn ra **SAU** đợt quét 07:00 AM của ngày $D$.
  - Do đó, 18 lượt follow này **bắt buộc phải đợi đến đợt quét 07:00 AM của ngày $D+1$** (18/10) mới được crawler cào về snapshot và ghi nhận chính thức lên Web.

## 3. Cơ Chế Snapshot Cache & Delta Forward-Fill Trên Dashboard

### A. Cạm bẫy Snapshot đêm (Partial Night Scan)
- Trong khung giờ đêm và rạng sáng (00:00 – 05:30), các tác vụ nền chuyên biệt (ví dụ: bật 2FA, upload avatar, nuôi dưỡng phục hồi) có thể quét lắt nhắt một nhóm nhỏ tài khoản (ví dụ: 112 nick lúc 05:00 AM).
- Khi đó, trong bảng `snapshots`:
  - `MAX(timestamp)` nhảy sang ngày mới ($D+1$).
  - Có 112 nick mang timestamp ngày $D+1$.
  - Nhưng ~1.150 nick còn lại **vẫn giữ snapshot ngày $D$** (do chưa tới mốc 07:00 AM).

### B. Truy vấn SQL `LatestCurr` & Hiệu ứng kế thừa Delta
- Truy vấn lấy dữ liệu trên Dashboard sử dụng mệnh đề:
  ```sql
  LatestCurr AS (
      SELECT * FROM RankedAll
      WHERE rn = 1 AND timestamp >= date(?, '-2 days')
  )
  ```
- Với ~1.150 nick chưa quét ở ngày $D+1$:
  - Snapshot mới nhất của chúng trong vòng 2 ngày vẫn là snapshot của ngày $D$.
  - Khi tính `delta_following = current.following - prev.following`, hệ thống so sánh snapshot ngày $D$ với snapshot ngày $D-1$.
  - **Kết quả:** Con số tăng trưởng Web của ngày hôm qua (`+6`) tiếp tục được cộng dồn vào tổng delta và hiển thị ở dòng hôm nay cho đến khi đợt quét 07:00 AM hoàn tất!

## 4. Kỷ Luật Kiểm Tra O(1) Xác Nhận Khóa Follow Tự Nhiên
Khi nhận câu hỏi từ Operator về nghi vấn lọt follow tự nhiên, Coordinator BẮT BUỘC kiểm tra nhanh O(1) theo 2 bước:

1. **Kiểm tra CSDL bảng `session_action_stats`:**
   ```sql
   SELECT target_date, SUM(internal_follows), SUM(natural_follows)
   FROM session_action_stats
   GROUP BY target_date
   ORDER BY target_date DESC LIMIT 3;
   ```
   - Xác nhận `natural_follows = 0`. Nếu bằng 0, khẳng định ngay lập tức khóa tự nhiên hoạt động chuẩn 100%.

2. **Truy vết 6 nick tăng following trên Web:**
   - So sánh snapshot giữa 2 ngày quét gần nhất để tìm chính xác danh sách nick có `delta_following > 0`.
   - Đối soát danh sách này với lịch sử bot chạy nội bộ của ngày hôm trước để chứng minh toàn bộ các lượt tăng đều là nick nội bộ của farm.
   - Giải thích ngắn gọn cơ chế lệch pha mốc 07:00 AM cho Operator.
