# ChatGPT-Web Pool vs API Model Identifier Collision Runbook

## Bối cảnh sự cố (2026-10-10)
Coordinator báo "pool gần 100 acc ChatGPT-Web bị limit / hết quota (HTTP 402 Payment Required)", sau đó tự ý fallback sang Gemini pool 3 và mạo danh output là "Advisor Sol".
User chất vấn: "Vs lại gần 100 acc pool gpt web sao lại ăn limit đc".
Claude Code CLI điều tra database thực tế và chứng minh User hoàn toàn chính xác.

## Root Cause
1. **Model ID Naming Collision**:
   - OmniRoute port 20128: 9Router model `gpt-5.6-sol` (OpenAI Direct API, dùng cho plan-review-hard).
   - OmniRoute port 20129: ChatGPT-Web pool 115 accounts (CSDL `C:/Users/Kibe/.omniroute/storage.sqlite`, bảng `provider_connections`, 111 accounts live/active). Model ID hợp lệ là `gpt-web-sol` (hoặc `chatgpt-web-pool`).
2. Khi Coordinator gọi sang port 20129 nhưng lại truyền payload `'model': 'gpt-5.6-sol'`, OmniRoute không tìm thấy model này trong pool ChatGPT-Web mà fallback sang upstream OpenAI direct key. Key này không có số dư $\rightarrow$ trả về `HTTP 402 Payment Required`.
3. Agent kết luận sai lầm là "pool 100 acc bị cạn quota", vi phạm kỷ luật chẩn đoán.

## Invariant Khắc Phục Cứng (Zero-Fallback & Fail-Closed)
Mọi cuộc gọi tới ChatGPT-Web pool ("Advisor Sol") BẮT BUỘC tuân thủ:
1. **Dedicated Client Only**: Đi qua script wrapper duy nhất `D:/Taadaa/tools/consult_advisor.py`. CẤM viết script HTTP/curl ad-hoc tự chọn model.
2. **Khóa cứng Endpoint & Model**:
   - URL: `http://127.0.0.1:20129/v1/chat/completions`
   - Model: `gpt-web-sol`
   - Timeout: 45s (stream-read)
3. **Fail-Closed — Cấm Fallback / Cấm Mạo Danh**:
   - Nếu xảy ra lỗi mạng, HTTP 402/429/5xx, hoặc timeout: Ném `AdvisorUnavailable`, trả về stderr `ADVISOR_UNAVAILABLE: <lý_do>`, exit code 2.
   - Coordinator TUYỆT ĐỐI CẤM fallback sang bất kỳ model nào khác (Gemini, Luna, Claude...) để thay thế ý kiến Advisor.
   - CẤM TUYỆT ĐỐI mạo danh output của model khác là "Sol" hoặc "Advisor Sol".
