# Protection Regression Gate: Repo Scoping & Cross-Repo Contamination Prevention (2026-10-27)

## 1. Context & The Anti-Pattern
Trong hệ sinh thái Taadaa Farm gồm ~20 repositories độc lập (`tools`, `tiktok-luot nuoi acc`, `GPM auto`, `Tiktok-video`, `Tiktok_Reg`...), cơ chế chốt chặn bất biến (Protection Regression Gate / GuardGate) ban đầu sử dụng 1 file `rules.json` cào bằng.
Hậu quả nghiêm trọng (Leaky Abstraction & False Positive Friction):
- Khi dev/bot sửa code tại repo A (`GPM auto`), GuardGate duyệt qua toàn bộ 14 rules và kích hoạt các rules của repo B (`tiktok-luot nuoi acc` Case 162 USB timeout $\ge$ 20s, Case 161 follow ceiling $\le$ 0).
- Trùng tên biến ngẫu nhiên (`connection_wait_timeout`, `follow_limit`, `row['PASS']`) dẫn đến **DENY oan (False Deny)**.
- Error guidance trả về sai ngữ cảnh: Đang sửa script login Gmail trên PC nhưng Gate báo *"Kiểm tra nguồn tổ ong và cáp USB uplink của Samsung S7"*, làm Worker hoang mang, sửa bậy và sinh vòng lặp tê liệt.

## 2. Architectural Decision Record (ADR)
Thống nhất giữa Operator, Coordinator và Principal Architect:

### A. Phân tầng 3 cấp độ (3-Tier Invariant Hierarchy):
1. **Tier 0 — Global Invariants (`repos: ["*"]`, `paths: ["*"]`):**
   - Áp dụng trên toàn bộ 20/20 repos. Vi phạm ở bất kỳ đâu cũng bị chặn đứng ngay lập tức.
   - Ví dụ:
     * Cấm quét đĩa diện rộng trên thư mục gốc `D:/` (`os.walk`, `glob`, `rglob`).
     * Cấm `shell uiautomator dump` và `import uiautomator2` (tránh tràn RAM / OOM-kill `EXIT=137` trên S7).
     * Cấm dump chuỗi `base64` khổng lồ ra terminal stdout.
     * Cấm scheme `socks5h://` trong `TELEGRAM_PROXY`.
     * Cấm bulk pre-reserve giữ lock hàng loạt trong queue (bắt buộc JIT lock từng máy).
     * Cấm gán domain ngoài vào Android `http_proxy` (gây Hairpin NAT drop chấm than Wi-Fi).
     * Cấm gán SSID ngoài farm (`Dat`, `Dat-1`, `BOX 2`...).
2. **Tier 1 — Repo-Scoped Invariants (`repos: [...]`):**
   - Chỉ áp dụng đích danh cho repo sở tại.
   - Ví dụ:
     * `tiktok-luot nuoi acc`: Case 161, Case 162, cấm đè cờ dưỡng sinh toàn farm (`TAADAA_REST_DAY_NO_FOLLOW`).
     * `GPM auto`: Khóa cứng stage khởi tạo `HOTMAIL_LOGIN`, cấm skip khi có token.
     * `tools`: Khóa sàn worker timeout $\ge 300$s (`dispatch_worker_timeout_floor`).
     * Phone Farm accounts: Cấm check compound password `if bool(username) and bool(password)`, cấm gán pass TikTok ảo.
3. **Tier 2 — Path-Level Invariants (`paths: [...]`):**
   - Chỉ kích hoạt khi `git diff` (`+++ b/...`) chạm vào đúng file logic quy định (ví dụ: `*multi_machine_feed_session*`, `*dispatch_worker*`).
   - Sửa file tài liệu, test, hay submodule khác sẽ được bỏ qua, không gây nghẽn.

### B. Giữ 1 File Duy Nhất (Single Source of Truth):
- Tuyệt đối KHÔNG rải 20 file rule rác vào 20 repo con.
- Chống "Vừa đá bóng vừa thổi còi": Quản trị tập trung tại `D:/Taadaa/tools/guardgate/rules.json` tước quyền dev/bot tự sửa rule trong PR để lách gate.
- Audit 1 điểm và chi phí đồng bộ bằng 0.

### C. Cơ chế Lọc $O(1)$ trong Engine:
Trong `GuardEngine` (`guardgate/engine.py`):
```python
def _is_rule_in_scope(self, rule: Mapping[str, Any], action: Mapping[str, Any]) -> bool:
    repo = action.get("repo", "") or action.get("args", {}).get("repo", "")
    diff = action.get("diff", "") or action.get("args", {}).get("diff", "")
    rule_scope = rule.get("scope", {})
    if not rule_scope:
        return True

    target_repos = [r.lower() for r in rule_scope.get("repos", ["*"])]
    if "*" not in target_repos:
        from pathlib import Path
        repo_name = Path(repo).name.lower() if repo else ""
        if not repo_name or not any(tr in repo_name for tr in target_repos):
            return False

    target_paths = rule_scope.get("paths", ["*"])
    if "*" not in target_paths and diff:
        import fnmatch
        mod_files = [l[6:].strip() for l in diff.splitlines() if l.startswith("+++ b/")]
        if mod_files and not any(
            any(fnmatch.fnmatch(mf, tp) or tp in mf for tp in target_paths)
            for mf in mod_files
        ):
            return False

    return True
```

## 3. Schema Chuẩn Trong `rules.json`
```json
{
  "id": "case_162_usb_micro_drop_timeout_floor",
  "scope": {
    "repos": ["tiktok-luot nuoi acc"],
    "paths": ["*multi_machine_feed_session*"]
  },
  "params": {
    "variable": "connection_wait_timeout",
    "min_value": 20.0
  },
  "reason": "Khóa sàn connection_wait_timeout >= 20.0s chống sập hàng loạt khi micro-drop USB Hub (Case 162)",
  "guidance": "Khi feed bị chờ lâu/treo máy, giải quyết bằng cách kiểm tra device liveness nội bộ; TUYỆT ĐỐI KHÔNG hạ timeout micro-drop USB."
}
```

## 4. Verification & Matrix Tests
Mọi thay đổi scope bắt buộc kiểm chứng qua ma trận 5 chiều:
1. `Sửa Repo A (GPM auto)` có code vi phạm của `Repo B (Phone farm)` $\rightarrow$ **ALLOW** (Không bắn nhầm).
2. `Sửa đúng Repo B (Phone farm)` vi phạm $\rightarrow$ **DENY**.
3. `Sửa Repo A (GPM auto)` vi phạm rule của chính nó $\rightarrow$ **DENY**.
4. `Sửa Repo B` có code của Repo A $\rightarrow$ **ALLOW**.
5. `Global rule` vi phạm ở bất kỳ repo nào $\rightarrow$ **DENY 100%**.
