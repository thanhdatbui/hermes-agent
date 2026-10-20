# Test Fixture Compaction & Auto-Sync Cron Race in Closeout Gate (2026-10-20)

## 1. Context & Sự Cố
Trong phiên triển khai cơ chế Delta Snapshot cho các cron report (Hotmail lifecycle, Gmail nurture, Render watchdog):
1. **Bẫy Diff Lạm Phát Do Test Fixture Lớn (>26KB):**
   - Các script báo cáo farm có schema trạng thái rộng (hàng chục metric key cho từng farm `kibe`, `admin`, `totals`, `buckets`).
   - Việc viết các test method lặp đi lặp lại các dict fixture literal đẩy diff của file test lên >250 dòng (>27KB diff text), tiệm cận trần payload của Sol High (30KB).
   - Khi diff vượt ngưỡng an toàn, Sol Reviewer phán quyết `NEED_CONTEXT` hoặc trừ điểm vì "test diff bị lược / không đủ ngữ cảnh review toàn diện".
2. **Auto-Sync Cron Race trên HEAD (`7e576815788f`):**
   - Cronjob `sync-hermes-skills-and-brain-to-git` chạy mỗi 5 phút tự động commit các thay đổi skills/memories vào nhánh `main`.
   - Nếu commit của cron chen ngang vào đỉnh `HEAD` khi đang chuẩn bị chạy `closeout_gate.py --base HEAD~1 --files ...`, gate sẽ báo lỗi `[Gate Fail-Fast: SCOPE_NOT_DECLARED]` hoặc `no staged, working-tree, or HEAD-commit changes for targets`.

## 2. Kỹ Thuật Khắc Phục (Patterns & Solutions)

### A. Parameterized Fixture Factory Pattern Cho Test Suite
- Thay vì khai báo lặp đi lặp lại dict fixture 15–20 dòng trong từng test method:
```python
# CHỐNG LẠM PHÁT DIFF: Dùng helper factory rút gọn
def _snap(**kwargs):
    m: dict = {k: 0 for k in report_mod.METRIC_KEYS}
    m["buckets"] = {s: 0 for s in report_mod.BUCKETS}
    m.update(kwargs)
    return {
        "farms": {"kibe": dict(m), "admin": dict(m)},
        "totals": dict(m),
        "recent": {k: 0 for k in report_mod.RECENT_KEYS},
        "farm_recent": {"kibe": {k: 0 for k in report_mod.RECENT_KEYS}, "admin": {k: 0 for k in report_mod.RECENT_KEYS}},
        "pool": {"connections_ok": True, "combo_ok": True, "total": 0, "active": 0, "soaking": 0, "unknown": 0, "models": 0},
        "warning_count": 0,
    }
```
- Giúp giảm kích thước file test từ >44KB xuống <41KB, gọt bớt hơn 50 dòng boilerplate thừa mà vẫn giữ nguyên 100% assertions hành vi và độ phủ test.

### B. Quy Trình Khóa Cron Sync Trước Khi Closeout
1. **Tạm dừng cron sync trước khi commit:**
   `hermes cron pause 7e576815788f`
2. **Tách biệt Commit Chore và Commit Feature:**
   - Nếu đã có uncommitted changes ở skills/memories/jobs.json, commit riêng chúng trước:
     `git add -u && git reset HEAD <target_files> && git commit -m "chore: sync skills, brain memories, and watchdogs"`
   - Sau đó mới commit target files lên đỉnh HEAD:
     `git add <target_files> && git commit -m "feat(...): ..."`
   - Đảm bảo `git diff --name-only HEAD~1 HEAD` trả về CHÍNH XÁC danh sách trong `--files`.
3. **Chạy Closeout Gate an toàn:**
   `python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/Hermes --base HEAD~1 --files <target_impl> <target_test> --json-output`
4. **Mở lại cron sau khi hoàn tất phiên:**
   `hermes cron resume 7e576815788f`
