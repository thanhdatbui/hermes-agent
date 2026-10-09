# Pitfall & Procedure: Verifying Status and Combo Append for OAuth Pipeline

Khi tự động hóa hoặc viết test verification cho việc nạp OAuth qua pipeline GPM + Singbox và append vào combo OmniRoute (ví dụ: `run_oauth_s7_pipeline.py` & `append_to_combo_pool3.py`):

## 1. Cấu trúc lưu trữ trong `oauth_pipeline_status.json`
- File `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json` không lưu account status ở cấp root (`status_data.get(email)` sẽ trả về `None`).
- Thay vào đó, các account hoàn thành OAuth thành công được lưu trữ bên dưới sub-key `"omniroute_success"`:
  ```python
  status_data = json.load(f)
  acc_stat = status_data.get("omniroute_success", {}).get(email)
  # acc_stat có dạng: {'machine': 26, 'port': 5132, 'connection_id': '...', 'status': 'HTTP_200_OK'}
  ```

## 2. Kiểm tra target trong Combos OmniRoute
- `append_to_combo_pool3.py` gửi PUT request lên OmniRouter API (`http://127.0.0.1:20129/api/combos`) và sau đó ghi đè / backup danh sách combo vào `combos_backup.json` tại thời điểm đó.
- Khi probe kiểm tra xem connection_id đã vào combo chưa:
  - Nên probe trực tiếp live API endpoint: `http://127.0.0.1:20129/api/combos`
  - Hoặc đọc `D:\Taadaa\AI-Tools\tools\omniroute\combos_backup.json` và duyệt:
    ```python
    pool = next((c for c in combos if c.get("name") == "ag-gemini-pool-3"), None)
    # Target structure: {'connection_id': cid, 'model': '...', 'weight': 1, 'priority': 1, 'label': ...}
    ```
