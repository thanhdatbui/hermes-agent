# Handoff Session & Clean-Room Caging for Worker (Luna/Codex)

## Bối cảnh & Hiện tượng (2026-09-27)
- **Gemini (Coordinator):** Bias for action, thực dụng, xông xáo, chẩn đoán O(1), không sợ dirty repo, xử lý sự cố hiện trường tốt. Tuy nhiên dễ mắc tật "tiết kiệm lượt" (lazy delegation), gộp 2-3 file code ở nhiều repo vào 1 lần `delegate_task`.
- **Luna (gpt-5.6-luna / GPT series):** Trình thuật toán/code thuần nhỉnh hơn Gemini một chút. Nhưng khi làm Coordinator thì bị:
  1. *Defensive Paralysis (tê liệt phòng thủ):* Thấy dirty repo, git lock, cảnh báo an toàn là sợ trách nhiệm, từ chối làm hoặc viện cớ đòi xác nhận.
  2. *Over-engineering:* Tự đẻ ra kiến trúc P1/P2/P3, session lease, distributed lock, fsync directory... sa lầy vào review loops mà bỏ bê mục tiêu thực tế.

---

## 1. Quy trình Handoff an toàn từ Session cũ (Luna -> Gemini)
**TUYỆT ĐỐI KHÔNG RESUME SESSION CŨ.** Session cũ chứa context bị nhiễm độc (tranh cãi review, lock, giải thích dài dòng).
Phải mở session mới (`/new`) và thực hiện handoff 4 bước:

1. **Đóng băng session cũ:** Gõ `/stop` bên Telegram topic của session cũ để ngắt các background worker/process đang chạy, tránh 2 agent đè cùng 1 repo.
2. **Cất code dở sang nhánh riêng:**
   ```bash
   git switch -c wip/luna-<sid> && git add -A && git commit -m "WIP luna <sid>"
   git switch master # Trở về nhánh chính sạch
   ```
3. **Dọn stale lock an toàn (Xử lý dứt điểm orphan index.lock trên Windows/Git Bash):**
   ```bash
   # Nếu git switch/commit báo "fatal: Unable to create '.git/index.lock': File exists"
   # Kiểm tra xem có tiến trình git nào đang chạy ngầm không:
   ps aux | grep -i git
   # Nếu không có git process nào (chỉ là lock mồ côi do crash / session trước ngắt ngang):
   rm -f .git/index.lock
   # Sau đó thực hiện commit và switch bình thường:
   git add -A && git commit -m "wip: backup luna state before handoff"
   git switch master
   ```
4. **Bàn giao ngắn gọn 5 dòng vào session Gemini mới:**
   - Mục tiêu gốc của User (trích từ tin nhắn user đầu tiên).
   - Trạng thái repo thật (nhánh main sạch, code cũ ở `wip/luna-...`).
   - Việc hiện trường đang đứng (máy nào, flow nào).
   - Ranh giới (Scope Lock): Sửa đúng hàm/file X, cấm over-engineering P1/P2/P3, budget <= 30 dòng.
   - Chỉ thị: Bỏ qua toàn bộ kiến trúc thừa của session cũ, chỉ làm việc nhỏ nhất để thông luồng, tiêu chí test <30s pass.

---

## 2. "Lồng Vô Trùng" 4 Tầng Ép Luna Làm Thợ (Worker Caging)

Để khai thác năng lực viết code của Luna mà không bị bệnh over-engineering hay từ chối làm:

### Tầng 0: Git Worktree Cô Lập (Xóa bỏ hoàn toàn nỗi sợ Dirty)
Coordinator tạo một worktree riêng từ commit sạch:
```bash
git worktree add /tmp/cage/<task_id> -b cage/<task_id> HEAD
```
Luna chỉ được nhìn thấy thư mục này. Không có file dirty của người khác, không có lock lạ -> Triệt tiêu 100% cớ từ chối.

### Tầng 1: Tước Quyền & Hạ Reasoning Effort
- Trong `delegate_task`: chỉ cấp `toolsets=["file", "terminal"]`.
- CẤM cấp `delegate_task` (không cho tự gọi Claude review vòng lặp).
- CẤM `browser`, `web_search`, `memory`. Subagent tự nhiên không có `clarify` nên không thể hỏi ngược user.
- **Reasoning Effort:** Giữ ở mức `medium` (đã config trong `delegation.reasoning_effort: medium`) để cắt bỏ overthinking.

