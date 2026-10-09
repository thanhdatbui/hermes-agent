# BẪY PHÂN GIẢI PROVIDER TRONG HERMES DELEGATION CONFIG (THE SLASH DELIMITER TRAP)

## 1. Hiện Tượng & Triệu Chứng Lỗi (Symptom)
- Cấu hình trong `config.yaml`:
  ```yaml
  delegation:
    model: codex/gpt-5.6-luna-high
    provider: custom:omni
  ```
- Kỳ vọng: Subagent worker qua `delegate_task` sẽ gọi model `gpt-5.6-luna-high` qua cổng `codex` trên OmniRoute (:20129).
- Thực tế quan sát:
  - Worker chạy nhưng log trên OmniRoute `storage.sqlite` **HOÀN TOÀN KHÔNG CÓ BÓNG DÁNG CỦA CODEX**.
  - Toàn bộ request bị bắn về `antigravity/gemini-3.8-flash-tiered` (model của Coordinator chính).

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
- Hermes core parser khi đọc chuỗi `delegation.model`:
  - Nếu chuỗi chứa ký tự gạch chéo `/` (như `codex/gpt-5.6-luna-high`), parser nội bộ của Hermes tự động tách chuỗi theo định dạng `<provider>/<model>`.
  - Nó coi `codex` là tên provider và `gpt-5.6-luna-high` là tên model.
  - Tuy nhiên, trong danh sách `custom_providers` của Hermes **không tồn tại provider nào tên là `codex`** (chỉ có `custom:omni` hoặc `custom:9router`).
  - Khi không tìm thấy provider `codex`, cơ chế `resolve_provider` thất bại và **âm thầm fallback về parent coordinator model** (`ag-gemini-pool-3` / `antigravity`).

## 3. Giải Pháp Khắc Phục Triệt Để (Verified Fix)
Trong OmniRoute (:20129), các model Codex GPT đều có alias với prefix `cx/` hoặc alias trực tiếp. Chuỗi `cx/` không trùng với bất kỳ provider nào nên Hermes giữ nguyên mapping với `provider: custom:omni`:

### Cách cấu hình đúng 100%:
Trong `C:/Users/Kibe/AppData/Local/hermes/config.yaml`:
```yaml
delegation:
  child_timeout_seconds: 480
  max_concurrent_children: 6
  max_iterations: 35
  model: cx/gpt-5.6-luna-high     # Dùng alias 'cx/' thay vì 'codex/'
  provider: custom:omni          # Provider đúng đã khai báo trong custom_providers
  reasoning_effort: high
```

Hoặc dùng alias đã khai báo trong provider `omni`:
- `cx/gpt-5.6-luna-high` (Codex Luna High)
- `codex-luna` (Codex Luna Medium)
- `codex-terra` (Codex Terra Medium)

## 4. Công Thức Kiểm Chứng Độc Lập (Verification Probe)
Sau khi đổi cấu hình, bắt buộc kiểm tra log SQLite của OmniRoute để xác nhận request đã chạm tới Codex:
```python
import sqlite3
conn = sqlite3.connect('C:/Users/Kibe/.omniroute/storage.sqlite')
c = conn.cursor()
c.execute("SELECT timestamp, requested_model, model, provider, duration, status FROM call_logs ORDER BY rowid DESC LIMIT 1")
row = c.fetchone()
print(row)
# Kỳ vọng: provider == 'codex' và status == 200
```
