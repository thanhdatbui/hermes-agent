# Gmail Conversation-View Inbox Markers (Patch Contract O(1))

Áp dụng cho `_gmail_mailbox_state()` trong `D:/Taadaa/Tiktok_Reg/social_reg_v1.py`.

## Vấn đề
Khi Gmail mở thẳng vào màn hình chi tiết một thư (conversation view) thay vì
thread list / search bar, XML dump không chứa `open_search` hay
`conversation_list` → state bị đánh sai thành `no_inbox_marker`.

Dump thực tế (`fail_gmail_mailbox_wrong_app_..._104431.xml`, package
`com.google.android.gm`) chứa các node conversation view:
- `com.google.android.gm:id/subject_and_folder_view`
- `com.google.android.gm:id/sender_name`
- `com.google.android.gm:id/recipient_summary`
- `conversation_container`, `conversation_header`, `reply_button` / `forward_button`

## Fix O(1): thêm 3 markers vào nhánh inbox_marker
Trong `_gmail_mailbox_state()`, bên cạnh `open_search` /
`conversation_list` / `thread_list_view`, thêm:

```python
or "sender_name" in rid
or "recipient_summary" in rid
or "subject_and_folder_view" in rid
```

## Verify ad-hoc
- Load XML dump conversation view thật, gọi
  `_gmail_mailbox_state(xml_content, email=...)`.
- Kỳ vọng: `inbox_marker is True`, `reason == 'ok'`.
- Script verify tạm: prefix `hermes-verify-` dưới
  `C:\Users\Kibe\AppData\Local\Temp`, xóa sau khi chạy.
