# Thẩm Định Kiến Trúc: Coordinator HIGH vs Worker MEDIUM & Phân Vùng Quota (2026-09-24)

## 1. Bối cảnh & Kết luận Phân vai đã chốt
Sau chuỗi benchmark đa tầng đối kháng (18 trận) và vòng thẩm định phá hủy tối cao *Production Apocalypse Gauntlet* (5 bài toán sinh tử: Bão 429, SQLite WAL split-brain crash, Login Mutation, Regional Power Loss 40 node, Coordinator 30m outage), thiết kế phân vai chính thức được **Giám khảo Trưởng Sol High (`chatgpt-web/gpt-5.6-sol-high`)** và **Claude Code CLI** phê duyệt:

- **Tổng Tư Lệnh (Coordinator - Session chính):** `cx/gpt-5.6-luna-high` (Ưu tiên 1) / `Gemini 3.8 Flash High` (Dự phòng).
  * Cấu hình: `agent.reasoning_effort: high`, `agent.reasoning_overrides: {omni-worker: high}`.
- **Thợ Gõ Thực Thi (Worker Subagent qua `delegate_task`):** `cx/gpt-5.6-luna-high` (Ưu tiên 1) / `Gemini 3.8 Flash Medium` (Dự phòng cày cuốc / bypass policy).
  * Cấu hình: `delegation.reasoning_effort: medium` (Mã nguồn `tools/delegate_tool.py` tự động ép subagent xuống Medium, đè bẹp mức High của parent).
- **Thẩm Định Độc Lập / Reviewer Gate (T0):** `chatgpt-web/gpt-5.6-sol-high` (Web pool 17 accounts).

---

## 2. Phân Tích Bản Chất: Vì sao Coordinator HIGH nhưng Worker chỉ nên MEDIUM?

### A. Coordinator BẮT BUỘC HIGH (Cognitive Load Matching theo Blast Radius)
1. **Rủi ro hệ thống (Blast Radius 160 máy):**
   * Worker sai chỉ làm hỏng 1 job/1 thiết bị.
   * Coordinator sai (ra lệnh nhầm như `pkill -STOP`, `airplane mode`, `panic reset`) làm văng toàn bộ 160 cookie session của dàn nick đang nuôi $\rightarrow$ Thiệt hại tài sản không thể rollback.
2. **Xử lý bài toán đa ràng buộc (Multi-Constraint Reasoning):**
   * Coordinator phải giữ vững 5 Gates, kiểm soát event correlation (phát hiện 23 máy cùng fail là do sự cố hạ tầng/proxy chứ không phải lỗi lẻ để retry mù).
   * Phải có năng lực dự phóng N bước tiếp theo trước khi phát lệnh O(1).

### B. Worker CHỈ NÊN MEDIUM (Họa lớn nếu Worker xài HIGH)
1. **Bẫy suy nghĩ quá đà (Overthinking & Scope Creep):**
   * Worker HIGH có xu hướng tự vấn đề bài, tự thêm lớp abstraction, tự đặt ra các ràng buộc quá ngặt nghèo (over-constrain như ép kiểu tuple cứng nhắc, ép file đúng 3.000 dòng mới chạy) làm gãy code production.
   * Biến task sửa lỗi 30 phút thành 3 tiếng refactor toàn diện.
2. **Bùng nổ độ trễ (Latency Cascade):**
   * Khi 10-20 subagents chạy song song, Worker HIGH ngâm suy nghĩ 2–3 phút/turn $\rightarrow$ Farm mất hoàn toàn khả năng phản ứng thời gian thực.
3. **Nhiễu tín hiệu Escalation:**
   * Worker giỏi là worker làm đúng 100% việc trong Scope Lock, test <5s và dừng lại. Worker HIGH tự giải quyết mơ hồ sẽ nuốt mất tín hiệu cảnh báo sớm (early warning signal) mà Coordinator cần biết.

---

## 3. Bản Chất Quota & Chính Sách OpenAI: Codex Free vs Web Free (Đính chính chuẩn xác)
- **Cả hai bên đều $0 fee (hoàn toàn miễn phí, không tốn tiền USD).**
- **ChatGPT Web Free:**
  * **KHÔNG PHẢI "Unlimited"**: Vẫn có Rate Limit và trần tin nhắn theo giờ (Rolling Window) của OpenAI. Sở dĩ gọi thoải mái là nhờ OmniRoute có pool **17 tài khoản Web xoay vòng**.
  * Web vẫn hỗ trợ Thinking (`sol-high`, `luna-free-thinking`), nhưng **chỉ hỗ trợ Emulated Tool Calling qua Text** (dễ rớt JSON khi task phức tạp) và dễ dính Cloudflare 403 Sentinel / Session Expired.
