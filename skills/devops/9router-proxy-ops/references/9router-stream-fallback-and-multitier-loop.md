# 9Router SSE Streaming Fallback Limitation & Multi-Tier Loop Architecture

## 1. Cơ Chế Combo Fallback & Tử Huyệt SSE Stream trên 9Router (:20128)

Trong mã nguồn xử lý Combo của 9Router (`app/.next-cli-build/server/chunks/8910.js` / `chatCore.ts`):
- Khi client (Hermes Gateway) gửi request với `stream: true`, hàm `handleSingleModel(body, model)` thiết lập kết nối HTTP đến upstream provider (OpenRouter, OpenCode...).
- **Nếu Upstream trả HTTP 429 hoặc 5xx ngay tại bước handshake:**
  `response.ok == false` $\rightarrow$ 9Router kích hoạt logic fallback: ghi log `⚠️ [COMBO] Model X failed, trying next {"status": 429/503}` và chuyển sang thử model tiếp theo trong danh sách combo.
- **Tử huyệt Streaming Error (Ví dụ Nvidia Nemotron trên OpenRouter):**
  1. OpenRouter chấp nhận kết nối và trả về ngay **HTTP 200 OK** với header `Content-Type: text/event-stream`.
  2. Vì `response.ok == true`, 9Router coi model đó đã thành công và bắt đầu pipe dòng dữ liệu SSE trực tiếp về cho Hermes.
  3. Ngay chunk đầu tiên, upstream trả về lỗi nghiệp vụ:
     ```json
     data: {"error": {"message": "Upstream error from Nvidia: Service temporarily overloaded", "code": 502}}
     ```
  4. Lúc này socket stream đã mở và đang truyền dở sang client, 9Router **không thể tua lại stream** để gọi model số 2, đành chuyển tiếp nguyên vẹn chunk lỗi 502 về Hermes.

## 2. Phản Ứng Dây Chuyền Tại Hermes Gateway
- Hermes nhận được event stream có chứa `error` $\rightarrow$ ghi log `Streaming failed before delivery: Upstream error from Nvidia: Service temporarily overloaded`.
- Hermes thực hiện retry `attempt 2/2` vào cùng provider `custom:9router` và model `9r-free`.
- Ở lần 2, 9Router tiếp tục chọn model số 1 vì model này chưa bị đánh dấu cooldown (do tầng HTTP trả về 200 OK chứ không phải 429 hay 503).
- Lần 2 tiếp tục fail $\rightarrow$ Hermes Gateway cạn retry và báo lỗi sập model diện rộng (`⚠️ The model provider failed after retries`).

## 3. Quy Chuẩn Tối Ưu Combo `9r-free` (Không Để 1 Model Chẹn Họng Cả Chuỗi)
- **CẤM đặt model hay bị lỗi stream 502 (như Nvidia Nemotron Free) ở vị trí Top 1 của combo.**
- Luôn ưu tiên các model phản hồi tức thì, ổn định và stream sạch lên đầu danh sách:
  1. `openrouter/cohere/north-mini-code:free` (Phản hồi <1.2s)
  2. `openrouter/liquid/lfm-2.5-2.6b:free` (Phản hồi ~0.7s)
  3. `openrouter/dots-studio/dots-3-note-preview:free`
  4. `openrouter/inclusionai/ling-3.0-flash-fin:free`
  5. `oc/ling-3.0-flash-fin-free`
  6. `oc/mimo-v2.5-free`
  7. `oc/big-pickle`
  8. `openrouter/nvidia/nemotron-3-super-120b-a12b:free` (Đẩy xuống cuối cùng)

