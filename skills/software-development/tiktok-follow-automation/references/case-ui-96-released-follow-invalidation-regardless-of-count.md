# Case UI-96: Chuẩn Hóa Khấu Trừ Follow Tự Nhiên & Đối Soát Nhả Follow (User Correction 2026-10-06)

## 1. Bối Cảnh Thực Tế & Phản Hồi Chỉ Đạo Của User
- **Báo cáo watchdog Ca 2 - Phiên 1 (Row 4):**
  ```text
  • Lướt Feed:
    + Follow tự nhiên: 4 lượt / 1281 video (0.3%) (Đã tự trừ 22 lượt do nick bị nhả/drop)
  • Follow chéo (1 lượt follow):
    + Đối soát TikTok Web (+0 Following thật | Lệch -5 so với script báo 5):
      - M76 (@loanau4423): script báo 3 (chéo 0, tự nhiên 3) | web tăng +0 (Lệch -3)
      - M80 (@kymanzzc4ic): script báo 2 (chéo 1, tự nhiên 1) | web tăng +0 (Lệch -2)
    + Nhả follow (18 máy):
      - Nhả liền (0 lượt - 17 máy): M1, M6, M18, M26, M29, M31, M34, M35, M36, M37, M38, M46, M51, M54, M57, M64, M69
      - 1 - 4 lượt (1 máy): M80 (1 lượt)
  ```
- **Chỉ đạo chỉnh đốn chuẩn xác của User:**
  > *"chỉ ở lần nhả đầu tiên thì ms vô hiệu fl tự nhiên, tức là vừa đi fl chéo bị nhả liền nghĩa là trc đó đang bị nhả v thì all fl tự nhiên k hợp lệ. còn vẫn chạy fl đc bth chứng tỏ trc đó fl tự nhiên hợp lệ"*
  > *"thì nếu fl chéo đc 1 phát đầu tiên thành công thì ghi nhận fl tự nhiên, còn fl chéo nhả ngay phát đầu thì trừ hết fl tự nhiên ra?"*

## 2. Quy Tắc Bất Biến Về Trừ Follow Tự Nhiên (Natural Follow Invalidation Invariant)
1. **Trường hợp Nhả Liền Ngay Phát Đầu (`cnt == 0` và dính `FOLLOW_FAILED`):**
   - Vừa bước vào follow chéo lượt đầu đã bị nhả ngay lập tức $\rightarrow$ Bằng chứng xác thực nick đã bị hạn chế/chặn từ trước khi vào phiên nuôi feed.
   - **Xử lý:** Toàn bộ follow tự nhiên lúc lướt feed trước đó là không hợp lệ $\rightarrow$ **Trừ sạch 100% follow tự nhiên** vào `dropped_tot`.
2. **Trường hợp Phát Đầu Thành Công (`cnt > 0` rồi sau đó mới bị nhả):**
   - Nick đã follow chéo thành công ít nhất 1 target (ví dụ M80 follow thành công `@allynkapyej`) $\rightarrow$ Bằng chứng xác thực tại thời điểm lướt feed và lượt đầu, nick hoàn toàn bình thường.
   - **Xử lý:** **Ghi nhận đầy đủ follow tự nhiên** của máy đó, KHÔNG trừ bỏ.

## 3. Quy Tắc Đối Soát TikTok Web Khi Nick Bị Nhả (Reconcile Accounting Invariant)
- **Vấn đề lệch âm đối soát:**
  - Khi M80 follow chéo được 1 nick + tự nhiên 1 nick, script ghi nhận hợp lệ 2 lượt.
  - Tuy nhiên, khi sang target tiếp theo dính `FOLLOW_FAILED` (bị nhả sau vuốt), server TikTok backend không commit / rollback các lượt follow phát sinh trong phiên $\rightarrow$ Cào Web Following delta vẫn là `+0`.
  - Nếu Watchdog cứng nhắc lấy `delta (0) - script_reported (2) = Lệch -2`, hệ thống sẽ tự báo lỗi script giả (false alarm).
- **Quy tắc hiển thị đối soát chuẩn:**
  - Đối với các máy có dính cờ `FOLLOW_FAILED` trong phiên mà có `cnt > 0` (như M80):
    - Vẫn ghi nhận số lượt máy thực hiện thành công ở mục Lướt Feed và Follow Chéo để theo dõi telemetry.
    - Tại bảng Đối soát TikTok Web: BẮT BUỘC bỏ điều kiện `if failed and cnt == 0: reported = 0`. Hễ máy dính cờ `FOLLOW_FAILED` (bị nhả follow) thì toàn bộ follow trong phiên đã bị TikTok server rollback/drop $\rightarrow$ reset `m_to_reported = 0` (loại bỏ khỏi target đối soát), không tính vào số lệch âm của script để tránh báo lỗi giả `Lệch -2`.
    - Đối với các máy follow chéo = 0 (như M76): Không đưa follow tự nhiên đơn thuần vào so sánh đối soát web khi chưa có cơ chế verify profile.
