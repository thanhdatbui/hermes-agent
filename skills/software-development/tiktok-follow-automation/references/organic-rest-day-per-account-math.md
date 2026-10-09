# Per-Account Organic Rest & Rest Probability Math (2026-09-16)

## 1. Bối cảnh & Vấn đề của Modulo 6 cũ
- **Cơ chế cũ (Modulo 6 toàn farm):**
  - Day 0, 4 (Row lẻ) & Day 1, 3 (Row chẵn): Cày (Follow + Upload).
  - Day 2 (Row lẻ) & Day 5 (Row chẵn): Nghỉ dưỡng sinh (Pure Feed, 0 Follow, 0 Upload).
- **Điểm yếu của cơ chế cũ:**
  - Cả farm 80 máy cùng một dải proxy/IP đồng loạt dừng cày hoặc đồng loạt cày theo nhịp cố định 6 ngày.
  - Thuật toán chống bot của TikTok phát hiện cluster pattern đồng nhất theo chu kỳ.

## 2. Công thức Toán học: Chuyển sang Xúc xắc Ngẫu nhiên Độc lập từng Nick
Để bảo toàn chính xác tỷ lệ cày / dưỡng sinh như Modulo 6 cũ mà không tạo pattern toàn farm:

### Phép tính xác suất:
- Mỗi nick trong chu kỳ 6 ngày chỉ chạy vào 3 ngày (dãy Chẵn chạy ngày Chẵn, dãy Lẻ chạy ngày Lẻ).
- Trong 3 ngày được bật máy:
  - 2 ngày Cày (Follow + Upload).
  - 1 ngày Dưỡng sinh (0 Follow, 0 Upload, Pure Feed).
- **Tỷ lệ Dưỡng sinh chính xác = 1/3 (~33.33%)**.
- **Tỷ lệ Cày chính xác = 2/3 (~66.67%)**.
*(Lưu ý: Không dùng 25% vì 25% sẽ làm tăng tỷ lệ cày và giảm thời gian nghỉ so với thiết kế gốc).*

### Thuật toán Deterministic Hash Per-Account:
Để đảm bảo tính nhất quán (Phiên 1 và Phiên 2 trong cùng một ngày của cùng một nick phải có cùng trạng thái):
```python
import hashlib

def is_organic_rest_day(date_str: str, machine: int, row: int) -> bool:
    """Trả về True nếu nick hôm nay trúng lịch nghỉ dưỡng sinh (tỷ lệ 1/3)."""
    h = hashlib.md5(f"{date_str}:{machine}:{row}".encode()).hexdigest()
    # int(h[:8], 16) % 3 == 0 đại diện cho 1/3 xác suất
    return (int(h[:8], 16) % 3) == 0
```

## 3. Quy tắc Thực thi khi trúng Ngày Dưỡng Sinh
1. **Lướt Feed:** Chạy bình thường (Pure Feed) để nuôi trust profile tiêu dùng.
2. **Follow Hook:** Safe-skip toàn bộ lượt follow với reason: `organic-rest-day-pure-feed`.
3. **Upload Hook:** Safe-skip toàn bộ khâu upload với reason: `organic-rest-day-no-upload`.
4. **Báo cáo Watchdog:** Phân loại máy vào nhóm Dưỡng sinh rõ ràng, không tính vào lỗi hay timeout.
