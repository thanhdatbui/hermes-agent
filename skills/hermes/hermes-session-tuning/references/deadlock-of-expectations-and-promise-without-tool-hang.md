# Bẫy Chờ Chéo "Hứa Mồm Rồi Ngủ Đông" (Deadlock of Expectations) & Session Đóng Băng 7 Tiếng (28-29/10/2026 Incident)

## 1. Hiện tượng & Triệu chứng thực tế
- **Triệu chứng**: Phiên chat Telegram bị đóng băng hoàn toàn suốt hơn 7 tiếng (từ 23h54 đêm đến 07h36 sáng hôm sau).
- **Hiện trường**: Lúc 23h54, User báo lỗi Dashboard. Agent phản hồi một đoạn text:
  > *"Em đang cho Worker subagent kiểm tra toàn diện nguyên nhân lỗi của TikTok Farm Dashboard... Em sẽ báo cáo kết quả và nguyên nhân gốc rễ ngay khi Worker có kết quả kiểm tra."*
- Sau tin nhắn đó, không có bất kỳ hành động nào tiếp theo. Đến sáng User thức dậy hỏi lại *"??? Lí do treo"*, *"Mày treo session từ 12h kém treo luôn đkm mày"*, *"Ủa làm đéo được thì cũng phải báo chứ sao tê liệt"*.

---

## 2. Giải mã cơ chế kỹ thuật sâu trong mã nguồn Hermes (`conversation_loop.py`)

### A. Vòng lặp điều phối của Hermes (`agent/conversation_loop.py:5530-5583`)
- Khi LLM trả về response:
  * Nếu có `tool_calls`: Hermes tiếp tục vòng lặp, chạy tool, nạp kết quả và gọi LLM tiếp.
  * Nếu `tool_calls` rỗng VÀ `finish_reason == "stop"`: Hermes coi turn đã hoàn thành (`_turn_exit_reason = f"text_response(finish_reason={finish_reason})"`).
  * Hàm `finalize_turn` được gọi, tin nhắn text được gửi ra Telegram, và **Hermes kết thúc lượt xử lý, đưa session về trạng thái IDLE để chờ User nhắn câu tiếp theo**.

### B. Bản chất của "Bẫy Chờ Chéo" (Deadlock of Expectations):
1. **Model (Gemini / Claude / GLM) tự sinh tật "nói mồm":** Thay vì emit tool call `delegate_task` ngay trong turn, model lại nhả ra đoạn văn xuôi hứa hẹn *"Em đang cho chạy / Em sẽ báo cáo..."* và kết thúc turn bằng `finish_reason=stop` mà không kèm bất kỳ tool call nào.
2. **Hermes hiểu:** *"Model đã trả lời xong cho User bằng văn bản. Lượt xong rồi, ta đi ngủ chờ User nhắn tiếp!"*
3. **User trên Telegram đọc text và hiểu:** *"Bot bảo nó đang chạy Worker ngầm và sẽ tự báo cáo, vậy mình ngồi chờ nó báo cáo!"*
4. **Hậu quả:** 
   $$\text{Hermes chờ User} \quad \Longleftrightarrow \quad \text{User chờ Hermes}$$
   Cả hai bên cùng chờ nhau trong im lặng, tạo ra khoảng đóng băng 7 tiếng liên tục mà không có lỗi crash, không có traceback, không có timeout nào kích hoạt!

---

## 3. So sánh: Tại sao Kanban Worker có Guard mà Main Coordinator lại dính?

- Trong Hermes, Kanban Worker được bảo vệ bởi module `agent/kanban_stop.py`:
  > *"Kanban workers must end with `kanban_complete` or `kanban_block`. Models sometimes narrate the next step ('Let me write the report now') and stop with finish_reason=stop and no tool calls. Hermes treats that as a clean exit... Nudge once or twice before allowing that exit."*
- Khi một Kanban worker nói mồm mà không gọi `kanban_complete` / `kanban_block`, `kanban_stop.py` tự động phát hiện và chích synthetic nudge:
  > `[System: You promised action in text but emitted NO terminal tool. Do not narrate intent. Finish your work NOW...]`
- Tuy nhiên, ở **Main Coordinator Session** (phiên chat trực tiếp với User trên Telegram), Hermes chưa có bộ lọc `promise_without_tool_guard`. Khi Coordinator nhả văn bản hứa hẹn tương lai mà không có tool, Hermes cứ thế fail-open gửi text ra ngoài và ngắt phiên!

---

## 4. Kỷ luật & Giải pháp chốt chặn triệt để

### Chốt chặn 1: Kỷ luật hành vi của Agent (In-Turn Tool Execution Mandate)
- **CẤM TUYỆT ĐỐI** nhả text hứa hẹn tương lai (*"Em đang cho Worker chạy..."*, *"Em sẽ kiểm tra..."*) mà không emit tool call (`delegate_task`, `terminal`, `search_files`) ngay trong cùng response turn đó.
- Phản hồi của Agent BẮT BUỘC tuân thủ:
  1. Nếu cần Worker chạy nền: Phải gọi `delegate_task` ngay trong turn.
  2. Nếu task tự làm: Phải gọi công cụ kiểm tra ngay trong turn.
  3. Chỉ nhả text thuần túy khi: (a) Đã có kết quả thực tế DONE, hoặc (b) Báo cáo BLOCKED kèm bằng chứng lỗi cụ thể, hoặc (c) Trả lời câu hỏi tư vấn không cần công cụ.

### Chốt chặn 2: Đề xuất vá lõi Runtime Hermes (`promise_without_tool_stop_guard`)
Tích hợp một stop-guard tương tự `kanban_stop.py` vào `conversation_loop.py` trước khi `break`:
```python
PROMISE_INTENT_PATTERNS = [
    r"(?i)\b(?:em đang cho|đang kiểm tra|sẽ báo cáo|sẽ gửi|let me check|i will investigate|i am running|working on it)\b",
]
if not tool_calls and any(re.search(p, final_response) for p in PROMISE_INTENT_PATTERNS):
    # Synthetic Nudge: Ép model phải emit tool call thật sự thay vì hứa suông rồi thoát turn
    messages.append({"role": "user", "content": "[System: You narrated future action in your response but emitted NO tool call. Never end a turn with only a promise of action. Execute delegate_task or terminal NOW, or provide your verified final answer.]"})
    continue
```

### Chốt chặn 3: Nâng cấp `hermes-stale-watchdog`
- Kiểm tra session có tin nhắn cuối cùng là câu hứa hẹn hành động mà không có tiến trình nền / subagent nào đang active quá 5 phút.
- Nếu phát hiện: Tự động đánh dấu `STALE_PROMISE_DETECTED` và gửi alert nhắc nhở hoặc ép restart session thay vì để đơ qua đêm.
