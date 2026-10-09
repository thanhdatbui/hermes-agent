# Hermes Native Fallback Model Configuration & Farm Operational Boundary (2026-09-24)

Kinh nghiệm vận hành và cấu hình fallback model trực tiếp trên Hermes Agent cho Phone Farm 160 máy, phân định ranh giới giữa automation scripts và LLM orchestration.

## 1. Ranh Giới Thực Tế: Phone Farm Automation vs Hermes LLM

- **Bản chất hạ tầng Phone Farm 160 máy**: 160 thiết bị Android vận hành hoàn toàn bằng các kịch bản tự động hóa cục bộ (Python, ADB, ATX, UI XML, proxy socks5). Các máy này chạy độc lập, xử lý luồng công việc (Feed, Reg, Login, Follow) mà **KHÔNG hề gọi API LLM**.
- **LLM chỉ phục vụ DUY NHẤT một thực thể**: Đó là **Hermes Agent** (người điều phối Coordinator trong session Telegram/CLI và các subagent Worker được spawn khi gọi `delegate_task`).
- **Sai lầm lý thuyết cần tránh**: Không áp dụng các giả định máy móc về việc "160 máy đồng loạt gọi LLM tạo bão request đánh sập quota". Mọi tính toán quota (Codex, Web, Gemini) chỉ tính trên số lượng turn điều phối của Coordinator (1–3 calls/task) và subagent Worker (5–15 calls/task).

---

## 2. Yêu Cầu Cấu Hình Fallback: Mô Hình Hybrid Kép (Hermes Root + OmniRoute Tier 3)

Khi cần thiết lập **Luna High (`cx/gpt-5.6-luna-high`)** làm tuyến dự phòng cứu nguy khi model chính (`omni-worker`) ngã, user đã chuẩn hóa mô hình **Hybrid 2 Tầng**:
- **Ở tầng OmniRoute Combo (`omni-worker`)**: Đưa Luna High vào làm **Tier 3 (ƯU TIÊN TRƯỚC SONNET)**, đổi tên combo `ag-claude` thành `ag-sonnet`:
  - Tier 1: `ag-gemini-pool-3` (16 Gemini Pro)
  - Tier 2: `ag-gemini-free-pool` (87 Gemini Free)
  - 🎯 **Tier 3**: `codex/gpt-5.6-luna-high` (Codex Pool - Cứu cánh cấp Senior, đứng trước Sonnet)
  - Tier 4: `ag-sonnet` (89 Claude Sonnet 4.6 accounts - Phòng vệ tầng đáy của Proxy)
  *(Không để Luna High nằm dưới đáy Tier 4 sau Sonnet; hễ Google lỗi là nhảy vào Luna High ngay)*.
- **Ở tầng Hermes Agent (`config.yaml`)**:
  Cấu hình `fallback_model` độc lập ở cấp root. Đây là lưới an toàn nếu toàn bộ proxy OmniRoute bị đứt kết nối. Cả Coordinator và Subagent Worker đều được bảo vệ.

---

## 3. Cú Pháp Chuẩn Trong `config.yaml` Của Hermes

Trong file `C:/Users/Kibe/AppData/Local/hermes/config.yaml`:

```yaml
fallback_model:
  provider: custom:omni
  model: cx/gpt-5.6-luna-high
  base_url: http://192.168.110.123:20129/v1
  api_key: sk-24749f1a8e3d4c5b6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f
```

*Lưu ý khi dùng custom provider*:
- Trường `base_url` và `api_key` (hoặc `key_env: OMNIROUTE_API_KEY`) phải được cung cấp rõ ràng trong object fallback để hàm `resolve_provider_client()` trong `agent/chat_completion_helpers.py` khởi tạo đúng HTTP client mà không bị rơi vào lỗi `custom/main requested but no endpoint credentials found`.
- Khai báo model trong `custom_providers`:
  ```yaml
  custom_providers:
    - name: omni
      base_url: http://192.168.110.123:20129/v1
      models:
        omni-worker:
          context_length: 200000
        cx/gpt-5.6-luna-high:
          context_length: 256000
  ```

---

## 4. Cơ Chế Hoạt Động & Kế Thừa Của Core Hermes

Mã nguồn Hermes Agent bảo đảm tính kế thừa fallback tuyệt đối từ cha sang con:

### A. Ở Session Chính (Coordinator)
- Được khởi tạo với chuỗi fallback từ root config: `agent._fallback_chain = [{'provider': 'custom:omni', 'model': 'cx/gpt-5.6-luna-high', ...}]`.
- Khi `omni-worker` gặp lỗi 429, timeout, connection drop:
  Hàm `try_activate_fallback()` trong `agent/chat_completion_helpers.py` kích hoạt, đổi model in-place sang `cx/gpt-5.6-luna-high`.
- Reasoning config được re-resolve tự động qua `agent.reasoning_overrides` hoặc global effort `high`.

### B. Ở Subagents (Worker khi gọi `delegate_task`)
- Trong `tools/delegate_tool.py` (dòng 1280 & 1332):
  ```python
  parent_fallback = getattr(parent_agent, "_fallback_chain", None) or None
  child = AIAgent(
      ...,
      fallback_model=parent_fallback,
      ...
  )
  ```
- Subagent Worker **tự động kế thừa 100% chuỗi fallback** này từ Coordinator.
- Khi Worker đang sửa code/chạy test mà `omni-worker` gặp sự cố, Worker tự động failover sang `cx/gpt-5.6-luna-high` để hoàn thành nốt nhiệm vụ trong isolated sandbox.

---

## 5. Xác Minh Thực Tế Bằng Code (Verification Script)

```python
from tools.delegate_tool import _build_child_agent
from run_agent import AIAgent

parent = AIAgent(
    model="omni-worker",
    provider="omni",
    base_url="http://localhost:20129/v1",
    api_key="sk-dummy",
    fallback_model={
        "provider": "custom:omni",
        "model": "cx/gpt-5.6-luna-high",
        "base_url": "http://localhost:20129/v1",
        "api_key": "sk-dummy"
    }
)

child = _build_child_agent(
    task_index=0, goal="test", context="", toolsets=None,
    model=None, max_iterations=10, task_count=1, parent_agent=parent
)

assert parent._fallback_chain == child._fallback_chain
print("VERIFIED: Subagent successfully inherited fallback_model from Parent Coordinator!")
```
