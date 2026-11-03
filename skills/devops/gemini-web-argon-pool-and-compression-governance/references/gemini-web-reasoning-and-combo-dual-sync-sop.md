# Gemini-Web Reasoning Effort & Combo Dual-Sync SOP (2026-11-03)

## 1. Bản Chất Kiến Trúc Reasoning Slot Trên OmniRoute (:20129)
Mã nguồn backend `C:/Users/Kibe/OmniRoute/open-sse/executors/gemini-web.ts`:
- Google StreamGenerate không nhận thinking qua parameters thông thường mà nhận qua Slot 17 trong cấu trúc Protobuf payload `f.req`:
  ```typescript
  function resolveThinkingSlot(reasoningEffort?: string | null): unknown {
    switch (reasoningEffort?.trim().toLowerCase()) {
      case "high":   return [[0]];   // Kích hoạt Maximum Reasoning cho Gemini Web
      case "low":    return [[4]];
      case "none":   return null;
      default:       return [[2]];
    }
  }
  inner[17] = resolveThinkingSlot(reasoningEffort);
  ```
- **Lỗ hổng bỏ sót:** Trước đây cả `gate_b_planner.py` và `consult_advisor.py` chỉ gửi payload cơ bản (`model`, `messages`) mà quên truyền `"reasoning_effort": "high"`. Cần luôn đính kèm explicit `"reasoning_effort": "high"` khi gọi Gemini Web cho vai trò Planner hoặc Advisor.

## 2. Bẫy Lệch Tài Khoản Giữa 2 Combo Cùng Loại (Dual-Combo Desync)
- **Hiện tượng:** Cùng trỏ tới dàn nick Google AI Pro Web nhưng OmniRoute tồn tại 2 combo:
  - `gemini-web`: Tạo ngày 29/10 nạp đủ 20 acc (dùng cho Engine Nén context & `gate_b_planner.py`).
  - `gemini-web-argon-pool`: Tạo ngày 17/10 chỉ có 15 acc do sót 5 acc mở rộng (dùng cho Worker & `consult_advisor.py`).
- **Khắc phục:** Khi mở rộng pool account Google Web, BẮT BUỘC kiểm tra và đồng bộ đồng thời cả 2 bản ghi combo trong bảng `combos` (`C:/Users/Kibe/.omniroute/storage.sqlite`), tránh tình trạng một combo chạy 20 nick còn combo kia chỉ xoay quanh 15 nick.

## 3. Phân Định Rạch Ròi: Advisor vs Planner
- **Advisor (`consult_advisor.py`):** Tư vấn chiến lược kiến trúc, phân tích đa chiều (chạy song song Sol + Gemini + Claude), đầu ra là markdown text tự do.
- **Planner (`gate_b_planner.py`):** Soạn thảo hợp đồng sửa code O(1) phục vụ S1 Pipeline, chạy thác đổ (Gemini -> Claude -> Sol), đầu ra BẮT BUỘC là JSON thuần túy `{"edits": [...]}` và neo `old_string` duy nhất (`count == 1`). CẤM gộp 2 tool vì contract đầu ra xung đột.
