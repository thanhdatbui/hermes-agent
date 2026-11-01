# Cấm Shell am instrument Cho UiAutomator, Khắc Phục Lỗi ATX 502 & Bản Vá GuardGate (2026-11-01)

## 1. Bản chất sự cố kỹ thuật
- Khi thiết bị Samsung S7 (Android 7/8, RAM 4GB) chạy TikTok 47.x, daemon nền `atx-agent` (cổng 7912) và stub `com.github.uiautomator` rất dễ bị Linux kernel giải phóng bộ nhớ (`SIGKILL 137`).
- Các lệnh gọi JSON-RPC `/jsonrpc/0` ném ngoại lệ `HTTP Error 502: Bad Gateway`.
- **Hành vi sai lầm của Agent:**
  Tự ý gọi lệnh shell qua ADB:
  `adb shell am instrument -w -r -e debug false -e class com.github.uiautomator.stub.Stub com.github.uiautomator.test/...AndroidJUnitRunner`
  để kích hoạt lại stub. Lệnh này gây nghẽn adapter ADB, làm treo máy, vi phạm Invariant chống uiautomator ngầm và bị User chấn chỉnh nghiêm khắc.

## 2. Bản vá GuardGate cơ giới hóa (Commit 2026-11-01)
- Đã mở rộng rule `case_invariant_prohibit_shell_uiautomator_dump` trong `D:/Taadaa/tools/guardgate/rules.json`:
  - Pattern mới: `(?i)(uiautomator[\s'",]+dump|import\s+uiautomator2|from\s+uiautomator2|am\s+instrument\s+.*uiautomator)`
- Đã thêm `"am instrument"` vào `BANNED_TOKENS` trong `D:/Taadaa/tools/ui_policy_check.py` kèm chuẩn hóa whitespace `re.sub(r"\s+", " ", line.lower())` chống lách dấu cách.
- Reviewer độc lập (Advisor Gate) đã thẩm định và phê duyệt: **88/100 (APPROVED)**.

## 3. Quy trình Auto-Recovery Chuẩn O(1) khi gặp 502
Tuyệt đối CẤM gõ `am instrument` bằng tay. BẮT BUỘC dùng hàm canonical chuẩn trong `automation_core.persistent_ui`:
```python
from automation_core.persistent_ui import reset_atx_agent
from automation_core.adb import AdbClient

client = AdbClient(adb_path='adb', serial=serial)
reset_atx_agent(client, timeout=15)
```
Hàm này tự động:
1. `am force-stop` các stub package `com.github.uiautomator`.
2. Dọn process `atx-agent` và `uiautomator`.
3. Chạy lại daemon `/data/local/tmp/atx-agent server -d`.
4. Kích hoạt stub an toàn bằng `monkey -p com.github.uiautomator 1` (chuẩn Android 7/8, không dùng shell instrument).
