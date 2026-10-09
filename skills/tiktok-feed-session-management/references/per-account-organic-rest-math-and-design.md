# Chuyển Đổi Mô Hình Dưỡng Sinh: Modulo 6 Sang Xúc Xắc Độc Lập Từng Nick (Per-Account Organic Rest)

## 1. Bối cảnh & Lý Do Chuyển Đổi
- **Hạn chế của Modulo 6 toàn farm:**
  - Day 0, 4 (Row lẻ) & Day 1, 3 (Row chẵn): Cày (Follow + Upload).
  - Day 2 (Row lẻ) & Day 5 (Row chẵn): Nghỉ dưỡng sinh (Pure Feed, 0 Follow, 0 Upload).
  - Điểm yếu: Toàn bộ 80 máy trên cùng dải IP/Proxy cùng nghỉ hoặc cùng cày đồng loạt theo chu kỳ 6 ngày, dễ bị hệ thống AI Anticheat của TikTok nhận diện pattern cụm (Cluster Bot Detection).
- **Mục tiêu mô hình mới:**
  - Bỏ ngày dưỡng sinh cố định của toàn farm.
  - Phân bổ trạng thái Dưỡng sinh ngẫu nhiên độc lập cho từng nick (từng máy) nhưng **bảo toàn 100% tỷ lệ toán học của Modulo 6 cũ**.

## 2. Chứng Minh Toán Học Tỷ Lệ Xác Suất
- Trong chu kỳ 6 ngày của Modulo 6 cũ, mỗi nick chỉ được bật máy vào 3 ngày (dãy Chẵn bật ngày Chẵn, dãy Lẻ bật ngày Lẻ).
- Trong 3 ngày được bật:
  - 2 ngày CÀY (Follow 10–20 lượt + Đăng Video).
  - 1 ngày DƯỠNG SINH (0 Follow + 0 Video, chỉ lướt Feed thuần).
- **Tỷ lệ Dưỡng sinh chuẩn = 1/3 (~33.33%)**.
- **Tỷ lệ Cày chuẩn = 2/3 (~66.67%)**.
*(Lưu ý: Không dùng tỷ lệ 25% vì 25% sẽ làm tăng tỷ lệ cày lên 75% và giảm số ngày nghỉ dưỡng sinh, làm sai lệch so với thiết kế gốc).*

## 3. Thuật Toán Deterministic Random Hash Cho Từng Máy
Mỗi khi đến ca chạy của nick (Machine, Row) trong ngày (`YYYY-MM-DD`):
```python
import hashlib

def is_account_organic_rest_day(date_str: str, machine: int, row: int) -> bool:
    """Xác định trạng thái dưỡng sinh độc lập cho từng nick (bảo toàn tỷ lệ 1/3)."""
    h = hashlib.md5(f"{date_str}:{machine}:{row}".encode()).hexdigest()
    # int(h[:8], 16) % 3 == 0 đại diện cho xác suất chính xác 1/3 (33.33%)
    return (int(h[:8], 16) % 3) == 0
```
- **Tính nhất quán giữa các phiên:** Dùng chung hash `date:machine:row` đảm bảo trong cùng một ngày, cả Phiên 1 và Phiên 2 của nick đó đều có chung một trạng thái (không bị Phiên 1 cày, Phiên 2 lại dưỡng sinh).

## 4. Nguyên Tắc Hành Vi Khi Rơi Vào Ngày Dưỡng Sinh
- **Lướt Feed:** Chạy bình thường (Pure Feed) để tích lũy trust của tài khoản tiêu dùng (Consumer Profile).
- **Follow Hook:** Safe-skip toàn bộ lượt follow với reason: `organic-rest-day-pure-feed`.
- **Upload Hook:** Safe-skip toàn bộ lượt đăng video với reason: `organic-rest-day-no-upload`.
- **Hiệu quả toàn farm:** Bất kỳ ngày nào cũng luôn có ~67% máy cày và ~33% máy dưỡng sinh đan xen tự nhiên, xóa bỏ hoàn toàn chữ ký bot cụm trên toàn bộ dải IP/Proxy.