## 4. Kiến Trúc Fallback Vòng Lặp Đa Tầng Cứu Cánh (Omni ⇄ 9Router Loop)
Khi OmniRoute (:20129) bị Watchdog restart đột ngột, tiến trình chỉ mất 10-30s để hồi phục. Thiết lập chuỗi fallback nhiều tầng tại Hermes `config.yaml`:
```yaml
fallback_providers:
  - provider: custom:9router
    model: 9r-free
  - provider: custom:9router
    model: opencode-free
  - provider: omni
    model: ag-gemini-pool-3
```
- **Tầng 1 (`9r-free` qua 9Router):** Nhận diện xử lý ngay khi Omni sập.
- **Tầng 2 (`opencode-free` qua 9Router):** Dự phòng độc lập nếu OpenRouter bị throttle / dính stream error.
- **Tầng 3 (`ag-gemini-pool-3` qua Omni):** Vòng ngược trở lại OmniRoute sau khi Omni đã khởi động lại xong. Lưu ý: Trỏ về `ag-gemini-pool-3` (Pool Antigravity Gemini Flash luôn sẵn sàng 100%), KHÔNG trỏ về `omni-free` (vốn chứa các model OpenCode hay bị timeout/throttle).

## 5. Lưu Ý Cấu Hình Hermes CLI & Deploy
- Khi dùng lệnh CLI `hermes config set fallback_providers ...`, tool có thể parse chuỗi JSON thành string thay vì list object. Luôn kiểm tra lại bằng `hermes fallback list` hoặc dùng Python `save_config` để đảm bảo format chuẩn list dict:
  ```python
  from hermes_cli.config import load_config, save_config
  cfg = load_config()
  cfg["fallback_providers"] = [
      {"model": "9r-free", "provider": "custom:9router"},
      {"model": "opencode-free", "provider": "custom:9router"},
      {"model": "ag-gemini-pool-3", "provider": "omni"}
  ]
  save_config(cfg)
  ```
- Đồng bộ ngay vào file deploy bundle: `D:/Taadaa/Hermes/deploy/hermes-home/config.yaml`.

---

## 6. Bẫy Tử Huyệt: Gán Model Antigravity vào `custom:9router` Trong `fallback_providers`
### Hiện tượng
- Hermes log tràn ngập lỗi:
  `ERROR agent.conversation_loop: API call failed after 2 retries. HTTP 404: No active credentials for provider: antigravity | provider=custom:9router model=gpt-5.6-luna` hoặc `model=gemini-3.7-flash-high`.
- Subagent khi delegate hoặc agent khi đang chat bị sập ngang dù tài nguyên máy và pool Antigravity vẫn hoạt động tốt.

### Nguyên nhân gốc rễ
1. **Lệch Phân Vai Giữa 9Router (:20128) và OmniRoute (:20129):**
   - Toàn bộ 110+ tài khoản Antigravity (Gemini Pro, Gemini Free, Claude Sonnet) và ChatGPT Web/Codex hiện đã được tập trung quản trị tại **OmniRoute (:20129)**.
   - **9Router (:20128) KHÔNG CÒN lưu active credentials cho provider `antigravity`**.
2. **Cấu Hình Fallback Sai Bản Chất:**
   - Trong `config.yaml`, nếu khai báo:
     ```yaml
     fallback_providers:
       - model: gemini-3.7-flash-high
         provider: custom:9router
       - model: gpt-5.6-luna
         provider: custom:9router
     ```
   - Khi primary provider (`omni-worker` trên `custom:omni`) gặp độ trễ do reasoning token dài (>15s) hoặc timeout kết nối, Hermes Gateway tự động kích hoạt chuỗi fallback sang `custom:9router`.
   - Vì 9Router không có credential cho `antigravity`, nó lập tức trả về `HTTP 404: No active credentials for provider: antigravity`, khiến toàn bộ chuỗi fallback sụp đổ ngay lập tức.

### Quy Chuẩn Cấu Hình An Toàn Tuyệt Đối
1. **Chỉ trỏ model Free vào `custom:9router`:**
   - Trên `custom:9router`, CHỈ sử dụng các model OpenRouter/OpenCode miễn phí: `9r-free`, `opencode-free`.
2. **Model Antigravity / Gemini / Claude BẮT BUỘC trỏ về `omni` (:20129):**
   - Nếu cần fallback về pool Gemini hoặc Claude, bắt buộc dùng `provider: omni` với model `ag-gemini-pool-3` hoặc `omni-free`.
3. **Cấu hình chuẩn hóa mẫu:**
   ```yaml
   fallback_providers:
     - provider: custom:9router
       model: 9r-free
     - provider: omni
       model: ag-gemini-pool-3
   ```

