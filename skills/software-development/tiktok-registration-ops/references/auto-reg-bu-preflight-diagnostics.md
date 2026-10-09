# Chẩn đoán & Vận hành Tự Động Reg Bù (Preflight Ensure Row Accounts)

## 1. Cơ chế Tự Động Reg Bù theo Ca
Hệ thống tự động reg bù được tích hợp trực tiếp vào `tiktok_runner.py` thông qua hook:
`_preflight_ensure_accounts(row, window_key, cluster)` chạy trước mỗi window nuôi feed:
- Khung giờ kích hoạt: `00:00`, `01:30`, `06:00`, `08:00`, `12:00`, `14:00`, `18:00`, `20:00`.
- Script thực thi lõi: `D:\Taadaa\tools\ensure_row_accounts.py <row>`.
- Marker quản lý: `.preflight_<cluster>_<window_key>` (JSON metadata, tự xóa fail-open nếu batch lỗi).

### Chu kỳ Parity Chẵn/Lẻ theo ngày:
- **Ngày dương lịch CHẴN (Day % 2 == 0):** Chạy các Row chẵn:
  - 00:00 & 01:30 -> Row 8
  - 06:00 & 08:00 -> Row 2
  - 12:00 & 14:00 -> Row 4
  - 18:00 & 20:00 -> Row 6
- **Ngày dương lịch LẺ (Day % 2 == 1):** Chạy các Row lẻ:
  - 00:00 & 01:30 -> Row 7
  - 06:00 & 08:00 -> Row 1
  - 12:00 & 14:00 -> Row 3
  - 18:00 & 20:00 -> Row 5

> **Pitfall:** Nếu máy thiếu tài khoản ở Row ngược parity với ngày hiện tại (ví dụ: M62 thiếu Row 3 nhưng hôm nay là ngày 24 chẵn), preflight sẽ CHƯA chạy cho Row đó cho đến ngày kế tiếp.

---

## 2. Quy trình Chẩn đoán O(1) khi User hỏi "Sao không tự reg bù máy thiếu"

### Bước 1: Kiểm tra danh sách máy thiếu thực tế
Chạy dry-run kiểm tra:
```bash
python D:/Taadaa/tools/ensure_row_accounts.py <row> --dry-run
```
Kiểm tra xem máy có nằm trong danh sách `missing` hay không, và có sẵn mail trong `gmail_clean_v2.xlsx` hay không.

### Bước 2: Kiểm tra lịch sử Batch Runs gần nhất
Vào thư mục artifact của cluster tương ứng:
- Kibe: `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\`
- Admin: `D:\Taadaa\runtime\admin\artifacts\runs\social-batch-all\`

Đọc file `all_results.json` của run mới nhất trong ngày để xem trạng thái của các STT:
```python
import json
from pathlib import Path
latest_run = sorted(Path(r'D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all').glob('20*'))[-1]
results = json.loads((latest_run / 'all_results.json').read_text(encoding='utf-8'))
for t in results:
    print(t.get('stt'), t.get('status'))
```

### Bước 3: Đọc log lỗi chi tiết từng máy
Tại `batch_1/stt_<M>/stderr.log` hoặc `stdout.log`:
- `[04_add_account] MACHINE_FULL_8_ACCOUNTS`: Máy đã có đủ 8 tài khoản trên TikTok Switcher thực tế -> nút "Thêm tài khoản" bị ẩn.
  - **Nguyên nhân:** Lệch giữa Excel và máy thực tế (nick ký sinh từ máy khác hoặc nick cũ chưa đồng bộ vào Excel).
  - **Khắc phục:** Không tự ý reg đè. Kiểm tra ảnh dropdown `D:/Taadaa/Tiktok_Reg/screenshots_social/<M>_03_dropdown_*.png`, xác định nick ký sinh/thừa, thực hiện logout an toàn trước khi chạy lại reg.
- `AdbCommandTimeout: UI_XML_TIMEOUT`: Máy bị đơ/lag ADB hoặc atx-agent -> toggle Wi-Fi / reboot thiết bị.
- `[03_dropdown] Khong mo duoc account dropdown`: Kẹt giao diện TikTok hoặc chưa vào được Profile.
- `KeyError: "[Content_Types].xml"`: File Excel tracking bị lỗi nén zip khi lưu. Khôi phục từ file backup `.bak_<timestamp>` gần nhất trong cùng thư mục.
