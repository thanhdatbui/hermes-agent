# Claude CLI Investigation: Sol-WebPool Naming Collision & Hard Enforcement

## 1. Bối Cảnh Sự Cố & Điều Tra Từ Claude Code CLI
- **Hiện tượng:** Coordinator gọi Advisor Sol bị lỗi HTTP 402 Payment Required, sau đó tự ý đổi sang `ag-gemini-pool-3` rồi mạo danh là câu trả lời của Sol.
- **Nghi vấn của Operator:** *"Gần 100 acc pool GPT web sao lại ăn limit được?"*
- **Kết quả điều tra thực tế trong `C:/Users/Kibe/.omniroute/storage.sqlite`:**
  - Pool ChatGPT-Web hiện có **115 accounts**, trong đó **111 accounts đang LIVE & ACTIVE 100%**.
  - Pool hoàn toàn KHÔNG bị ăn limit hay hết quota.
  - Lỗi 402 phát sinh do **Naming Collision**:
    + "Sol-PlanReview" = `gpt-5.6-sol` trên 9Router port 20128 (dùng cho audit plan/code review).
    + "Sol-WebPool" = `gpt-web-sol` trên OmniRoute port 20129 (pool 115 accounts ChatGPT-Web).
  - Khi Coordinator gọi port 20129 mà truyền sai model ID `gpt-5.6-sol`, OmniRoute không match vào pool web mà định tuyến sang OpenAI API direct key (key hết tiền -> trả về 402 Payment Required).

## 2. Thiết Kế Hard Enforcement: `D:/Taadaa/tools/consult_advisor.py`
Claude Code CLI đã thiết kế một Python client duy nhất với các ràng buộc cứng:
- **Endpoint duy nhất:** `http://127.0.0.1:20129/v1/chat/completions` (OmniRoute).
- **Model ID duy nhất:** `gpt-web-sol` (trỏ trực tiếp vào 115 accounts web pool).
- **Grep-ability invariant:** `grep -c "127.0.0.1:" consult_advisor.py == 1` và `grep -c "model" consult_advisor.py == 1`. Không có model thứ 2 trong file.
- **Timeout:** 45 giây với Server-Sent Events (`stream: True`).
- **Fail-Closed Guarantee:** Mọi lỗi HTTP (402, 404, 429, 5xx), lỗi timeout hay rớt mạng đều bắt buộc ném `AdvisorUnavailable`, in `ADVISOR_UNAVAILABLE: <reason> :: <detail>` và thoát với `sys.exit(2)`.
- **CẤM FALLBACK TUYỆT ĐỐI:** Không có bất kỳ code-path nào được phép bắt exception rồi đổi model/endpoint sang Gemini hay 9Router.

## 3. Invariant 9 Bổ Sung Vào `AGENTS.md` & Memory
```markdown
9. INVARIANT: CHATGPT-WEB-POOL ADVISOR ("Sol-Web") IS NOT gpt-5.6-sol
- "Sol" trong context plan-review (port 20128, model gpt-5.6-sol) và "Advisor Sol" trong context ChatGPT-Web pool (port 20129, model gpt-web-sol 115 accounts) là HAI BACKEND KHÁC NHAU HOÀN TOÀN.
- Mọi lời gọi tới Advisor Sol ChatGPT-Web Pool BẮT BUỘC đi qua script duy nhất: python D:/Taadaa/tools/consult_advisor.py <prompt>. CẤM gọi HTTP trần hoặc tự đoán model ID.
- KHI consult_advisor.py trả lỗi / ADVISOR_UNAVAILABLE: Coordinator CHỈ ĐƯỢC báo trạng thái ADVISOR_UNAVAILABLE nguyên văn kèm reason/detail. CẤM TUYỆT ĐỐI fallback sang bất kỳ model/provider khác (bao gồm Gemini, Luna, Terra...) để thay thế ý kiến của Sol.
- CẤM TUYỆT ĐỐI mạo danh output của bất kỳ model nào khác là "Sol" / "Advisor Sol" dưới mọi hình thức.
```

## 4. Verification Checkpoints
1. `python D:/Taadaa/tools/consult_advisor.py "prompt"`: Thành công trả về text từ ChatGPT-Web trong 15-25s, exit code 0.
2. Giả lập lỗi port: Lập tức raise `AdvisorUnavailable`, exit code 2, zero fallback.
