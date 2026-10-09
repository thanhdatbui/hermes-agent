# Worker cháy budget 15 calls mà chưa áp patch (2026-09-13)

## Sự việc
Fix `tap_profile` (TikTok-video/adapter.py): 3 worker `omni-worker` liên tiếp chạm trần 15 tool calls mà KHÔNG ghi được byte nào vào file.
- Worker 1: chỉ sửa được `ui_profile.py` (1 dòng resource-id oly), FAIL-FAST đúng, trả proposed contract cho adapter.py.
- Worker 2: khảo sát lại từ đầu + viết contract, hết budget trước khi patch.
- Worker 3: định vị lại anchor từ đầu, hết budget trước khi patch.
- Worker 4 (đang chạy): contract rút gọn còn đúng 2 calls (1 patch + 1 test).

## Nguyên nhân
Contract giao cho worker chứa cả: khảo sát hiện trường + đọc nhiều file + viết contract + patch + test — vượt xa budget 15 calls. Worker nào cũng đốt calls vào đọc/search lại những gì coordinator đã biết.

## Quy tắc (bổ sung cho coordinator)
1. Khi coordinator đã tự xác minh hiện trường (XML/log/anchor dòng chính xác), worker KHÔNG được khảo sát lại. Contract phải có `old_string`/`new_string` đóng sẵn + cấm search/read ngoài file đích.
2. Task áp patch = micro-task ≤3 calls: 1 patch + 1 test + 1 báo cáo. Cấm gộp khảo sát + patch + test vào cùng một worker khi budget là 15.
3. Worker trả về `0 files modified` + hết iterations = THẤT BẠI CẤU TRÚC (Gate 3): cấm retry prompt cũ; lần dispatch sau phải rút gọn scope (như worker 4), không được giao lại nguyên task.
4. FAIL-FAST là hành vi đúng (worker 1 được khen): trả anchor + proposed contract sớm tốt hơn đốt hết budget rồi fail im lặng.
