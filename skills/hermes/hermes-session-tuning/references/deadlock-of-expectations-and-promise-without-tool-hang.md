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

### Chốt chặn 2: Thiết kế O(1) One-Shot Loop Nudge (Đồng thuận Claude Sonnet 5.5 - Chống Over-engineering & Chống Bại liệt)

Thay vì viết thêm file hook rườm rà hay regex forest cồng kềnh, Claude Sonnet 5.5 tư vấn giải pháp O(1) tối giản đặt ngay tại điểm exit duy nhất của `conversation_loop.py`:

```python
# Cấp module trong conversation_loop.py
_PROMISE_MARKERS = ("đang ", "để em", "em sẽ", "i'll ", "i will ", "let me ", "i'm going to", "now ")
_PROMISE_NUDGE = (
    "[System] Your last message promised an action but emitted NO tool call. "
    "If you intend to act, emit the tool call NOW. If you are done or need the user, "
    "answer plainly with no promise of future work."
)

def _is_promise_without_tool(text: str) -> bool:
    tail = (text or "").strip()[-160:].lower()  # O(1): chỉ xét 160 ký tự đuôi
    # Nếu câu kết thúc bằng "?" -> User clarify / hỏi ý kiến -> KHÔNG CHẶN
    return bool(tail) and not tail.endswith("?") and any(m in tail for m in _PROMISE_MARKERS)

# Trong vòng lặp while của conversation_loop (per user turn: nudged = False):
if finish_reason == "stop" and not tool_calls:
    if not nudged and _is_promise_without_tool(assistant_text):
        nudged = True
        messages.append({"role": "user", "content": _PROMISE_NUDGE, "synthetic": True})
        continue  # Ép chạy thêm đúng 1 nhịp nữa để nhả tool call thật

    if nudged and _is_promise_without_tool(assistant_text):
        # Nếu đã nhắc 1 lần mà model vẫn lì lợm hứa mồm không gọi tool:
        # BẮT BUỘC gắn nhãn cảnh báo đỏ để User biết là agent đã dừng, cấm im lặng chờ nhau!
        assistant_text += "\n\n⚠️ [Agent stopped without acting - reply to retry]"
    break
```

**Tại sao cơ chế này chuẩn O(1) & chống bại liệt:**
1. **Hard cap 1 lần/turn (`nudged` local):** Không thể rơi vào vòng lặp xoay mòng mòng (spin loop). Nhịp thứ 2 chấp nhận thoát vô điều kiện.
2. **Không over-engineer:** Kiểm tra tuple substring trên 160 ký tự đuôi, không regex, không hook rườm rà.
3. **Không bại liệt:** Tin nhắn kết thúc bằng `?` (hỏi User, làm rõ yêu cầu) lọt qua 100%. Nếu model lì lợm không gọi tool, Hermes gắn nhãn cảnh báo đỏ công khai để User biết đường can thiệp, triệt tiêu hoàn toàn khả năng im lặng treo qua đêm.

### Chốt chặn 3: Nâng cấp `hermes-stale-watchdog`
- Kiểm tra session có tin nhắn cuối cùng là câu hứa hẹn hành động mà không có tiến trình nền / subagent nào đang active quá 5 phút.
- Nếu phát hiện: Tự động đánh dấu `STALE_PROMISE_DETECTED` và gửi alert nhắc nhở hoặc ép restart session thay vì để đơ qua đêm.
