# Cạm Bẫy `git -C <dir>` Trên Coordinator Guard & Phân Biệt Stale Lock Khi Batch Mẹ Đang Chạy (06/09/2026)

## 1. Cạm Bẫy `git -C <dir>` Khi Chạy Trong Pha `WORKER_RUNNING` / `IDLE`

### Triệu chứng
1. **Trong Pha `WORKER_RUNNING`:**
   Coordinator muốn kiểm tra working tree hoặc diff bằng lệnh:
   `git -C "D:/Taadaa/tiktok-luot nuoi acc" status --short`
   hoặc `git -C "D:/Taadaa/..." diff`
   Lệnh bị Hook chặn đứng vật lý với lỗi:
   `⛔ [FARM GUARD - PHASE: WORKER_RUNNING] Worker subagent đang chạy trong background.`

2. **Trong Pha `IDLE` (Chốt Phiên Staging Gate 2):**
   Khi Coordinator stage file PowerShell bằng lệnh:
   `git -C "D:/Taadaa/tiktok-luot nuoi acc" add docs/... scripts/run-feed-session.ps1`
   Do `git -C` không khớp `ALLOWLIST_PATTERNS`, lệnh trôi xuống Tầng 3 Denylist. Tại đây regex `r'(?:"[^"]*"|\x27[^\x27]*\x27|\S+)\.ps1\b'` bắt trúng chuỗi `run-feed-session.ps1` và chặn đứng với lỗi:
   `⛔ [FARM GUARD - LONG-RUNNER BLOCKED] BỊ CHẶN BỞI PRE-TOOL-USE HOOK: Đây là script batch / automation dài hơi...`

### Nguyên nhân cốt lõi
Trong `farm-coordinator-guard` (`~/.hermes/plugins/farm-coordinator-guard/__init__.py`):
- `ALLOWLIST_PATTERNS` định nghĩa:
  `r"^\s*git\s+(status|log|diff|add|commit|push|pull|fetch|stash|branch|checkout)\b"`
- Cả `ALLOWLIST_PATTERNS` và biến `is_benign` (trong `WORKER_RUNNING`) đều neo chặt từ khóa subcommand ngay sau `git\s+`. Khi truyền flag `-C <path>` ở giữa (`git -C "..." add`), regex không khớp.
- Hậu quả: Lệnh `git add` lành tính trôi xuống Denylist và bị chặn nhầm chỉ vì tên file staged tình cờ có đuôi `.ps1`!

### Quy chuẩn khắc phục (Best Practice)
1. **Dùng tham số `workdir` của tool `terminal` (BẮT BUỘC):**
   Thay vì truyền `git -C "D:/Taadaa/..." add ...`, hãy gọi:
   `terminal(command="git add docs/... scripts/run-feed-session.ps1", workdir="D:/Taadaa/tiktok-luot nuoi acc")`.
   Lệnh lúc này bắt đầu bằng `git add`, khớp 100% Allowlist và không bao giờ bị trôi xuống Denylist.
2. **Cập nhật Regex trong Plugin Guard:**
   Hỗ trợ tùy chọn cờ `-C\s+(?:"[^"]+"|\S+)` nằm giữa `git` và subcommand:
   `r"^\s*git(?:\s+-C\s+(?:"[^"]*"|\S+))?\s+(status|log|diff|add|commit|push|pull|fetch|stash|branch|checkout)\b"`

---

## 2. Phân Biệt Stale Device Lock Khi Batch Mẹ (Multi-Machine) Vẫn Còn PID

### Hiện tượng
Khi kích hoạt lệnh Canary trên Máy 46:
File lock `machine_46.lock.json` ghi PID `226252`.
Kiểm tra `tasklist` thấy PID `226252` vẫn đang sống và là tiến trình mẹ:
`python run_tiktok.py --mode multi-machine-feed-session --machines 1..80`

### Bản chất & Xử lý an toàn
1. Tiến trình mẹ multi-machine batch chạy qua hàng chục máy. Máy 46 đã hoàn thành hoặc đã dừng do Fast-Fail từ trước, nhưng file `.lock.json` của máy 46 vẫn còn ghi nhận PID của tiến trình mẹ đang phục vụ các máy khác (như Máy 5, 27, 58).
2. **Quy tắc xác minh:**
   - Kiểm tra log mới nhất của máy mục tiêu trong runtime directory (`runtime/kibe/live/.../machines/machine_<N>/.../log.jsonl`).
   - Nếu log cho thấy máy <N> đã emit step kết thúc / dừng phiên và tiến trình mẹ không còn thao tác trên máy này, việc dọn dẹp lock `machine_<N>.lock.json` để chạy Canary độc lập là an toàn và hợp lệ.
   - Tuyệt đối KHÔNG `taskkill` PID của tiến trình mẹ vì sẽ làm gãy ngang các máy khác trong fleet đang chạy bình thường.
