# Triage reviewer findings before repair (closeout)

Dùng khi plan-review trả `REJECT` trong closeout: phân loại finding nào là
lỗi thật, finding nào là false-positive, trước khi sửa. Sửa mù theo review
đã từng tạo ra string hỏng và commit lỗi trong phiên 2026-09-03.

## 1. Reproduce từng blocker trước khi edit

- **Syntax claim** → `python -m py_compile <file>` trên đúng file. Chỉ sửa
  khi compile fail thật.
- **Missing function/import claim** → grep định nghĩa trong source + import
  bằng đúng cwd mà runner chính thức dùng (ví dụ `python_runner/` chứ không
  phải repo root). Import sai cwd cho `ModuleNotFoundError` giả.
- **Broken-string claim** → in `repr()` dòng bị nêu tên, kiểm tra continuation.

## 2. Baseline check cho test fail

Khi focused test fail sau edit, stash scoped file và chạy lại trên HEAD sạch:

```bash
git stash push -m "wip: triage" <scoped-file>
python -m pytest <failing-test> -x
git stash pop
```

Fail cả trên HEAD sạch = lỗi có sẵn (baseline), không quy cho candidate.
Báo rõ baseline, không fix lan man ngoài scope.

## 3. Pitfall: backslash-newline trong f-string

```python
canary_cmd=f'...scripts\
un-follow.ps1" ...'
```

Backslash cuối dòng là line-continuation: hoặc sinh chuỗi hỏng
(`scriptsun-follow.ps1`, mất `run-`) hoặc `SyntaxError: unterminated string
literal` (py_compile bắt được). Fix: khi chuỗi không cần interpolation, bỏ
`f` prefix và dùng plain string một dòng với `/` thay vì `\\`.

## 4. Stale git lock sau tiến trình timeout

`fatal: cannot lock ref ... File exists` sau khi git process timeout:
chứng minh không còn writer active (tasklist), rồi chỉ xóa đúng file
`*.lock` stale (`index.lock`, `HEAD.lock`, `refs/heads/*.lock`). Tuyệt đối
không `reset --hard` / `clean -fd` để "dọn" lock.

## 5. Tự động sửa lỗi & Re-review vòng lặp đến APPROVED

Khi review trả `REJECT` trong chốt phiên:
1. **KHÔNG DỪNG LẠI & CẤM PUSH KHI CÒN REJECTED:** Tuyệt đối không dừng phiên báo blocker dở dang khi chưa nỗ lực sửa, và CẤM TUYỆT ĐỐI push lên remote khi chưa có `DECISION: APPROVED`.
2. **Tự động triage & fix vòng lặp:**
   - Triage từng blocker (kiểm tra syntax bằng `py_compile`, kiểm tra circular import, loại bỏ collision priority, thêm fail-closed checks).
   - Chạy focused unit tests để bảo đảm fix hoạt động.
   - Gọi lại G1 Plan-Review với toàn bộ diff phiên (so với base commit đầu phiên `git diff <base_commit>` để reviewer nhìn thấy đầy đủ các alias và hàm phụ trợ, tránh false-rejection).
   - Lặp lại quy trình sửa -> test -> review đến khi nhận được `DECISION: APPROVED`.
3. **Chỉ chuyển sang G2/G3/G4 sau khi APPROVED:** Khi đã có verdict APPROVED từ 9Router, mới tiến hành commit exact scope, rebase upstream và push remote.

## 6. Overly broad fallback & Fail-closed preservation

- **Tránh wildcard trên `manual-needed:*`:** Khi xử lý focus fallback trong `safety_check`, không dùng `detected.startswith("manual-needed:")` vì sẽ vô tình override focus cho cả `manual-needed:login` hoặc `manual-needed:google-account`, phá vỡ nguyên tắc fail-closed. Chỉ whitelist các màn hình an toàn cụ thể (`KNOWN_TIKTOK_SCREENS`, `SPONSORED_SCREENS`, `MANUAL_SCREEN_REASONS`).
- **OmniRoute (:20129) Failover khi 9Router Timeout:** Khi route `plan-review` trên 9Router (`:20128`) bị nghẽn socket/timeout quá 60s, lập tức chuyển sang gọi OmniRoute (`:20129`) với model `antigravity/claude-sonnet-4-6-low` hoặc `ag-claude` để tiếp tục chu trình review độc lập đạt chuẩn mà không làm tắc tiến trình chốt phiên.

## 7. Plaintext Credentials & Lan Passwords in Docs/Examples

- **Chặn đứng mọi credential thật:** Plan-Review kiểm tra nghiêm ngặt chính sách bảo mật và sẽ lập tức `REJECT` nếu diff chứa credential thật (ví dụ `admin%401:admin%401@192.168.110.2:10001` hay mật khẩu Wi-Fi/router) kể cả khi nằm trong file tài liệu `.md`, cmt code hay lệnh probe ví dụ.
- **Giải pháp:** Bắt buộc thay thế bằng placeholder dạng token chuẩn: `<PROXY_USER>:<PROXY_PASS>@<PROXY_HOST>:<PROXY_PORT>` hoặc `<WPA2_PASSPHRASE_FARM>`.

