# Mechanical Anti-Paralysis Architecture & Scope Lockdown (Claude Sonnet 5.5 Spec 2026-10-18)

## 1. Bối cảnh Sự cố (The Paralysis Incident 18/10/2026)
Trong phiên chốt công việc:
1. Coordinator chạy `closeout_gate.py --repo D:/Taadaa/tools --base HEAD~1` nhưng **quên cờ `--files`**. Repo có 16 dirty files từ nhiều tác vụ khác nhau khiến diff phình to > 82KB, Gate kích hoạt `[Gate Fail-Fast: DIFF_TOO_LARGE]`.
2. Khi thử gọi Claude CLI để sửa, Claude bị `CLAUDE_QUOTA_GUARD_BLOCKED` vì quota 5h đạt 86% (ngưỡng bảo vệ 85%).
3. Dù hệ thống có sẵn **Tier 2 Fallback: Antigravity CLI (`ag_cli.py fix`)** với 22/22 profiles Google Pro READY 100%, Coordinator rơi vào **hội chứng đóng băng (paralysis / Luna behavior)**: dừng hành động, quên nấc fallback, và quay ra chat than vãn với User `BLOCKED: chưa thể báo Done, diff quá lớn, quota Claude bị chặn`.
4. Sau khi User chấn chỉnh, Coordinator kích hoạt `ag_cli.py fix`, chỉ định đúng `--files`, qua Gate điểm 82 (Grace Band) và auto-push origin/main thành công.

---

## 2. Phân tích Nguyên nhân Gốc rễ (Root Cause Analysis)
- **Lỗ hổng "Tự do phát ngôn vô căn cứ" (Unchecked Speech Freedom):** Coordinator có thể tự tiện nói ra chữ `BLOCKED` mà không cần trình ra receipt máy móc chứng minh tất cả các nấc cứu hộ vật lý đã thất bại.
- **Thiếu Fail-Fast Scope Guard ở Closeout Gate:** Khi repo dirty mà gọi thiếu `--files`, gate quét trần trụi toàn bộ `git diff HEAD`, tự đẻ ra lỗi `DIFF_TOO_LARGE`.
- **Thang Fallback rời rạc:** Việc gọi Tier 1 (Claude CLI) và Tier 2 (Agy CLI) là 2 lệnh tách biệt, phụ thuộc hoàn toàn vào trí nhớ của LLM Coordinator thay vì được bọc trong một pipeline khép kín.

---

## 3. Bản thiết kế 4 Lớp Bảo vệ Cơ học (Claude Sonnet 5.5 Spec)

### Lớp 1 — Scope Guard & Auto-Scope tại `closeout_gate.py`:
- Trong `closeout_gate.py` (`extract_diff` / `main`):
  - Khi `--repo` được gọi mà người dùng **KHÔNG truyền `--files`**:
    - Kiểm tra `git status --porcelain`.
    - Nếu repo có `> 2` dirty files: **FAIL-CLOSED NGAY LẬP TỨC** tại Step 1 với thông báo rõ ràng:
      `[GATE_SCOPE_ERROR]: Repo có dirty files. BẮT BUỘC chỉ định --files <file1> <file2> để giới hạn scope O(1).`
    - Nếu repo có đúng `1..2` dirty files: **Auto-Scope tự động**, tự nạp 2 file đó vào `--files`.
  - Triệt tiêu 100% lỗi `DIFF_TOO_LARGE` do quên gõ `--files`.

### Lớp 2 — Single Pipeline Dispatcher (`remediation_dispatcher.py`):
- Gom logic điều phối thợ sửa vào 1 entrypoint duy nhất:
  `python D:/Taadaa/tools/remediation_dispatcher.py --task "..." --files ...`
- Vòng lặp cơ học nội bộ:
  - **Tier 1:** Chạy Claude Haiku 5.5 CLI. Nếu thành công -> thoát `0`.
  - **Tier 2 (Tự động):** Nếu Claude bị Quota Guard chặn (`exit 20`) hoặc timeout -> Tự động kích hoạt `ag_cli.py fix` (Antigravity Pro pool) mà **KHÔNG trả quyền về cho Coordinator**.
  - **Tier 3:** Chỉ khi CẢ Claude LẪN Antigravity đều thất bại thật sự, script mới xuất file receipt: `ladder_exhausted.receipt` chứa chữ ký số và log lỗi của cả 2 tier.

### Lớp 3 — Mechanical Speech Gate (Cấm mồm kêu BLOCKED bừa bãi):
- Trong hook bảo vệ `guard_dispatch_contract.py` hoặc post-turn validator:
  - Nếu Coordinator định gửi tin nhắn chứa từ khóa `BLOCKED`:
  - Hệ thống kiểm tra xem trên đĩa có file `ladder_exhausted.receipt` được tạo trong vòng 10 phút gần nhất hay không.
  - **Nếu KHÔNG có receipt:** Khóa họng Coordinator ngay lập tức, trả về lỗi nội bộ:
    `[SPEECH_GATE_BLOCKED]: CẤM BÁO BLOCKED! Bạn chưa đi hết thang cứu hộ (thiếu ladder_exhausted.receipt). Phải dispatch tiếp Antigravity CLI!`

### Lớp 4 — Trạng thái Máy Đọc (`ag_cli.py pool-status --json`):
- Bổ sung cờ `--json` cho `ag_cli.py pool-status` để xuất trạng thái pool (`pool_status.json`) cho script dispatcher tự kiểm tra số lượng profile READY trước khi dispatch.

---

## 4. Kỷ luật Bất biến dành cho Coordinator
1. CẤM báo BLOCKED khi chưa chạy hết thang cứu hộ (Claude CLI -> Agy CLI).
2. Khi repo có nhiều dirty files, BẮT BUỘC dùng `--files <file1> <file2>` khi gọi `closeout_gate.py`.
3. Khi Claude CLI bị Quota Guard chặn, BẮT BUỘC fallback ngay sang `ag_cli.py fix` (Antigravity Pro pool).
