# Closeout Gate Worktree Scope Pitfalls & Sol Reviewer >=85 Rubric Patterns

## 1. Cạm bẫy "targets without working-tree changes" trong closeout_gate.py

### Nguyên nhân kỹ thuật:
Trong `closeout_gate.py`:
```python
changed = set(untracked)
if tracked_targets:
    changed |= set(_z_paths(_git_bytes(repo, "diff", "HEAD", "--name-only", "-z", "--", *tracked_targets)))
if changed:
    if sorted(changed) != targets:
        raise ValueError(f"targets without working-tree changes: {sorted(set(targets) - changed)}")
    return "worktree_targeted", targets, diff
```
Khi truyền `--files F1 F2 F3`:
- Nếu có **bất kỳ** file nào trong danh sách `--files` có thay đổi so với `HEAD` (dù là staged hay unstaged), nhánh `if changed:` sẽ được kích hoạt.
- Lúc này, `closeout_gate.py` đòi hỏi **TẤT CẢ** các file trong danh sách `--files` đều phải có thay đổi so với `HEAD`.
- Nếu F1, F2 đã commit vào `HEAD` (không còn diff vs `HEAD`), còn F3 vừa được sửa (có diff vs `HEAD`), `changed = {F3}` != `targets = {F1, F2, F3}` -> **CRASH ngay lập tức** với lỗi `targets without working-tree changes: ['F1', 'F2']`.

### Quy tắc xử lý dứt điểm:
1. **Hoặc tất cả cùng uncommitted**: Dùng `git reset --soft <base>` để đưa toàn bộ thay đổi của F1, F2, F3 về staged/worktree so với `HEAD~1` hoặc commit base, sau đó chạy `closeout_gate.py`.
2. **Hoặc tất cả cùng committed**: Dùng `git commit` gom sạch F1, F2, F3 vào HEAD commit, đảm bảo `git diff HEAD -- <targets>` hoàn toàn sạch, và `set(targets) == committed_scope(base..HEAD)`.

---

## 2. Tiêu chuẩn nâng điểm Sol Reviewer (:20129) từ 82-84 lên >=85 (APPROVED)

Khi review các task liên quan đến logic thời gian, buffer, caching hoặc data synchronization, Sol Reviewer luôn vạch lá tìm sâu các rủi ro sau để trừ điểm:

### A. Regression Proof rõ ràng (Chứng minh bug cũ thực sự sai)
- Không chỉ viết test xác nhận hàm mới chạy đúng.
- Bắt buộc có test so sánh trực tiếp hành vi cũ vs mới (ví dụ: `buffered <= eod_micro` nhưng `buffered > eod_sec`, chứng minh tại sao format cũ bị lọt qua).

### B. Độ phủ Edge-Cases toàn diện
- **Biên âm (Negative Clamping)**: Cắt tại `start_of_day (00:00:00)`. Test cả trường hợp clamp (`-1500` phút) và không clamp (`-5` phút từ `01:00:00` -> `00:55:00`).
- **Rollover qua ngày mới**: Thời gian gần nửa đêm cộng thêm buffer vượt sang ngày hôm sau (không được nhầm là subsecond cap).
- **Subsecond Precision**: Chuẩn hóa `.replace(microsecond=0)` để tương thích 100% với kiểu lưu trữ SQLite string datetime (`%Y-%m-%d %H:%M:%S`).
- **Format biến thể**: Chuỗi rỗng, khoảng trắng, định dạng ISO có Timezone Offset (`+07:00`).
- **Suppress Logging**: Khi `minutes == 0`, dùng `caplog` xác nhận không sinh telemetry log rác.

### C. Concurrent Thread Safety cho In-Memory Metrics
- Khi dùng `threading.Lock` bảo vệ `RECONCILE_METRICS`, bắt buộc có test đa luồng (ví dụ: 5 threads x 20 calls) assert chính xác tổng số counts để chứng minh lock hoạt động đúng.

### D. Integration Test với SQLite WHERE Clause
- Tạo bảng SQLite in-memory / tmp_path, chèn timestamp có microsecond (`.250000`, `.750000`) và thực thi câu truy vấn `SELECT ... WHERE ts <= ?`.
- Chứng minh toán tử so sánh chuỗi của SQLite hoạt động đúng như mong đợi với timestamp đã được cap.

### E. Đồng bộ tuyệt đối giữa Standalone script và Hermes Cron runner
- Khi hệ thống duy trì 2 bản script song song (`scripts/` và `scripts/hermes_cron/`), docstring và helper logic bắt buộc phải đồng bộ 100%.
- Viết test so sánh parity trên danh sách 15+ test vectors biên để đảm bảo 0% drift.
