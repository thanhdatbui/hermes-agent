# BÀI HỌC KIẾN TRÚC 3 CỔNG CƠ HỌC & ĐIỀU PHỐI WORKER (22/10/2026)

## 1. Hệ thống 3 Cổng Cơ học (`plan_exec_gate.py`)

Hệ thống được chuẩn hóa để điều phối quy trình phát triển mã nguồn giữa Coordinator AI và Worker AI:

* **Gate A (Empirical Ground-Truth Verification):**
  - Nhiệm vụ: Chặn đứng tình trạng báo cáo mồm. Bắt buộc kiểm chứng bằng chứng thực tế từ 4 nguồn: `file` (SHA256 range), `ocr` (WinRT OCR đọc text màn hình), `cmd` (lệnh exit code), `log` (regex pattern).
  - Khóa: Tạo `evidence_pack.json` và ký chữ ký số Canonical HMAC-SHA256 bao phủ toàn bộ các trường: `gate`, `task_id`, `status`, `plan_sha256`, `evidence_pack_sha256`, `base_commit_sha`.

* **Gate B (Plan Verification & Scope Lockdown):**
  - Nhiệm vụ: Độc quyền giao cho **Claude Sonnet 5.5** (`claude_worker.py --role planner`) lập kế hoạch `plan.json` dựa trên bằng chứng đã khóa từ Gate A.
  - Khóa:
    - Bắt buộc kiểm tra Git working tree phải sạch (clean working tree).
    - Bắt buộc có đủ danh sách file được sửa (`files_to_edit`), lệnh test nghiệm thu (`acceptance`) <30s, và lệnh rollback (`rollback`).
    - Neo giữ `base_commit_sha` vào Git Ref `refs/gates/<task_id>/a` và ghi đồng thời vào cả local ledger lẫn coordinator ledger.

* **Gate C (Acceptance & Scope Compliance):**
  - Nhiệm vụ: Nghiệm thu kết quả sau khi Worker thi công.
  - Khóa:
    - Soi `git diff` đối chiếu với `base_commit_sha` của Gate B: nếu có file bị sửa ngoài `files_to_edit`, file bị xóa lạ, hoặc rename không hợp lệ -> REJECT ngay.
    - Chạy toàn bộ các lệnh acceptance test: bất kỳ test nào fail hoặc timeout -> REJECT ngay.

---

## 2. Ranh giới Tin cậy (Trust Boundary & Threat Model)

* **Phạm vi bảo vệ thực tế:**
  - Gate A/B/C là **guardrail cơ học chống worker vô tình hoặc hợp tác** (ngăn ngừa bug phát sinh, scope creep, lách test, drift commit, hoặc vô tình sửa đè receipt).
* **Giới hạn hệ điều hành (Same-user OS Limitations):**
  - Khi Coordinator, Gate và Worker cùng chạy chung một User OS trên Windows: các thực thể như Git ref, file ledger trong `%TEMP%`, hay quyền Process DACL đều có thể bị tiến trình cùng user can thiệp nếu cố tình phá hoại.
  - Để cô lập đối kháng tuyệt đối (hostile adversary), bắt buộc phải có hạ tầng sandbox bên ngoài (Job Object Low-Integrity, AppContainer, hoặc tách biệt User OS).

---

## 3. Thứ tự Ưu tiên Worker (Single Dispatch Gateway)

Theo chỉ đạo của Operator ngày 22/10/2026:
* **Tier 1 (Primary mặc định):** **Agy CLI (`ag_cli.py fix`)**. Khi có task sửa code, hệ thống ưu tiên gọi Agy CLI thực thi trước để tận dụng tài nguyên.
* **Tier 2 (Fallback):** **Claude Haiku CLI (`claude_worker.py --role worker`)**. Chỉ kích hoạt khi Agy CLI thất bại hoặc chạm giới hạn quota.
* **Planner:** Luôn cố định là **Claude Sonnet 5.5 (`claude_worker.py --role planner`)** cho Gate B.

---

## 4. Kỷ luật Phản hồi: Chống Ghi Chép Thừa Vào Memory

* **Phản hồi của Operator:** *"Có gate cơ học r mà cập nhật memory chi v"*.
* **Bài học sâu sắc:**
  - Bộ nhớ Persistent Memory chỉ dành cho thông tin ngữ cảnh biến động, sở thích cá nhân, hoặc trạng thái vận hành chưa được code hóa.
  - Những gì đã được **cổng cơ học / code Python khóa cứng (như default argument `--primary agy` trong `dispatch_worker.py`)** thì để code tự thực thi. Tuyệt đối không ghi chép thủ công vào memory làm phình context và phân tán sự chú ý của model.
