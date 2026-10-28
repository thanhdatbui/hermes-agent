# Cạm Bẫy Auto-Resume Trong Forum Topics / Threads vs DM (Sender Prefix & Passive Prompt Trap)

## Hiện Tượng Lệch Pha (Desync Behavior)
Sau khi Restart Gateway hoặc khởi động lại máy:
- **Session ở DM (Chat riêng 1-1):** Tự động resume và chủ động thực thi tiếp công việc đang dở về DONE/BLOCKED bình thường.
- **Session ở Forum Topics / Group Threads (như topic `[BATCH ALERT]` Telegram):** Không chịu làm tiếp mà nhảy vào lải nhải hỏi người dùng: *"Phiên làm việc đã được khôi phục thành công... Anh muốn em tiến hành theo hướng nào tiếp theo?"*.

## Nguyên Nhân Gốc Rễ Trong Kiến Trúc Gateway (`gateway/run.py`)

### 1. Bẫy Sender Prefix Trên Non-DM (`is_shared_multi_user_session`)
Khi gateway khởi động lại, `_schedule_resume_pending_sessions()` bắn ra một sự kiện nội bộ `MessageEvent(text="", internal=True)` để kích hoạt lượt chạy tiếp theo cho session dở dang.

Tuy nhiên, hàm `_prepare_inbound_message_text()` trước đó chỉ kiểm tra:
```python
if _is_shared_multi_user and source.user_name:
    message_text = f"[{source.user_name}] {message_text}"
```
- Trong **DM**: `source.chat_type == "dm"` $\rightarrow$ `_is_shared_multi_user` là `False`. `message_text` giữ nguyên chuỗi rỗng `""`.
- Trong **Forum Topic / Thread**: `source.thread_id` có giá trị và `chat_type != "dm"` $\rightarrow$ `_is_shared_multi_user` là `True`. Chuỗi rỗng `""` bị bọc thành `"[User Name] "`!

### 2. Sụp Đổ Điều Kiện `_auto_continue_task`
Tại `_run_agent_inner()`:
```python
_auto_continue_task = (not message) and _reason in (
    "restart_interrupted", "restart_timeout", "shutdown_timeout"
)
```
Do `message` bị dính chuỗi `"[User Name] "`, `(not message)` bị đánh giá thành `False`.
Gateway tưởng rằng có tin nhắn mới thật từ người dùng gửi tới!

### 3. Cạm Bẫy Prompt Thụ Động (`else:` & `_replay_guard`)
Khi `message` không rỗng, luồng rơi vào nhánh:
```python
if message:
    _resume_guidance = "Address the user's NEW message below FIRST and focus on what the user is asking now."
    _replay_guard = "Do NOT re-execute old tool calls — skip any unfinished work from the conversation history."
```
Hoặc nếu `_reason` rơi vào nhánh `else`:
```python
else:
    _resume_guidance = "Report to the user that the session was restored successfully and ask what they would like to do next."
    _replay_guard = "Do NOT re-execute old tool calls — skip any unfinished work from the conversation history."
```
Model nhìn thấy chỉ thị: "Bỏ qua công việc cũ dở dang và hỏi người dùng muốn làm gì tiếp theo", trong khi tin nhắn mới lại chỉ là cái tên `[User Name]` trống không. Kết quả là model ngoan ngoãn làm theo hướng dẫn thụ động và quay ra hỏi user.

---

## Chuẩn Hóa Khắc Phục (Hardened Standard)

1. **Khóa Chặn Sender Prefix trên Synthetic Events:**
   Trong `_prepare_inbound_message_text()`:
   ```python
   if (
       _is_shared_multi_user
       and source.user_name
       and (event.text or "").strip()
       and not getattr(event, "internal", False)
   ):
       message_text = f"[{source.user_name}] {message_text}"
   ```
   Tuyệt đối không bao giờ chèn `[{source.user_name}]` khi nội dung tin nhắn rỗng hoặc sự kiện mang cờ `internal=True`.

2. **Bóc Tách Tin Nhắn Người Dùng Thật Bằng Regex:**
   Tại `_run_agent_inner()`:
   ```python
   _has_real_user_message = bool(
       message
       and isinstance(message, str)
       and not re.match(r"^(\[[^\]]+\]\s*)*$", message.strip())
   )
   if not _has_real_user_message:
       message = ""
   _auto_continue_task = not _has_real_user_message
   ```
   Nếu chuỗi tin nhắn chỉ chứa sender tag hoặc khoảng trắng, tự động ép về chuỗi rỗng `""` và kích hoạt chế độ chủ động `_auto_continue_task = True`.

3. **Tiêu Diệt Hoàn Toàn Prompt Thụ Động:**
   Xóa bỏ triệt để mọi câu chữ *"Report to the user that the session was restored successfully and ask what they would like to do next"* và *"skip any unfinished work"* trong toàn bộ codebase Gateway. Mọi phiên resume khi không có tin nhắn mới từ user đều phải nhận chỉ thị hành động dứt điểm về `DONE` hoặc `BLOCKED`.

---

## 4. Bẫy Đồng Bộ 3 Vị Trí Khi Vá Lỗi Gateway (Triple-Location Sync Trap)

### Tại sao sửa xong, commit Git rồi mà Gateway restart vẫn bị lỗi cũ?
Trên Windows, tiến trình Gateway chạy ngầm (`pythonw.exe -m hermes_cli.main gateway run`) được cấp biến môi trường `PYTHONPATH` trỏ vào `venv/Lib/site-packages`.

Tiến trình Gateway nạp `gateway.run` **trực tiếp từ `site-packages`**, KHÔNG nạp từ repository git!
Nếu phiên làm việc chỉ sửa code và commit trên repo git `gateway/run.py` mà quên đồng bộ vào môi trường runtime, khi Gateway restart nó vẫn tiếp tục nạp file cũ từ ngày trước trong `site-packages`.

### Quy trình chuẩn bắt buộc khi vá Gateway (`gateway/run.py`):
1. **Sửa & Commit trong repo:** `D:/Taadaa/Hermes/gateway/run.py`
2. **Đồng bộ ngay sang 2 vị trí runtime:**
   - Source package runtime: `hermes-agent/gateway/run.py`
   - Venv package runtime: `venv/Lib/site-packages/gateway/run.py`
3. **Pre-flight Compile & Focused Test:**
   ```bash
   python -m py_compile "$LOCALAPPDATA/hermes/hermes-agent/venv/Lib/site-packages/gateway/run.py" "$LOCALAPPDATA/hermes/hermes-agent/gateway/run.py" "D:/Taadaa/Hermes/gateway/run.py"
   pytest "D:/Taadaa/Hermes/tests/test_session.py" -v
   ```
4. **Hậu kiểm sau khi Restart Gateway:**
   Dùng Python inspect module đã nạp trong RAM để kiểm chứng chuỗi lỗi đã biến mất hoàn toàn:
   ```python
   import gateway.run, inspect
   src = inspect.getsource(gateway.run)
   assert 'ask what they would like to do next' not in src
   ```
