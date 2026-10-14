# Quy Chuẩn Nạp Module Dưỡng Sinh Động (Day 4 & Ca 3 Day 3) trong Hermes Cron

## Bối cảnh và Sự cố
Trong chu kỳ nuôi 4 ngày:
- Ngày 1: Ca 1 (Row 1) - Ca 2 (Row 3) - Ca 3 (Row 5)
- Ngày 2: Ca 1 (Row 2) - Ca 2 (Row 4) - Ca 3 (Row 6)
- Ngày 3: Ca 1 (Row 7) - Ca 2 (Row 8) - Ca 3 (Dưỡng sinh động)
- Ngày 4: Dưỡng sinh xả tải toàn farm (toàn bộ 3 ca đều chạy dưỡng sinh động)

Module `D:/Taadaa/tools/healing_selector.py` chịu trách nhiệm chấm điểm để chọn row tài khoản yếu nhất farm cần hồi phục:
$$\text{Score} = 100 \times p_{\text{fail}} + 20 \times p_{\text{young}}$$

## Bẫy Đường Dẫn Khi Deploy Runner Ngoài Repo
Khi runner script được sao chép và kích hoạt từ môi trường thực thi cron riêng biệt ngoài cây thư mục git:
- `Path(__file__).resolve().parents` chỉ duyệt ngược các thư mục cha trên ổ đĩa chứa file thực thi, không bao giờ chạm tới `D:/Taadaa/tools`.
- Nếu biến môi trường `HERMES_CRON_TOOLS_DIR` chưa được set ở process cha, hàm `_load_determine_healing_row()` sẽ quăng ngoại lệ `ImportError`.
- Khi dính `ImportError`, runner bị ép nhảy vào nhánh `except` fallback tĩnh:
  - Ca 1 (06h, 08h) -> Row 3
  - Ca 2 (12h, 14h) -> Row 4
  - Ca 3 (18h, 20h) -> Row 5
  Dẫn đến việc ngày dưỡng sinh không bốc được đúng các row yếu nhất (như Row 2, Row 7).

## Giải Pháp Chuẩn Hóa
1. **Đọc cấu hình môi trường repo:** Nạp `HERMES_CRON_TOOLS_DIR` từ `repo_env_overrides()` (`env.json`) nếu `os.environ` chưa có.
2. **Khai báo danh sách candidate roots dự phòng:** Bổ sung các đường dẫn gốc đã biết:
   - `D:/Taadaa/tools`
   - `D:/Taadaa/tiktok-luot nuoi acc/tools`
   - `D:/Taadaa/automation-core/tools`
3. **Phòng thủ chiều sâu trong `env.json`:** Luôn ghi nhận `"HERMES_CRON_TOOLS_DIR": "D:/Taadaa/tools"` trong `runtime/hermes-cron/env.json`.
