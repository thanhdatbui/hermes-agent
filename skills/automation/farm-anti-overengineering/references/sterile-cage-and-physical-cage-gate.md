# Lồng Vô Trùng & Cổng Nghiệm Thu Vật Lý (Sterile Cage & Physical Cage Gate)

## Bối cảnh & Hiện tượng (Incident ngày 26-27/09/2026)
- **Coordinator (Gemini/DeepMind):** Bias for action cao, xử lý hiện trường nhanh, nhưng có tâm lý "lazy delegation" (gộp 2-3 file code ở nhiều repo khác nhau vào 1 lệnh `delegate_task` duy nhất để tiết kiệm lượt).
- **Worker (Luna / GPT-5.6 series):** Trình thuật toán/code cú pháp cao hơn một chút, nhưng khi nhận 1 cục việc to tướng không có Scope Lock thì bị **Defensive Paralysis** & **Over-engineering kinh khủng**:
  - Tự vẽ kiến trúc P1/P2/P3, session lease, lock distributed, fsync atomic, vòng lặp review Claude 58 -> 74 -> 68 điểm.
  - Sợ repo dirty, sợ git lock, đọc file dạo tốn 21 tool calls và dính timeout 1200s (20 phút) chết đứng.

---

## 1. Cơ Chế Lồng Vô Trùng (Sterile Cage 4 Tầng)

1. **Lớp 1: Scope Lock O(1) & Tiêm Prompt Phân Vai (Role Injection)**
   - Coordinator chịu 100% trách nhiệm về rủi ro và an toàn repo.
   - Worker chỉ là "thợ vặn ốc" (code surgery): DUY NHẤT 1 file code, <= 30 dòng diff, 1 lệnh focused test < 30s.
   - CẤM tạo file mới, CẤM tạo file .md, CẤM refactor/thêm abstraction, CẤM chạy lệnh git lạ (`git status`, `git log`, `git checkout`).
2. **Lớp 2: Worktree Sạch (Triệt tiêu nỗi sợ Dirty Repo)**
   - Khi repo bẩn hoặc có lock, Coordinator tạo worktree tạm: `git worktree add <dir> -b <branch> HEAD` để Worker chỉ nhìn thấy môi trường 100% sạch.
3. **Lớp 3: Hard Hook Chặn Đa File (`guard_dispatch_contract.py`)**
   - Hook tự động phân tích: nếu phát hiện >= 2 file code nghiệp vụ trong 1 lệnh `delegate_task` -> **CHẶN ĐỨNG VẬT LÝ NGAY LẬP TỨC** (`[HARD GATE #3 - MULTI-FILE BLOCKED]`).
   - Cưỡng chế Sol Plan (`SOL_PLAN_ID`), nếu Sol sập kích hoạt van an toàn `SOL_FALLBACK`.
4. **Lớp 4: Cổng Nghiệm Thu Vật Lý (`D:/Taadaa/tools/cage_gate.py`)**
   - Đạt điểm thẩm định độc lập 96/100 (APPROVED).
   - Kiểm tra `numstat <= max_lines` (mặc định 30 dòng).
   - Chặn lách luật bằng file nhị phân (`binary_not_allowed`).
   - Xác thực `--base <SHA>` bằng `git merge-base --is-ancestor BASE HEAD` (chống worker tự commit qua mặt).
   - Chống process leak trên Windows bằng `CREATE_NEW_PROCESS_GROUP` + `taskkill /F /T /PID`.
   - Exit code: 0 PASS, 1 REJECT, 2 GATE_ERROR.

---

## 2. Hoán Đổi Worker Luna / Gemini

### Cách nhanh nhất qua CLI:
- Đổi Worker sang **LUNA** (Ghim cứng `codex-luna`):
  ```bash
  hermes config set delegation.model codex-luna
  ```
- Đổi Worker về **MẶC ĐỊNH (Combo `omni-worker` / Gemini ưu tiên)**:
  ```bash
  hermes config set delegation.model omni-worker
  ```

### Lưu ý trong `config.yaml`:
- Provider `omni` bắt buộc phải khai báo model trong `models:` (ví dụ `codex-luna: {context_length: 256000}`) thì Hermes mới route đúng, tránh bị fallback ngầm về model Coordinator.
