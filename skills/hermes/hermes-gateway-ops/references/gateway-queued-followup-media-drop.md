# Hermes Gateway Queued Follow-Up Media Drop Trap

Ngày ghi nhận: 20/09/2026.
Tác nhân: Hermes Gateway Agent Dispatch Loop (`gateway/run.py`).

---

## 1. HIỆN TƯỢNG VÀ TRIỆU CHỨNG
- Người dùng nhận được báo cáo văn bản đầy đủ kèm dòng cú pháp `MEDIA:<path_anh>` hoặc dòng chữ mô tả nghiệm thu, nhưng **hoàn toàn không có hình ảnh/media nào được đính kèm** trên Telegram.
- Tần suất: Cứ khoảng 7–8 lượt chat có gửi media thì gặp 1 lượt bị mất ảnh ("Gửi ảnh lỗi r").
- Log Gateway (`gateway.log`):
  - Xuất hiện thông báo:
    `Queued follow-up for session <session_key>: final stream delivery not confirmed; sending first response before continuing.`
  - Ngay sau đó là `adapter.send(chat_id, first_response)` gửi text thô, nhưng hoàn toàn không có log `[Telegram] Sending media group of 1 photo(s)`.

---

## 2. CƠ CHẾ GỐC RỄ (ROOT CAUSE)
1. Trong luồng bình thường (`_process_message_background` hoặc `_handle_message_with_agent`), sau khi stream hoặc sau khi agent hoàn tất lượt chat, Gateway luôn gọi:
   - `BasePlatformAdapter.extract_media(response)` để bóc tách các tag `MEDIA:<path>`.
   - `adapter.send(...)` gửi phần văn bản.
   - `adapter.send_multiple_images(...)` hoặc `_deliver_media_from_response(...)` để gửi các tệp đính kèm.
2. Tuy nhiên, khi có **subagent nền hoàn tất** (`[ASYNC DELEGATION BATCH COMPLETE]`) hoặc **watchdog notification** gửi vào hàng đợi đúng lúc turn hiện tại vừa sinh xong `first_response`:
   - Gateway kích hoạt nhánh xử lý **Queued follow-up** trong `_run_agent_inner` (khoảng dòng 20130 trong `gateway/run.py`).
   - Nhánh này chỉ gọi:
     ```python
     await adapter.send(source.chat_id, first_response, metadata=_status_thread_metadata)
     ```
     để xả nhanh text của turn trước trước khi đệ quy chạy tiếp tin nhắn trong hàng đợi.
   - Nhánh này **hoàn toàn bỏ quên việc bóc tách và gửi media đính kèm**, khiến toàn bộ ảnh/video của lượt đầu bị nuốt mất hoặc chỉ hiển thị dưới dạng chuỗi text thô.

---

## 3. GIẢI PHÁP KHẮC PHỤC TRIỆT ĐỂ
Bổ sung đoạn code gửi media ngay sau khối gửi `first_response` trong `gateway/run.py`:

```python
if first_response and adapter:
    try:
        _ev = pending_event or MessageEvent(
            platform=source.platform,
            event_type=EventType.MESSAGE,
            source=source,
            text=first_response,
        )
        await self._deliver_media_from_response(first_response, _ev, adapter)
    except Exception as _med_err:
        logger.warning("Failed to deliver media before queued message: %s", _med_err)
```

**Kỷ luật đồng bộ 3 vị trí:**
1. Runtime: `%LOCALAPPDATA%\hermes\hermes-agent\gateway\run.py`
2. Dual-runtime venv: `%LOCALAPPDATA%\hermes\hermes-agent\venv\Lib\site-packages\gateway\run.py`
3. Repository: `D:\Taadaa\Hermes\gateway\run.py`
Sau đó nạp lại bằng `delayed-restart.ps1`.
