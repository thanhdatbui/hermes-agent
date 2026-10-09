# Hermes Fallback Chain giữa OmniRoute (:20129) và 9Router (:20128)

Tài liệu hướng dẫn và pitfall cấu hình chuỗi tự động cứu hộ (Fallback Provider Chain) cho Hermes Coordinator / Worker khi OmniRoute gặp sự cố sập hoặc khởi động lại.

---

## 1. Cơ chế hoạt động của Hermes Fallback Chain

Hermes Agent có sẵn cơ chế `fallback_providers` (quản lý qua `hermes fallback` hoặc `config.yaml`):

1. **Tự động failover khi Primary sập:**
   * Khi Primary provider (`omni` ở port 20129) bị quá tải, rớt socket (`WinError 10054`), Watchdog kill do lag health check, hoặc trả lỗi HTTP `429/500/502/503`, Hermes không văng session mà lập tức chuyển runtime sang provider kế tiếp trong chuỗi fallback (`custom:9router` ở port 20128).
2. **Turn-scoped Restoration (Tự động quay về Primary):**
   * Fallback chỉ giữ hiệu lực trong turn bị lỗi. Sang turn tiếp theo, Hermes tự động khôi phục lại cấu hình Primary (`omni`) để thử lại.
   * Nếu OmniRoute đã hoàn tất khởi động lại, request tiếp tục chạy trên Omni. Nếu Omni vẫn chưa sẵn sàng, Hermes lại tiếp tục rơi sang Fallback.

---

## 2. Pitfalls nghiêm trọng cần tránh

### Pitfall 1: Lỗi định dạng JSON string trong `config.yaml`
* **Triệu chứng:** `hermes fallback list` báo `No fallback providers configured.` dù trong `config.yaml` thấy có dòng `fallback_providers: '[{"model": ...}]'`.
* **Nguyên nhân:** Hàm `get_fallback_chain()` trong `hermes_cli/fallback_config.py` kiểm tra `isinstance(raw, list)`. Khi giá trị bị bọc trong dấu nháy dạng JSON string (`str`), parser bỏ qua toàn bộ và trả về `[]`.
* **Khắc phục:** Bắt buộc cấu hình dưới dạng YAML List chuẩn:
  ```yaml
  fallback_providers:
    - model: 9r-free
      provider: custom:9router
  ```

### Pitfall 2: Fallback nội bộ cùng instance (Ngõ cụt)
* **Sai lầm:** Đặt Primary là `omni` (`model: omni-worker`), và Fallback là `omni-free` cũng trên provider `omni` (port 20129).
* **Hậu quả:** Khi process `node.exe` của OmniRoute bị Watchdog terminate hoặc crash do OOM, toàn bộ port 20129 đóng kết nối. Fallback vào `omni-free` cũng chết theo, dẫn đến fail toàn bộ session.
* **Quy tắc:** Provider fallback BẮT BUỘC phải trỏ sang instance độc lập: `custom:9router` (port 20128) với model như `9r-free` hoặc `ag/gemini-3.7-flash-high`.

---

## 3. Lệnh kiểm tra xác thực (Verification O(1))

Sau khi cấu hình, luôn chạy:
```bash
hermes fallback list
```
Kết quả đúng chuẩn phải hiển thị:
```text
  Primary:   omni-worker (via omni)

  Fallback chain (1 entry):
    1. 9r-free (via custom:9router)

  Tried in order when the primary fails (rate-limit, 5xx, connection errors).
```