### Tầng 2: Hard Hook Chặn Đa File & Cưỡng Chế Sol Plan (`guard_dispatch_contract.py`)
Án ngữ trước cửa `delegate_task`:
1. **Khóa chặn đa file (Anti-Multi-File):** Nếu Coordinator gộp $\ge 2$ file code nghiệp vụ trong 1 lệnh -> Hook CHẶN VẬT LÝ NGAY LẬP TỨC (`[HARD GATE #3 - MULTI-FILE BLOCKED]`), ép chẻ nhỏ 1 file/task.
2. **Cưỡng chế Sol Plan:** Bắt buộc có `SOL_PLAN_ID` (tự động gọi Sol Web :20129) hoặc kích hoạt van an toàn `SOL_FALLBACK` khi Sol sập.
3. **Tiêm Patch Contract Phân Vai Rõ Ràng:**
```text
BẠN LÀ WORKER (THỢ VẶN ỐC), KHÔNG PHẢI KIẾN TRÚC SƯ.

PHÂN CHIA TRÁCH NHIỆM:
- Coordinator chịu trách nhiệm 100% về an toàn repo, rủi ro, merge và kiến trúc. Trạng thái repo đã được kiểm tra an toàn. ĐÓ KHÔNG PHẢI VIỆC CỦA BẠN.
- Bạn chỉ chịu trách nhiệm: Tạo diff nhỏ nhất để FOCUSED_TEST vượt qua.

RÀNG BUỘC CỨNG:
1. Chỉ được sửa đúng các file trong danh sách: {files_allow}.
2. CẤM tạo file mới, CẤM tạo file .md, CẤM refactor/đổi tên hàm, CẤM thêm abstraction/class.
3. CẤM chạy bất kỳ lệnh git nào ngoài `git diff` (CẤM git status, git log, git checkout).
4. Nếu có lo ngại: Ghi vào dòng NOTE rồi BẮT BUỘC LÀM TIẾP, CẤM DỪNG LẠI.
5. Chỉ được báo BLOCKED với 3 lý do: FILE_MISSING | TEST_COMMAND_BROKEN | GOAL_CONTRADICTS_EVIDENCE.
6. Budget: Tối đa 5 tool calls, <= 30 dòng code thay đổi.
```

### Tầng 3: Cổng Nghiệm Thu Vật Lý Bằng Code Script (`D:/Taadaa/tools/cage_gate.py`)
Sau khi Worker nộp kết quả, Coordinator chạy script nghiệm thu vật lý độc lập (đã đạt **APPROVED 96/100** từ Sol High Senior Reviewer):
```bash
python D:/Taadaa/tools/cage_gate.py --target-file <file> --test-cmd "<lenh_test_duoi_30s>" --base <SHA>
```
Script tự động kiểm tra nghiêm ngặt:
1. **Diff Scope:** Chỉ duy nhất `--target-file` được sửa (phát hiện cả untracked, cấm file `.md`, cấm file lạ).
2. **Diff Budget:** Tổng dòng thêm + xóa $\le 30$ dòng (mặc định `--max-lines 30`). Chống lách bằng file binary (`binary_not_allowed`).
3. **Chống Worker commit qua mặt:** Kiểm tra `--base` SHA và xác thực `git merge-base --is-ancestor <base> HEAD`.
4. **An toàn Test & Process Tree:** Chạy test với `stdin=DEVNULL`, stdout/stderr ghi file tạm chống deadlock pipe. Trên Windows dùng `CREATE_NEW_PROCESS_GROUP` + `taskkill /F /T /PID` khi timeout (30s) để triệt tiêu process leak; trên Linux dùng `start_new_session=True` + `os.killpg(SIGKILL)`.
5. **Fail-Closed:** Exit code 0 (APPROVED/PASS), Exit code 1 (REJECTED), Exit code 2 (GATE_ERROR).
- **PASS:** Coordinator cherry-pick diff về nhánh chính, dọn worktree.
- **FAIL:** Gửi lỗi terminal lại cho Worker sửa duy nhất 1 lần. Fail lần 2 -> Coordinator tự làm.

---

## 3. Hoán Đổi Worker Nhanh
- Đổi sang **LUNA**: `hermes config set delegation.model codex-luna`
- Đổi về **MẶC ĐỊNH**: `hermes config set delegation.model omni-worker`
- **Pitfall Routing:** Trong `config.yaml`, provider `omni` bắt buộc phải khai báo model trong `models:` (ví dụ `codex-luna: {context_length: 256000}`) và gán `delegation.provider: custom:omni` thì Hermes mới route đúng, tránh bị fallback ngầm về model Coordinator.

---

## 4. Tác Động Khi Worker Là Gemini (Không Phải Luna)
- **Hoàn toàn KHÔNG bị ảnh hưởng tiêu cực, ngược lại càng an toàn hơn gấp bội:**
  - Lồng vô trùng giúp **chữa đúng điểm yếu "tự chế biến"** của Gemini (cắt bỏ tật tự refactor file xung quanh hay mở rộng phạm vi).
  - Bản tiêm phân vai (*"Coordinator chịu 100% trách nhiệm an toàn, worker chỉ cần làm pass test"*) giải tỏa áp lực tâm lý cho cả hai: Luna hết tê liệt/sợ trách nhiệm, còn Gemini thì bớt tài lanh.
  - Cổng nghiệm thu `cage_gate.py` chạy bằng Python thuần, đánh giá khách quan dựa trên code thật, không phụ thuộc vào model nào nộp bài.

---

## 5. Quy Tắc Phân Vai Tối Thượng (Rule of Thumb)
- **Hiện trường Farm, ADB, Cron, Config, Sửa gấp ("Ống nước 5 phút"):** 100% để **Gemini** tự làm.
- **Chỉ gọi Luna làm Worker khi:** Bài toán thuật toán/hàm thuần hóc búa, regex phức tạp, giới hạn <= 2 file và có sẵn test unit rõ ràng.
