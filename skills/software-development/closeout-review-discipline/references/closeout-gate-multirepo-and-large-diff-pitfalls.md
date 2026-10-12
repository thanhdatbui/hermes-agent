# Closeout Gate Multi-Repo Working Tree & Large Diff Pitfalls

## 1. Pitfall: Bẫy Diff Quá Lớn (`DIFF_TOO_LARGE`) Khi Truyền Repo Cấp Con Với Base Mặc Định

### Hiện tượng:
Khi chạy `python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/tiktok-luot nuoi acc" --files scripts/feed_session_watchdog.py ...` với `--base origin/main` (mặc định), Gate báo lỗi:
```text
✘ GATE-FAIL(diff-too-large): [Gate Fail-Fast: DIFF_TOO_LARGE] targeted diff quá lớn (166435 > 120000 bytes).
Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.
```

### Nguyên nhân gốc rễ (Root Cause):
- Trong môi trường local làm việc đa repo (monorepo hoặc repo nhiều branch/worktree tồn dư), nhánh local đang checkout có thể lệch nhiều commit so với `origin/main` (ví dụ: chứa 58 files diff từ các đợt phát triển trước đó).
- Khi truyền `--base origin/main`, `closeout_gate.py` so sánh working-tree/target files với `origin/main` thay vì commit cha của phiên hiện tại.
- Nếu repo tích tụ nhiều thay đổi lịch sử chưa push về `origin/main`, diff tích lũy sẽ vượt trần 120,000 bytes.

### Quy tắc khắc phục (Remediation Invariant):
1. **Kiểm tra trạng thái branch trước khi gọi closeout:**
   - Dùng `git -C <repo> diff --stat HEAD` để biết chính xác các file đang thay đổi trong phiên hiện tại.
2. **Neo `--base HEAD` khi kiểm tra working tree của phiên hiện tại:**
   - Khi commit chưa được tạo và bạn muốn thẩm định đúng tập file vừa sửa:
     `python D:/Taadaa/tools/closeout_gate.py --repo <repo_path> --base HEAD --files <target_files> --json-output`
   - Điều này giới hạn diff CHỈ đúng phần uncommitted changes của các file mục tiêu trong phiên làm việc, không bị tính dồn các commit cũ so với remote origin.
3. **Khi commit đã tạo cục bộ:**
   - Dùng `--base HEAD~1` để so sánh đúng 1 commit vừa tạo gần nhất.

---

## 2. Pitfall: Untracked Files Bị Bỏ Qua Bởi `closeout_gate.py --files`

### Hiện tượng:
File mới tạo (ví dụ: `nurture_health_helper.py`, `tests/test_nurture_health_helper.py`) khi chạy `closeout_gate.py --files ...` có thể báo:
```text
✘ Failed to extract diff: no staged, working-tree, or HEAD-commit changes for targets [...]
```

### Nguyên nhân:
- `git diff` mặc định chỉ theo dõi các file đã được git track (`tracked files`). Các file hoàn toàn mới nằm ở trạng thái untracked (`??`) không sinh ra git diff thông thường nếu chưa được stage hoặc commit.

### Quy tắc khắc phục:
- Đối với file hoàn toàn mới, cần `git add <new_files>` để đưa vào staging area trước khi chạy `closeout_gate.py`, hoặc đảm bảo file được git track để Gate có thể trích xuất candidate diff sha256 chuẩn xác.

---

## 3. Pitfall: OmniRoute Read Timeout (HTTP 300s) & Cơ Chế First-Responder Sol Repair

### Hiện tượng:
Khi gọi `closeout_gate.py`, bước 4 gọi model `review` trên `:20129` có thể bị timeout 300s:
```text
[Gate] FATAL: Pipeline execution failed: [OmniRouteClient] Request timed out on read: HTTPConnectionPool(host='127.0.0.1', port=20129): Read timed out. (read timeout=300.0)
```

### Quy tắc ứng xử:
1. **TRANSIENT vs STRUCTURAL:**
   - Timeout mạng / backend OmniRoute `:20129` là lỗi TRANSIENT. Retry với backoff (tối đa 2 lần).
2. **Khi Gate REJECTED (Score < 85):**
   - Strike 1 & 2 Remediation: BẮT BUỘC dùng `python D:/Taadaa/tools/sol_repair.py --repo <repo> --files <files> --findings "..."` để Sol High sinh patch O(1).
   - Kiểm tra `git diff --numstat <= 30` dòng trước khi apply.
   - Chạy focused pytest verify lại trước khi rerun `closeout_gate.py`.

---

## 4. Pitfall: Xung Đột Ghi Audit Log Đa Repo (`gate_audit.jsonl` Collision Trap) & Lỗi Chặn `git push`

### Hiện tượng:
Repo vừa hoàn tất kiểm thử và được Reviewer chấm điểm đạt `APPROVED >= 85/100`, nhưng khi chạy `git push` thì Coordinator Guard chặn đứng:
```text
⛔ [COORDINATOR GUARD - TERMINAL BLOCKED]: COORDINATOR TERMINAL BLOCKED: Cấm 'git push' trước khi Closeout Gate trả về APPROVED >= 85!
```

### Nguyên nhân gốc rễ (Root Cause):
- Toàn bộ các repo trên hệ thống Taadaa Phone Farm chia sẻ chung một tệp nhật ký thẩm định tập trung tại `D:/Taadaa/logs/gate_audit.jsonl`.
- Khi có nhiều worker, cronjob hoặc quy trình chạy song song (ví dụ: một subagent khác đang audit `D:/Taadaa/tools` cùng lúc), mỗi lần `closeout_gate.py` kết thúc sẽ nối (append) một dòng JSON vào cuối file `gate_audit.jsonl`.
- Hook kiểm tra an toàn `git push` của Coordinator Guard đọc bản ghi thẩm định ở đuôi tệp (`tail /d/Taadaa/logs/gate_audit.jsonl`). Nếu repo khác vừa append một kết quả `REJECTED` (ví dụ score 82 < 85), Guard sẽ đọc nhầm trạng thái của repo đó và tưởng rằng phiên hiện tại chưa đạt chuẩn, dẫn đến chặn lệnh push oan.

### Quy tắc điều phối & Khắc phục:
1. **Kiểm tra đuôi log audit ngay lập tức:**
   - Dùng lệnh `tail -n 5 /d/Taadaa/logs/gate_audit.jsonl` để đối soát xem dòng cuối cùng thuộc repo nào (`"repo"`) và kết quả là gì (`"verdict"`).
2. **Tái kích hoạt Gate để chiếm đỉnh Log:**
   - Nếu dòng cuối cùng bị đè bởi repo khác có verdict REJECTED, Coordinator chỉ cần chạy lại `closeout_gate.py` cho repo hiện tại:
     `python D:/Taadaa/tools/closeout_gate.py --repo "<repo_path>" --base HEAD~1 --files <files> --json-output`
   - Bản ghi `APPROVED` mới sẽ được nối vào cuối file `gate_audit.jsonl`.
3. **Thực thi `git push` ngay sau đó:**
   - Khi tệp log đã có bản ghi mới nhất là `APPROVED` của repo hiện tại, Guard sẽ lập tức mở khóa cho lệnh `git push`.

