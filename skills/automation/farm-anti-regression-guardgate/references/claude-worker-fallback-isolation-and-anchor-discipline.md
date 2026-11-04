# Kỷ Luật Cô Lập Fallback Claude Worker vs Advisor & Cơ Chế Anchor Comment Định Danh

## 1. Sự Cố Mạo Danh Cố Vấn Claude Khi Hết Quota (2026-11-04)
- **Hiện tượng:** Khi Operator triệu tập Hội đồng Cố vấn qua `consult_advisor.py`, Claude CLI đã logout / hết quota. Tuy nhiên, `claude_worker.py` âm thầm kích hoạt `fallback_to_antigravity(args, reason="quota_gate", role="reviewer")`, chạy `ag_cli.py ask` bằng Profile `acc_02` (Gemini-3.8-Flash qua proxy IDE).
- **Hậu quả:** Wrapper `consult_advisor.py` vẫn gắn nhãn `🟣 [ADVISOR CLAUDE — SONNET / CLI]`, khiến Operator hiểu nhầm rằng Claude CLI thật đang chạy và đang trừ tiền vào tài khoản Claude nạp cho người nhà.
- **Khắc phục triệt để:**
  * Sửa hàm `fallback_to_antigravity` trong `D:/Taadaa/tools/claude_worker.py` (Commit `e3a42b4`):
    ```python
    def fallback_to_antigravity(args: argparse.Namespace, reason: str = "quota_gate", role: str = "worker") -> int:
        if role != "worker":
            print(f"[QUOTA_GATE] Refuse ag_cli fallback for non-worker role: {role}", file=sys.stderr)
            return EXIT_QUOTA_BLOCKED
    ```
  * Chỉ DUY NHẤT `role == "worker"` mới được fallback sang `ag_cli.py fix` để sửa code.
  * Các role `planner` và `reviewer` khi hết quota/lỗi phải báo cáo trung thực: `Advisor Claude CLI: unavailable`, cấm giả mạo danh xưng.

---

## 2. Tinh Gọn Hệ Thống Gate: Thống Nhất 2 Trụ Cột Thay Vì Over-Engineering
- **Vấn đề over-engineering:** Các phiên trước sinh ra quá nhiều danh xưng mơ hồ (*Regression Gate, Protection Regression Gate, Invariant Rule, GuardGate...*), gây nhiễu loạn nhận thức.
- **Thống nhất đúng 2 trụ cột:**
  1. **Trụ cột 1 — GuardGate (`rules.json`):** Vật cản tĩnh kiểm tra diff trong `< 0.05s`.
  2. **Trụ cột 2 — Pytest Suite:** Kiểm thử hành vi động của logic nghiệp vụ.
  3. **Điểm kiểm duyệt duy nhất:** `closeout_gate.py` (`closeout_v2.py`) kiểm tra cả 2 trước khi commit/push.

---

## 3. Quy Chuẩn Comment Định Danh Làm Anchor Bất Biến
- **Comment Định Danh làm Anchor Scoped:**
  * Thay vì quét toàn bộ file làm regex dễ gãy hoặc cào git log $O(C \times L)$ làm phình token, mỗi khối logic quan trọng hoặc đoạn fix bug hiểm bắt buộc có banner:
    ```python
    # ── BƯỚC 3: THÊM TÀI KHOẢN (BENTO SWITCHER SAFE FALLBACK) ──
    # [INVARIANT: BENTO_SWITCHER_FALLBACK]
    ```
  * Rule trong `rules.json` gắn matcher theo anchor này, đảm bảo regex kiểm tra tập trung, không bị vỡ do format hay khoảng trắng ở các phần code khác.
  * Test case tương ứng trong `tests/` mock và assert đúng hành vi của bước đó.