## 8. Broad Process Kill vs PID-Targeted Operations

- **Cấm kill diện rộng:** Lệnh `Stop-Process -Name pythonw -Force` (hoặc `pkill pythonw`) sẽ giết toàn bộ các tiến trình Python không cửa sổ trên hệ thống, bao gồm các script chạy nền của Phone Farm. Plan-Review sẽ reject nếu phát hiện lệnh này trong code lẫn tài liệu hướng dẫn.
- **Giải pháp:** Luôn trích xuất PID cụ thể từ state file (ví dụ `$p = (Get-Content '$env:LOCALAPPDATA\hermes\gateway_state.json' | ConvertFrom-Json).pid`) và dùng `Stop-Process -Id $p -Force`.

## 9. Restart Watcher Robustness Invariants (restart-when-idle.ps1)

- **Nguyên nhân reject:** Watcher script thiếu timeout (chạy vô hạn nếu bot không bao giờ idle), thiếu đợi giải phóng process (gây race condition trên file lock SQLite `state.db`), và không kiểm tra tiến trình mới sau khởi động.
- **Quy chuẩn bắt buộc:**
  1. Giới hạn thời gian chờ tối đa (ví dụ `$maxWaitSeconds = 600`) đối chiếu với `[DateTime]::UtcNow`.
  2. Bổ sung `Wait-Process -Id $targetPid -Timeout 10` ngay sau `Stop-Process` trước khi sleep.
  3. Dùng `Start-Process ... -PassThru` và kiểm tra `if ($newProc -and !$newProc.HasExited)` để xác thực tiến trình mới không crash sớm.

## 10. Marker Overlap, Substring Anchoring & Dead-Code Subsumption

- **Tránh trùng lặp substring giữa các marker:** Khi mở rộng tập marker (ví dụ nhận diện post dạng Photo trên TikTok Feed), tuyệt đối không để 2 danh mục marker kiểm tra chung 1 từ khóa con (như `photo_marker` và `repost_marker` đều kiểm tra `"đăng lại"`, làm một UI element bị tính điểm 2 lần, làm tăng điểm giả tạo). Phải tách riêng biệt thành các danh mục độc lập (`repost_marker`, `photo_marker`, `follow_marker`).
- **Siết chặt neo từ vựng tiếng Việt (Strict Substring Anchoring):** Không dùng `in value` trên các từ đơn phổ biến tiếng Việt như `"ảnh"` hay `"lưu"` (dễ match vào caption, username, hoặc alt-text). Dùng `value in {"ảnh", "photo"}` hoặc `value.startswith("ảnh,")` / `value.startswith("photo,")`. Với bookmark/lưu, dùng cụm từ chính xác như `"đã lưu"`, `"thêm vào mục yêu thích"`, tránh bare `"lưu"` hoặc `"yêu thích"` (trùng nút Thích/Like).
- **Tránh Dead Code khi thêm điều kiện tổng hợp (Subsumption):** Khi thêm khối kiểm tra điều kiện tổng hợp trước một dòng `return bool(...)` cũ: nếu khối mới đã bao hàm (subsume) tất cả các điều kiện của dòng cũ, dòng cũ trở thành unreachable dead code $\rightarrow$ Bắt buộc xóa dòng cũ hoặc chuyển thành `return False` dứt khoát.
- **Thứ tự kiểm tra không được short-circuit các nhánh chuyên biệt:** Các kiểm tra tổng quát (General Feed / FYP) phải đặt SAU các kiểm tra luồng hẹp (Following Feed, Friends Feed) để tránh bypass logic kiểm tra tab chuyên biệt.
- **Đồng bộ tuyệt đối giữa Code và Docs (Case Documentation):** Số lượng marker (ví dụ 8 markers thay vì 7) và tên các từ khóa/marker trong `docs/farm-automation-cases.md` phải khớp 100% với code thực tế. Reviewer sẽ REJECT nếu tài liệu ghi một đằng (ví dụ bảo `"đăng lại"` nằm trong `photo_marker`) nhưng code triển khai một nẻo (`repost_marker`).

## 11. Concurrent Background Writer Stash & Rebase Pattern (Gate 3)

- **Hiện tượng:** Trong môi trường Phone Farm, các tiến trình nền (reaper locks, background feed workers) liên tục touch các file trong working tree (`scripts/reap-dead-owner-locks.py`, `python_runner/flows/feed_swipe_smoke.py`, v.v.). Khi Coordinator chạy `git pull --rebase origin master`, git từ chối với lỗi: `cannot pull with rebase: You have unstaged changes`.
- **Giải pháp an toàn:**
  1. Dùng `git stash push --include-untracked -m "stash_concurrent_worker_edits"` để cô lập toàn bộ các thay đổi chưa stage của tiến trình nền.
  2. Thực hiện `git pull --rebase origin master` sạch sẽ.
  3. Sau khi rebase và push xong, chạy `git stash pop` ngay để khôi phục nguyên vẹn trạng thái làm việc cho các tiến trình nền mà không làm mất bất kỳ byte nào.

