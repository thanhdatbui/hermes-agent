# Claude Opus Max Audit & Per-Session Heartbeat Watchdog Architecture

## 1. Quy Chuẩn Reviewer: OmniRoute Combo vs Claude CLI Opus Max

Được chuẩn hóa theo chỉ thị của user ngày 06/09/2026:

| Loại tác vụ | Công cụ Review / Audit | Cấu hình & Tham số bắt buộc |
|---|---|---|
| **Review / Audit Plan bình thường** | Combo OmniRoute Review | Endpoint `:20129` theo chuỗi đã setup (Opus -> Sonnet -> GPT OSS -> Nemotron -> AG; cấm tự review). |
| **Ca khó / Tranh chấp kiến trúc** | Claude CLI Opus | `claude -p "..." --model opus --effort high` (Claude qua app CLI native, cấm nhầm với OmniRoute) |
| **User chủ động ra lệnh gọi Claude CLI** ("gọi claude cli", "kêu claude kiểm tra") | Claude CLI Opus | **LUÔN gọi Claude CLI native (app CLI) Opus ở mức High (`--model opus --effort high`). CẤM tự ý hạ xuống Sonnet.** Mọi tham số reasoning đều để cấp độ high để bảo toàn quota Claude Pro. |

---

## 2. Bài Học Kiến Trúc Từ Audit Claude Opus Max (Vòng 2)

Khi audit hệ thống Silent Stale Watchdog, Claude Opus Max đã đào sâu tới tận tiến trình runtime và chỉ ra 3 lỗ hổng cốt lõi của thiết kế ban đầu:

### Lỗ hổng 1: Producer Heartbeat Chưa Nạp Vào RAM (Blocker Runtime)
- **Hiện tượng:** Hook `post_tool_call` được viết trong plugin trên đĩa, nhưng Hermes Gateway tiến trình mẹ đã chạy từ trước chưa nạp lại module này.
- **Hậu quả:** File `watchdog_state.json` chưa hề được tạo trên đĩa. Script watchdog đọc file không thấy gì (`if not state: return 0`) nên im lặng vĩnh viễn $\rightarrow$ Watchdog bị mù hoàn toàn, rơi vào đúng chế độ "treo im lặng".
- **Giải pháp:** Mọi thay đổi hook trong plugin BẮT BUỘC phải đi kèm restart Gateway và verify file state vật lý xuất hiện trên đĩa (`test -f watchdog_state.json`).

### Lỗ hổng 2: Heartbeat Toàn Cục (Global Last-Writer-Wins) Bị Che Khuất
- **Hiện tượng:** Lưu 1 giá trị `last_beat` toàn cục cho cả hệ thống.
- **Hậu quả:** Trên farm có nhiều session (coordinator, multiple background workers). Nếu 1 worker chạy tool call liên tục, `last_beat` luôn tươi $\rightarrow$ Vô tình che giấu một worker hoặc coordinator khác đang bị treo cứng 45 phút!
- **Giải pháp:** BẮT BUỘC dùng cấu trúc **Heartbeat per-session**:
  ```json
  {
    "sessions": {
      "session_id_1": {
        "last_beat": 1788673400.0,
        "tool": "terminal",
        "is_canary": false,
        "state": "running"
      }
    }
  }
  ```
  Watchdog duyệt từng session đang ở trạng thái active trong `farm_coordinator_phase.json` để kiểm tra độ trễ độc lập.

### Lỗ hổng 3: Gán Cờ Canary Ngược Thời Điểm (Post-Hook Trap)
- **Hiện tượng:** Cờ `is_canary` được suy ra ở `post_tool_call` (sau khi tool đã chạy xong).
- **Hậu quả:** Lệnh Canary máy thật là lệnh chạy dài 10-15 phút chưa return. Trong lúc nó đang chạy, `watchdog` đọc heartbeat của tool *trước đó* (`is_canary = False`) $\rightarrow$ Áp ngưỡng 10 phút và **báo treo giả**.
- **Giải pháp:** 
  1. Gán cờ `is_canary = True` ngay tại **`pre_tool_call`** khi lệnh chuẩn bị thực thi.
  2. Nới rộng regex nhận diện launcher thật: `r'\b(canary|recoverytestswipes|run-feed-session)\b'`.

---

## 3. Checklist Triển Khai Heartbeat Per-Session

1. Ghi heartbeat per-session vào `watchdog_state.json` (atomic write per PID).
2. Đánh dấu `running_tool` và `is_canary` ở `pre_tool_call`, cập nhật kết quả ở `post_tool_call`.
3. Ép mã hóa `sys.stdout.reconfigure(encoding="utf-8")` trong script watchdog để chống `UnicodeEncodeError` trên console pipe Windows.
4. Bọc `try ... except Exception: return 0` toàn bộ `main()` để đảm bảo invariant stdout hoàn toàn trắng khi bình thường.

---

## 4. Đặc Tả Triển Khai Thực Tế (v2.2 Production Implemented - 06/09/2026)

### Schema `watchdog_state.json`:
```json
{
  "sessions": {
    "<session_id>": {
      "last_beat": 1788675348.183,
      "last_beat_iso": "2026-09-06T13:15:48.184363",
      "current_tool": null,
      "current_tool_start": null,
      "is_canary": true,
      "status": "success",
      "tool": "terminal",
      "parent_session_id": "<coordinator_session_id>"
    }
  },
  "updated_at": 1788675348.185
}
```

### Điểm Mấu Chốt Kiến Trúc:
1. **Pre-hook Canary Lock**: Kiểm tra regex `r'\b(canary|recoverytestswipes|run-feed-session)\b'`. Nếu khớp, ngay lập tức gán `current_tool_start = time.time()` và `is_canary = True`. Nếu tool bị chặn bởi State Guard hoặc Action Guard, lập tức đánh dấu `status = "blocked"` để không để lại trạng thái "running" giả.
2. **Subagent Resolution qua SQLite `state.db`**: Khi Worker Subagent chạy, hook tự động truy vấn `parent_session_id` từ `state.db`. Watchdog script khi quét Coordinator session (`phase in ('WORKER_RUNNING', 'ALERT')`) sẽ tự động map tới state của subagent tương ứng.
3. **Đồng bộ song hành (Dual Mirror)**: Mọi chỉnh sửa trên `farm-coordinator-guard` và `hermes_stale_watchdog.py` BẮT BUỘC lưu đồng thời ở:
   - Runtime: `~/AppData/Local/hermes/plugins/` và `~/AppData/Local/hermes/scripts/`
   - Git Deploy Repo: `D:/Taadaa/Hermes/deploy/hermes-home/plugins/` và `deploy/hermes-home/scripts/`
