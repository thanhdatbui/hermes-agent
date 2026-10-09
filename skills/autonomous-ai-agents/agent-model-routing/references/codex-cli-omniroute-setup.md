# Codex CLI kết nối OmniRoute (:20129) để chạy GPT Sol / Terra / Luna

## 1. Yêu cầu giao thức của Codex CLI
- Binary `codex-cli` v0.145+ **bắt buộc** dùng `wire_api = "responses"`. Giá trị `"chat"` đã bị gỡ bỏ và sẽ gây lỗi hoặc warning.
- Endpoint `/v1/responses` của OmniRoute (:20129) tương thích hoàn toàn chuẩn Responses API này.

## 2. Cấu hình chuẩn trong `~/.codex/config.toml`
```toml
[model_providers.omni]
name = "OmniRoute"
base_url = "http://localhost:20129/v1"
env_key = "NINEROUTER_API_KEY"
wire_api = "responses"
```

## 3. Cú pháp gọi Codex CLI từ Coordinator / Terminal

### Chạy GPT Sol (Web pool, zero-cost, reasoning đỉnh cao):
```bash
codex exec -c 'model_provider="omni"' -m "chatgpt-web/gpt-5.6-sol-high" --sandbox workspace-write "Mô tả nhiệm vụ sửa code"
```

### Chạy GPT Terra / Luna / Sol API:
```bash
# GPT Sol
codex exec -c 'model_provider="omni"' -m "gpt-5.6-sol" --sandbox workspace-write "Task..."

# GPT Terra
codex exec -c 'model_provider="omni"' -m "gpt-5.6-terra" --sandbox workspace-write "Task..."

# GPT Luna
codex exec -c 'model_provider="omni"' -m "gpt-5.6-luna" --sandbox workspace-write "Task..."
```

## 4. Phân biệt với Hermes `delegate_task`
- Hermes `delegate_task` chỉ dùng 1 model gán cứng toàn cục trong `config.yaml` (`delegation.model`). Không thể chọn model theo từng turn chat.
- Khi cần worker thông minh bậc cao (Sol/Luna) thực hiện code surgery hoặc refactor monolith: **BẮT BUỘC spawn Codex CLI qua terminal** theo cú pháp trên thay vì dùng `delegate_task`.