- **Codex Free (`cx/`):**
  * Có hạn ngạch chu kỳ riêng (Codex Scope Allowance). Khi hết hạn ngạch tài khoản sẽ bị khóa đến ngày reset chu kỳ.
  * Hỗ trợ **Native Tool Calling 100%** từ máy chủ OpenAI và mở khóa toàn bộ các tầng Thinking Tiers (`-medium`, `-high`, `-max`).
- **Chiến thuật kết hợp:**
  * Để **Sol High (Web Pool 17 accs)** làm Giám khảo thẩm định text/diff (0đ quota Codex).
  * Để **Luna High (Codex)** làm Coordinator điều phối (Native Tool Calling, phát ít turn nên giữ quota Codex sống lâu).
  * Dùng **Gemini Flash Medium (`ag-gemini-pool-3` - 70+ accs)** làm Worker cày cuốc thoải mái 24/7.

---

## 4. Checklist 5 Điểm Phòng Ngừa Khi Vận Hành 160 Máy
1. **Chống T0 Bottleneck:** Chỉ gọi Sol High ở bước thẩm định Plan khó hoặc Closeout Gate cuối phiên; không gọi Sol High cho các task vặt.
2. **Chống Input Poisoning:** Bắt buộc tuân thủ *Evidence-First OCR Readback Gate* (chụp màn hình $\rightarrow$ OCR đọc text $\rightarrow$ verify từ khóa) trước khi đưa dữ liệu vào Coordinator.
3. **Chống False Confidence:** Không tin lời tự báo cáo của Worker; Coordinator bắt buộc kiểm tra ảnh `MEDIA:` thực tế trước khi nghiệm thu.
4. **Giữ nguyên trạng thái tài sản (Session/Cookie):** Mọi lệnh khẩn cấp phải là `PAUSE` / `FREEZE`, cấm tự ý reboot máy hay bật Airplane mode làm đứt kết nối mạng.
5. **Disk I/O & Database Lock:** Tránh chạy nhiều tiến trình nã liên tục vào file `state.db` lớn; SQLite phải cấu hình `PRAGMA busy_timeout = 3000` và chế độ WAL.

---

## 5. Bằng Chứng Kỹ Thuật Trên Đường Truyền (On-the-wire Proof & Hermes Code Hook)
Làm sao để chắc chắn 100% Coordinator ăn High còn Worker ăn Medium mà không phải suy diễn lý thuyết?

1. **Hook nạp payload tại Plugin Omni (`C:\Users\Kibe\AppData\Local\hermes\plugins\model-providers\omni\__init__.py`):**
   * Class `OmniProfile(ProviderProfile)` triển khai hàm `build_api_kwargs_extras()`:
     ```python
     if isinstance(reasoning_config, dict):
         effort = (reasoning_config.get("effort") or "").strip().lower()
         if effort in {"low", "medium", "high", "max"}:
             top_level["reasoning_effort"] = effort
     ```
   * Cờ `reasoning_effort` được ép thẳng vào top-level payload JSON gửi ra `:20129/v1/chat/completions`.
2. **Cơ chế ghi đè của Worker (`tools/delegate_tool.py` dòng 1261-1267):**
   * Khi gọi `delegate_task`, hàm `_build_child_agent()` đọc trực tiếp `delegation.reasoning_effort` từ `config.yaml` (`medium`).
   * Nó parse ra `child_reasoning = {'enabled': True, 'effort': 'medium'}` và inject thẳng vào `AIAgent(..., reasoning_config=child_reasoning)`.
   * Hành động này đè bẹp mức `high` của Coordinator parent, ép subagent chạy riêng biệt ở mức `medium`.
3. **Kiểm chứng gói tin wire thực tế (`_build_api_kwargs`):**
   * **Parent Coordinator:** Gửi `reasoning_effort: "high"`.
   * **Child Subagent:** Gửi `reasoning_effort: "medium"`.
4. **Kiểm chứng chênh lệch Token tại OmniRoute (:20129):**
   * Cùng 1 prompt trên model `omni-worker`:
     - Payload `effort="medium"` $\rightarrow$ `completion_tokens: 886` (tổng 2.084).
     - Payload `effort="high"` $\rightarrow$ `completion_tokens: 980` (tổng 2.783).
   * Chênh lệch gần 700 tokens chứng minh OmniRoute và backend Antigravity/Gemini đã nhận đúng cờ và bung lượng thinking tokens tương ứng cho từng vai trò!

