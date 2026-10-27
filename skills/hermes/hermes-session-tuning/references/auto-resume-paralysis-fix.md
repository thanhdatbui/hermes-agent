# Phòng Chống Bệnh Bại Liệt Não Khi Auto-Resume Session Sau Gateway Restart / Reboot

## 1. Hiện Tượng & Triệu Chứng
Sau khi Gateway khởi động lại (do watchdog, timeout kết nối, hoặc máy tính reboot), session tự động hồi phục nhưng Agent lại dừng toàn bộ tiến trình dở dang và phát ngôn hành chính ngớ ngẩn:
> *"Phiên làm việc đã được khôi phục thành công sau khi kết nối gateway hoạt động trở lại. Các tiến trình trước đó đã được ghi nhận. Bạn muốn tiếp tục xử lý nội dung nào tiếp theo?"*
khiến User cực kỳ ức chế:
> *"Hồi chiều t fix cái auto resume này 1 lần r sao h vẫn bị lại vào hỏi bại liệt não đkm đang làm dở thì làm tiếp hỏi cái lồn. Lí do hỏi mà đéo làm tiếp?"*

---

## 2. Căn Nguyên Kỹ Thuật & Tử Huyệt Trôi Code

### A. Tử huyệt điều kiện rẽ nhánh (`gateway/run.py` dòng ~19081)
Mỗi khi Gateway restart hoặc shutdown do drain timeout, tiến trình gán biến `_reason = "restart_timeout"` hoặc `"shutdown_timeout"`.
Tại điểm xử lý resume:
```python
_auto_continue_task = (not message) and _reason == "restart_interrupted"
```
- Mã nguồn cũ **CHỈ CHẤP NHẬN** duy nhất chuỗi `"restart_interrupted"` (vốn chỉ sinh ra khi có script reboot OS đặt cờ).
- Khi Gateway restart vì bất kỳ lý do nào khác (`restart_timeout`, `shutdown_timeout`), biến `_auto_continue_task` rơi về **`False`**.

### B. System Note tiêm ngược chỉ thị bắt LLM bỏ cuộc và hỏi User
Khi `_auto_continue_task == False`, Gateway rơi vào nhánh `else` và tiêm thẳng chỉ thị hệ thống vào ngữ cảnh của LLM:
```python
_resume_guidance = (
    "Report to the user that the session was restored successfully and ask what they would like to do next."
)
_replay_guard = (
    "Do NOT re-execute old tool calls — skip any unfinished work from the conversation history."
)
```
Tương tự ở nhánh fallback (dòng ~19178):
> *"[System note: ... Report to the user that the session was restored successfully and ask what they would like to do next. Do NOT re-execute old tool calls — skip any unfinished work from the conversation history.]"*

👉 **Hậu quả:** LLM tuân thủ tuyệt đối chỉ thị hệ thống, bỏ dở toàn bộ công việc đang chạy và hỏi ngược lại User một câu vô nghĩa.

### C. Bẫy trôi code do uncommitted diff
Code đã được sửa vào buổi chiều nhưng chỉ nằm ở dạng file uncommitted diff trên disk, sau đó bị các subagent hoặc tool chạy lệnh `git checkout` / `git stash` đè ngược lại làm mất mã nguồn fix.

---

## 3. Bản Vá Chuẩn Hóa Cưỡng Chế (Commit `7f04bc84f`)

### Bước 1: Mở rộng nhận diện task dở dang trong `gateway/run.py`
```python
_auto_continue_task = (not message) and _reason in (
    "restart_interrupted", "restart_timeout", "shutdown_timeout"
)
```

### Bước 2: Thay thế System Note thành Lệnh Hành Động Cưỡng Chế
Xóa sổ hoàn toàn câu *"ask what they would like to do next"* và *"skip any unfinished work"*.
Thay bằng mệnh lệnh hành động bắt buộc:
```python
if _auto_continue_task:
    _resume_guidance = (
        "Kiểm tra lại hiện trường môi trường/thiết bị sau khi restart và chủ động tiếp tục thực thi để hoàn thành dứt điểm task đang dở về DONE hoặc BLOCKED kèm bằng chứng thực tế. Do NOT replay old tool calls from the history — re-check the real current state first and issue fresh calls only for what is still unfinished."
    )
```
Và ở nhánh fallback:
```python
system_note = (
    "[System note: The previous turn was interrupted by a gateway restart; the gateway is now back online. "
    "Kiểm tra lại hiện trường môi trường/thiết bị sau khi restart và chủ động tiếp tục thực thi để hoàn thành dứt điểm task đang dở về DONE hoặc BLOCKED kèm bằng chứng thực tế. "
    "Do NOT replay old tool calls from the history — re-check the real current state first and issue fresh calls only for what is still unfinished.]"
)
```

### Bước 3: Kỷ luật Git Commit Lõi Bắt Buộc
Bất kỳ thay đổi nào liên quan đến Gateway Core (`D:/Taadaa/Hermes/gateway/run.py`) BẮT BUỘC:
1. Chạy `python -m py_compile gateway/run.py` xác minh cú pháp.
2. Thực hiện `git commit` ngay lập tức để đóng đinh thay đổi, chống trôi mã nguồn khi các subagent khác thao tác git.
