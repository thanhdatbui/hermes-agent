# Bẫy lstrip("./") Gọt Cụt Dấu Chấm File Ẩn & Kỷ Luật Model Remediation (18/10/2026)

Đúc kết từ phiên giải quyết sự cố Closeout Gate ngày 18/10/2026.

---

## 1. Bẫy Kỹ Thuật: `lstrip("./")` Gọt Cụt Dấu Chấm Của File Ẩn (`.gitignore`, `.env`)

### Hiện Tượng:
Trong `closeout_gate.py:238`:
```python
normalized = sorted(set(str(p).replace("\\", "/").lstrip("./") for p in scope))
```
Khi scope có chứa file ẩn như `.gitignore`, `.env`, `.gitattributes`:
- Python coi `lstrip(chars)` là tập hợp các ký tự cần lột bỏ ở đầu chuỗi.
- Ký tự `.` và `/` bị lột sạch ở đầu chuỗi, dẫn đến:
  - `".gitignore".lstrip("./")` ➔ `"gitignore"`
  - `".env".lstrip("./")` ➔ `"env"`
- Khi đối chiếu với `diff-tree -z --name-only HEAD` (vốn trả về nguyên bản `.gitignore`), Gate báo lỗi:
  ```text
  ✘ binding mismatch: committed scope mismatch with git state: expected ['gitignore', 'scripts/...'], got ['.gitignore', 'scripts/...']
  ```
- Lỗi này xảy ra ở Bước 2 (Extract Diff), làm fail gate ngay trên máy local trước khi kịp gọi LLM, gây lãng phí 2 vòng chạy vô ích và làm gián đoạn pipeline.

### Khắc Phục Chuẩn Xác:
Tuyệt đối không dùng `lstrip("./")` để chuẩn hóa đường dẫn. Dùng `removeprefix` hoặc cắt chuỗi có điều kiện:
```python
p_str = str(p).replace("\\", "/")
if p_str.startswith("./"):
    p_str = p_str[2:]
```

---

## 2. Kỷ Luật Model Danh Chính Ngôn Thuận (Anti-Hallucinated Model Naming)

- **Chuẩn Farm:**
  - Claude Planner/Reviewer: **Claude Sonnet 5.5 / 3.7** (alias `--model sonnet` trong `claude_worker.py`).
  - Claude Worker: **Claude Haiku 5.5** (alias `--model haiku` trong `claude_worker.py` / `haiku_worker.py`).
  - Sol High / Auditor: **GPT-5.6 Sol Web** (`gpt-web-sol` qua OmniRoute `:20129`).
- **Cấm Tuyệt Đối:** Tự ý gán ghép hoặc nhắc tên các model lỗi thời/không tồn tại trên farm như *"Claude Sonnet 3.5"*. Sự cẩu thả trong danh xưng model làm mất tính nghiêm cẩn kỹ thuật của Coordinator.

---

## 3. Kỷ Luật Phục Hồi Strike 1-2 & Chống Nhảy Cóc Sang Worker

- **First-Responder Monopoly của Sol High:**
  - Strike 1 & 2 bắt buộc Sol High (`sol_repair.py` / `sol_worker.py`) tạo đề xuất patch O(1).
  - Nếu file `sol_repair.py` bị thiếu trên đĩa (do dọn rác untracked) hoặc `sol_worker.py` bị lỗi import:
    * **BẮT BUỘC DỪNG LẠI & BÁO CÁO NGAY:** Thông báo trung thực hiện trạng công cụ bị hỏng để khôi phục lại.
    * **CẤM TUYỆT ĐỐI:** Tự ý nhảy cóc sang Haiku Worker để sửa code đối phó nhằm che giấu công cụ hỏng.
- **Tách Lượt Cập Nhật Tiến Trình Trên Telegram (Anti-Silent Remediation Lag):**
  - Khi quy trình remediation kéo dài nhiều vòng (Vòng 1 reject ➔ Vòng 2 sửa ➔ Vòng 3 re-review), việc gom toàn bộ chuỗi chạy ngầm vào 1 turn duy nhất khiến User trên Telegram không thấy tiến độ.
  - Phải phát tín hiệu / cập nhật ngắn gọn điểm số từng vòng (ví dụ: *"Vòng 1: 76đ - Thiếu telemetry fallback, Sol đang tạo bản vá..."*) để User nắm bắt trạng thái theo thời gian thực.
