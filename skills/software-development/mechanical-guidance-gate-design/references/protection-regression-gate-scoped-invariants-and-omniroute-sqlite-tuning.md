# Protection Regression Gate: Scoped Invariants & OmniRoute Infrastructure Tuning

## 1. Context & Problem Statement
1. **Cross-Repo Bleed (Nhiễm chéo quy tắc bất biến):**
   - Taadaa Farm gồm 20 repositories độc lập (`tools`, `tiktok-luot nuoi acc`, `Tiktok-video`, `Tiktok_Reg`, `GPM auto`, `automation-core`...).
   - GuardGate ban đầu duyệt toàn bộ `rules.json` (14 rules) cho mọi commit mà không xét repo hay file path context.
   - Hậu quả: Sửa repo A (`GPM auto`) bị chặn nhầm bởi rule của repo B (`tiktok-luot nuoi acc` Case 161 follow_limit, Case 162 USB timeout), trả về guidance sai ngữ cảnh khiến agent hoang mang, sa vào vòng lặp tê liệt hoặc sửa bậy.

2. **OmniRoute Fast-Fail & SQLite Bloat:**
   - Probe TCP 2s (`PROXY_FAST_FAIL_TIMEOUT_MS = 2000`) chạy song song (`Promise.race`) với LLM request (15-45s). Khi mạng chập chờn trễ 2.1s, probe kết luận proxy chết và force-kill oan stream LLM đang chạy.
   - SQLite tích tụ > 1.06 triệu rows (`conversation_turn_nodes`, `quota_snapshots`), file phình 1.15 GB gây I/O lock trên Node.js Event Loop, watchdog đếm 12 lần timeout (180s) và force-kill tiến trình.

---

## 2. Architectural Solution: 3-Tier Protection Hierarchy

```
[Tier 0: Global Invariants]  --> 20/20 repos (Security, System Stability, Destructive Commands)
      │
[Tier 1: Repo-Scoped]        --> Đích danh Domain (Phone Farm vs GPM vs Tools vs Gateway)
      │
[Tier 2: Path-Level]         --> Lọc tiếp theo file context (Chỉ check khi đụng file/folder cụ thể)
```

### Tier 0: Global Invariants (Áp dụng toàn bộ hệ sinh thái)
- Cấm quét đĩa diện rộng trên thư mục gốc `D:/` (`os.walk`, `glob('D:/*')`, `rglob`).
- Cấm `shell uiautomator dump` và `import uiautomator2` (tránh tràn RAM OOM-kill EXIT=137 trên Samsung S7).
- Cấm dump chuỗi `base64` khổng lồ ra terminal stdout (`cat ... | base64`).
- Cấm scheme `socks5h://` trong `TELEGRAM_PROXY` (httpx không hỗ trợ, gây crash-loop Gateway).

### Tier 1: Repo-Scoped Invariants
- `tiktok-luot nuoi acc`: Case 161 (`follow_limit <= 0`), Case 162 (`connection_wait_timeout >= 20.0s`), cấm đè cờ dưỡng sinh toàn farm (`TAADAA_REST_DAY_NO_FOLLOW`).
- `GPM auto`: Khóa cứng stage khởi tạo `HOTMAIL_LOGIN`, cấm nhảy cóc sang `CHATGPT_REG`.
- `tools`: Khóa sàn worker timeout $\ge 300$s (`dispatch_worker_timeout_floor`).
- Phone Farm (`Tiktok_Reg`, `Tiktok-video`, `luot nuoi acc`): Cấm gán SSID ngoài farm (`Dat`, `BOX 2`), cấm gán domain vào `http_proxy`.

### Tier 2: Path-Level Filtering
- Chỉ kích hoạt rule khi git diff (`+++ b/...`) chạm đúng vào file/thư mục quy định trong `scope.paths`.

---

## 3. Storage & Engine Architecture

### Storage: Giữ 1 file `rules.json` tập trung (Single Source of Truth)
- **Cấm phân mảnh 20 files ở 20 repos:** Tránh tình trạng dev/bot tự sửa rule trong chính PR để lách gate ("vừa đá bóng vừa thổi còi").
- **Tập trung tại `tools/guardgate/rules.json`:** Dễ audit toàn cảnh và chi phí đồng bộ bằng 0 khi có Global Rule mới.

### Schema mẫu có Scope:
```json
{
  "id": "case_162_usb_micro_drop_timeout_floor",
  "scope": {
    "repos": ["tiktok-luot nuoi acc"],
    "paths": ["python_runner/flows/multi_machine_feed_session.py"]
  },
  "params": {
    "variable": "connection_wait_timeout",
    "min_value": 20.0
  },
  "reason": "Khóa sàn timeout USB >= 20.0s chống sập hàng loạt khi micro-drop USB Hub",
  "guidance": "Khi feed bị chờ lâu, giải quyết bằng liveness check; TUYỆT ĐỐI KHÔNG hạ timeout USB."
}
```

### Engine Matcher O(1):
```python
def _match_rules(self, repo_name: str, changed_files: list[str]) -> list[dict]:
    # O(1) Candidate Lookup
    candidates = self.global_rules + self.repo_rules_index.get(repo_name, [])
    applicable = []
    for rule in candidates:
        rule_paths = rule.get("scope", {}).get("paths", ["*"])
        if "*" in rule_paths:
            applicable.append(rule)
            continue
        if any(any(fnmatch.fnmatch(f, p) for p in rule_paths) for f in changed_files):
            applicable.append(rule)
    return applicable
```

---

## 4. OmniRoute Infrastructure Regression Gate Invariants
- `PROXY_FAST_FAIL_TIMEOUT_MS`: Khóa cứng trong dải `[4000, 10000]` ms (chuẩn 5000ms).
- `PROXY_FAIL_OPEN`: Khóa cứng `false` (ngăn rò rỉ IP Direct dân cư làm ban dàn nick farm).
- `$MaxDeadlockFailures`: Khóa cứng trong dải `[4, 6]` (~120s – 180s) tránh False-Kill khi prefill 300k+ tokens.
- Socket restart buffer: Bắt buộc có `Start-Sleep -Seconds 3` trước khi spawn Node.js mới để tránh đụng cờ `TIME_WAIT` port 20129.
- SQLite Cleanup: Chu kỳ `every 6h`, retention $\le 3$ ngày cho đủ 6 bảng nặng (`conversation_turn_nodes`, `agentic_conversations`, `quota_snapshots`, `xp_audit_log`, `proxy_logs`, `call_logs`).
