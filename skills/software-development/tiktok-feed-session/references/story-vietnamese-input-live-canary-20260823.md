# Live Story Quick Reaction Vietnamese Input & Canary Verification (2026-08-23)

## Hiện trường lỗi máy 56
- **Thiết bị:** Máy 56 (`ce0516055108a70e01`), tài khoản `tuantuannguyen56` (Row 1).
- **Hiện tượng:** TikTok mở video dạng Story, hiển thị panel 8 emoji phản hồi nhanh (`😎, 🤣, 😳, 🥰, ❤️, 👏, 🔥, 🎆`) và trường soạn tin nhắn có placeholder tiếng Việt: `Nhắn tin cho [user]...`. Bàn phím ảo hệ thống tự động bung lên chiếm nửa dưới màn hình (Y: 1000 - 1920).
- **Lỗi cũ:** `_is_story_input_node` chỉ nhận diện resource-id `story_reply_input` hoặc `story_quick_reply`. Trên UI thực tế của máy 56, resource-id là `input_box` nằm dưới container `e_4`, khiến hàm trả về `False` -> classifier trả về `unknown TikTok state` -> recovery swipe 2 lần trúng bàn phím ảo nên dừng phiên giữ hiện trường.

## Bản vá logic
1. Mở rộng `_is_story_input_node` trong `python_runner/flows/benign_popup_registry.py`:
   - Kiểm tra `_is_input_node(el)`.
   - Loại trừ `_DM_EXCLUSION_TERMS` (`message_input`, `chat_room`, `im_title_bar`, `im_root`, `chat_input`).
   - Nhận diện `_STORY_CONTEXT_RESOURCE_TERMS` HOẶC node text/content-desc chứa marker tiếng Việt `nhắn tin cho`, `gửi tin nhắn cho`.
2. Mở rộng `_scope_has_story_composer`: Chấp nhận scope khi có bất kỳ direct story input node nào bên trong.

## Lệnh Live Canary Verification bắt buộc
Khi hoàn tất code fix và unit test, bắt buộc chạy lệnh canary trên máy lỗi trước khi chốt phiên:
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 56 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
Tiêu chuẩn pass:
- Log JSONL: `feed-session-smoke completed`.
- `summary.txt`: `final_status: success`, `stop_reason: ""`.