## 12. Worker Feature Creep & Out-of-Scope Code Injection (Gate 1 Rejection)

- **Hiện tượng:** Worker subagent khi được giao sửa lỗi (ví dụ: bọc try/except cho timeout phím Back trong `feed_swipe_smoke.py`) lại tự ý "tiện tay" thêm các class, hàm helper và logic rẽ nhánh ngoài scope (ví dụ: class `SwitchOption`, hàm `_find_user_placeholder_switch_option`, nhánh fallback `is_placeholder_candidate` trong `verify_and_switch_profile` dài ~55 dòng).
- **Hậu quả:** Plan-Review Gate 1 lập tức phát hiện code ngoài scope, thay đổi luồng rẽ nhánh, có bare `except Exception: pass`, thiếu unit test và thiếu docs → Bắn `VERDICT: REJECTED`.
- **Triage & Xử lý:**
  1. Đối chiếu diff thực tế với mục tiêu ban đầu của task / Case fix.
  2. Bóc tách và revert triệt để toàn bộ phần code ngoài scope (out-of-scope additions), chỉ giữ lại đúng các thay đổi tối thiểu cần thiết để giải quyết lỗi được giao (Scope Lock).
  3. Chạy `python -m py_compile` kiểm tra lại cú pháp.
  4. Gửi lại diff hẹp cho Plan-Review để nhận ngay `VERDICT: APPROVED`.
  5. Nếu phần feature ngoài scope thực sự có giá trị, ghi chú lại để mở task / PR riêng biệt có unit test và documentation đầy đủ, tuyệt đối không nhập nhèm ghép chung vào bugfix patch.

## 13. Python Environment & PYTHONPATH Isolation on Windows (Pytest & PIL Errors)

- **Hiện tượng:** Khi chạy `python -m pytest` hoặc script xử lý ảnh (PIL/Pillow) trong terminal Git-Bash trên Windows, lệnh bị crash với lỗi:
  `ImportError: cannot import name '_imaging' from 'PIL' (AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL\__init__.py)`
- **Nguyên nhân:** Môi trường shell kế thừa `PYTHONPATH` trỏ vào venv của Hermes Agent (nơi PIL C-extension có thể không tương thích hoặc bị hỏng), làm ô nhiễm môi trường chạy của consumer repo và hệ thống.
- **Giải pháp chuẩn:**
  1. Khi chạy `pytest` cho consumer repos: BẮT BUỘC dùng `env -u PYTHONPATH "D:/Taadaa/python-envs/automation/Scripts/python.exe" -m pytest <tests> -q` để xóa sạch `PYTHONPATH` và gọi đúng python của repo.
  2. Khi chạy script vẽ banner / PIL độc lập: BẮT BUỘC gọi trực tiếp Python chuẩn của hệ điều hành với cờ cô lập: `C:/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe -E -s -c "..."` (`-E` bỏ qua env vars, `-s` bỏ user site-packages).

## 14. Review Scope Creep After Live Canary Pass (Canary Pass = Code Freeze)

- **Hiện tượng:** Sau khi Live Canary đã PASS trên thiết bị thật (ví dụ máy 39 đã đăng thành công video 5), Reviewer Gate 1 lại bới các lỗi ngoài scope (draft cleanup, hashtag threshold, format code) làm Coordinator sa đà dispatch worker sửa tiếp, kéo theo gãy mock test và kéo dài phiên hơn 3 tiếng (*"vkl mày làm cái đéo gì 3 tiếng k xong"*).
- **Quy tắc Bouncer (Reviewer Gatekeeper):** Khi Live Canary trên máy thật đã PASS, kết quả trên thiết bị thật là Chân Lý Tối Thượng (Ground Truth). Reviewer trong phiên hotfix cứu farm đóng vai trò là "Bouncer" kiểm tra nhị phân (Yes/No):
  1. Fix có giải quyết đúng Root Cause ban đầu gây kẹt máy không?
  2. Live Canary trên thiết bị thật đã pass 100% chưa?
  3. Có nguy cơ hồi quy gây crash cho các máy khác không?
- **Quy tắc chặn Scope Creep:** Nếu reviewer phát hiện các vấn đề ngoài scope ban đầu (không liên quan trực tiếp đến root cause gây alert), CẤM TUYỆT ĐỐI sửa code trong phiên này. Bắt buộc ghi nhận các phát hiện phụ đó vào ticket riêng / backlog P3 để xử lý ở phiên sau, và tiến hành chốt phiên commit/push ngay lập tức.



