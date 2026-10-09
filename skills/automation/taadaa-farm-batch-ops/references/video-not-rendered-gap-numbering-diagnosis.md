# Chuẩn Đoán & Khắc Phục Lỗi "Chưa render/thiếu video" (video_not_rendered) Do Gap Numbering

## 1. Hiện Tượng (Symptom)
- Watchdog feed session (`feed_session_watchdog.py`) báo cáo mục **Đăng Video**:
  `+ Bỏ qua (N): ... Chưa render/thiếu video (X)`
- Kiểm tra log chi tiết `upload_result.json`:
  ```json
  {
    "machine": 51,
    "row": 5,
    "status": "skipped",
    "reason": "video_not_rendered",
    "expected_video": "D:\\TIKTOK-videonuoinick\\405\\1.mp4",
    "workbook": "Tik5.xlsx"
  }
  ```
- Tuy nhiên kiểm tra thực tế thư mục `D:\TIKTOK-videonuoinick\405\` thì có tới 30-45 video clip hoàn chỉnh.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
- **Công thức cứng ngắc (Strict sequential cursor)**:
  - Logic Gate 5 trong runner (`multi_machine_feed_session.py` / `run_post.py`) tìm chính xác file theo công thức:
    `expected_video = (posted_count + 1).mp4`
  - Nếu file số 1 hoặc số kế tiếp bị khuyết do quá trình render/download sinh dãy số nhảy cóc (gap numbering, ví dụ bắt đầu từ `2.mp4` hoặc dãy `1.mp4, 3.mp4, 4.mp4` thiếu `2.mp4`), runner lập tức đánh dấu `video_not_rendered` và bỏ qua (skip) lượt đăng dù kho còn hàng chục video.

## 3. Cách Kiểm Tra Nhanh O(1) Toàn Farm (Tik1..Tik8)
Chạy script Python kiểm tra đối soát giữa workbook và filesystem:
```python
import openpyxl, os
from pathlib import Path

media_root = Path(r'D:\TIKTOK-videonuoinick')

for num in range(1, 9):
    fn = f'Tik{num}.xlsx'
    p = Path(r'D:\OneDrive\TaadaaData\kibe') / fn
    if not p.exists():
        p = Path(r'D:\OneDrive\TaadaaData\kibe') / f'tik{num}.xlsx'
    if not p.exists():
        continue
    
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    ws = wb.active
    headers = [c for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        d = dict(zip(headers, row))
        m = d.get('Máy')
        f = d.get('Folder Video')
        posted = d.get('Video Đã Đăng') or 0
        expected = (posted if isinstance(posted, int) else 0) + 1
        
        if f:
            target = media_root / str(f) / f'{expected}.mp4'
            if not target.exists():
                print(f"Tik{num} Máy {m} (Folder {f}) -> Thiếu {expected}.mp4")
```

## 4. Giải Pháp Xử Lý
1. **Data Level (Khắc phục tức thì)**:
   Sao chép 1 file số cao nhất trong folder thành file số đang thiếu (ví dụ copy file lớn nhất thành `1.mp4` hoặc `2.mp4`) để lấp đầy gap numbering.
2. **Code Level (Phòng ngừa cấu trúc)**:
   Nâng cấp logic Gate 5 trong `multi_machine_feed_session.py`: Khi `{next_video}.mp4` không tồn tại, tự động quét thư mục tìm file `.mp4` có số nhỏ nhất $\ge \text{next\_video}$ để làm candidate upload, chống fail im lặng khi kho video vẫn còn dồi dào.
