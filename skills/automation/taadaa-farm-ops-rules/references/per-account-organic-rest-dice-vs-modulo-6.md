# Per-Account Organic Rest (1/3 Dice) vs Global Modulo 6

## 1. Bối cảnh & Lý do thay đổi
Trước đây, toàn farm áp dụng chu kỳ Modulo 6 toàn cục (`day_cycle = (now - epoch).days % 6`):
- Day 0, 4: Row lẻ cày
- Day 1, 3: Row chẵn cày
- Day 2, 5: Row lẻ / Row chẵn Dưỡng sinh toàn farm (Pure Feed, 0 follow, 0 upload).

**Nhược điểm:** Toàn bộ 80 máy trên farm đồng loạt có hành vi giống hệt nhau (ngày thì cày dồn dập, ngày thì đồng loạt nghỉ), tạo pattern cụm bot (cluster anomaly) rất dễ bị thuật toán Anticheat của TikTok bắt bài.

## 2. Thiết kế Per-Account Organic Rest (Xác suất 1/3)
Giữ nguyên lịch phân định ngày Chẵn/Lẻ theo ngày dương lịch để đảm bảo nhịp sinh học (User Persona):
- **Ngày Lẻ (1, 3, 5, 7...):** Chạy dàn Row 1, 3, 5, 7.
- **Ngày Chẵn (2, 4, 6, 8...):** Chạy dàn Row 2, 4, 6, 8.

Mỗi nick khi đến ngày chạy của mình sẽ tự roll xúc xắc dưỡng sinh độc lập với tỷ lệ đúng bằng Modulo 6 cũ:
- **Tỷ lệ:** $1/3 \approx 33.33\%$ Dưỡng sinh (Pure feed), $2/3 \approx 66.67\%$ Cày (Follow + Upload).
- **Thuật toán băm Deterministic per day:**
  ```python
  def _is_account_organic_rest_day(machine: int, row: int, date_str: str | None = None) -> bool:
      if not date_str:
          date_str = datetime.now().strftime("%Y-%m-%d")
      h = hashlib.md5(f"{date_str}:{machine}:{row}".encode("utf-8")).hexdigest()
      return (int(h[:8], 16) % 3) == 0
  ```
- **Đặc tính:** Cố định cho từng nick trong cả ngày hôm đó (Phiên 1 và Phiên 2 của ca cùng chung trạng thái, không bị đổi tính cách giữa ngày).

## 3. Quy tắc Dưỡng Sinh (Pure Feed)
Khi nick trúng ngày dưỡng sinh:
1. **Follow Hook:** Bỏ qua hoàn toàn (`status: skipped`, `reason: "organic-rest-day-pure-feed"`).
2. **Upload Hook:** Bỏ qua hoàn toàn (`status: skipped`, `reason: "organic-rest-day-no-upload"`).
3. **Lướt Feed:** Vẫn chạy bình thường 100% để tích lũy thời gian xem video, tương tác tim/comment tự nhiên như người dùng tiêu dùng nội dung thật (High Trust Consumer Profile).

## 4. Tác động Báo cáo Watchdog
`feed_session_watchdog.py` tách riêng nhóm máy dưỡng sinh để hiển thị rõ ràng:
- `• Chế độ Dưỡng Sinh (Organic Rest ~33%): 🌿 Nghỉ dưỡng sinh (N máy): ...`
- Không gom lẫn vào danh sách `Bỏ qua` của Follow hoặc Upload gây hiểu lầm là lỗi kỹ thuật.
