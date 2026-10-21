# Cấm Tuyệt Đối Fallback Sang Luna Cho Hermes Coordinator

## 1. Hiện tượng & Vấn đề thực tiễn (Case Study 2026-10-21)
- **Bối cảnh:** Khi toàn bộ pool Gemini (`omni-worker` / `ag-gemini-pool-3`) trên OmniRoute (:20129) bị chạm trần quota hoặc dính 429 tạm thời, Hermes kích hoạt chuỗi `fallback_providers`.
- **Hậu quả khi fallback sang Luna (`gpt-5.6-luna` qua custom:9router hoặc custom:cockpit):**
  1. **Bảo thủ & Bại liệt (Defensive Paralysis):** Luna là conversational model, thiếu năng lực điều phối agentic phức tạp. Vừa gặp 1 lệnh terminal timeout (như `inspect_machine.py`), nó lập tức tự ý tuyên bố task `BLOCKED` và dừng phiên để trốn việc.
  2. **Vi phạm Guard cơ học:** Không nắm được các invariant của Coordinator, tự ý dùng `os.walk` quét đĩa bị Guard chặn, dispatch worker với model alias không tồn tại (`claude-haiku-5-5`), hoặc dispatch subagent treo cứng 600s.
  3. **Làm tắc nghẽn farm:** Khiến phiên làm việc bị đứt quãng, gây ức chế nghiêm trọng cho User và làm mất thời gian gỡ rối.

## 2. Quy tắc cấu hình Fallback Chain
- **CẤM TUYỆT ĐỐI** đưa `gpt-5.6-luna`, `cx/gpt-5.6-luna-high`, hoặc bất kỳ biến thể Luna nào vào danh sách `fallback_providers` của Hermes.
- **Cấu hình chuẩn trong `config.yaml`:**
  ```yaml
  fallback_providers:
    - provider: custom:omni
      model: ag-gemini-pool-3
      base_url: http://192.168.110.123:20129/v1
      key_env: OMNIROUTE_API_KEY
  ```
- **Xử lý khi cạn quota Gemini:**
  - Nếu cả Primary (`omni-worker`) và Fallback (`ag-gemini-pool-3`) đều cạn quota: Hệ thống phải **fail-closed** và báo lỗi trực tiếp về pool quota để User nạp thêm tài khoản OAuth VIP (như `jinrakal`, `thanhdatbui19951`).
  - Thà dừng lại chờ nạp acc chứ tuyệt đối không fallback sang Luna.

## 3. Lệnh vận hành kiểm tra & dọn dẹp
```bash
# Kiểm tra fallback chain
hermes fallback list

# Xóa toàn bộ fallback chain nếu dính Luna
hermes fallback clear

# Thiết lập fallback an toàn
hermes config set fallback_providers '[{"provider": "custom:omni", "model": "ag-gemini-pool-3", "base_url": "http://192.168.110.123:20129/v1", "key_env": "OMNIROUTE_API_KEY"}]'
```
