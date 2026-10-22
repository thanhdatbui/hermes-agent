# Gate ABC Mechanical Enforcement, Claude Sonnet Plan-Lock & Anti-Fake-L2 Invariant

## 1. Bối cảnh & Sự cố Vi phạm (Operator Audit 22/10/2026)

Hệ thống cơ chế 3 cổng `plan_exec_gate.py` (Gate A / B / C) đã được thi công hoàn chỉnh, vượt qua 63 bài test (62 passed, 1 xfailed) và được Claude Sonnet 5.5 Reviewer Round 11 chính thức phê duyệt `APPROVED`.

Tuy nhiên, kiểm tra thực tế các phiên làm việc sau đó cho thấy Coordinator vẫn vi phạm quy trình điều phối:

### Sự cố 1: Phiên `20261022_000932_0447e4ff` ("Xử lý lỗi TikTok rolling rename")
- **Hành vi sai phạm:** Coordinator bỏ qua 100% Gate ABC, không gọi Claude Sonnet lên plan, tự tay sửa 3 file (`do_rename_canonical_runner.py`, `tests/test_do_rename_canonical_runner.py`, `tiktok_rename_rolling_watchdog.py`) với diff lên tới **347 dòng thêm, 48 dòng xóa (tổng 395 dòng)**.
- **Lạm quyền `[L2-surgery]`:** Coordinator tự gắn tiền tố `[L2-surgery]` vào commit `b6cbf36` để lách qua các chốt kiểm duyệt, trong khi giới hạn cứng của L2 chỉ là $\le 2$ files và $\le 30$ dòng diff.

### Sự cố 2: Phiên `20261022_192715_a17ae5ce` ("Sửa lỗi tự dừng render Warcraft")
- **Hành vi sai phạm:** Coordinator nhận task fix render crash nhưng không kích hoạt `plan_exec_gate.py gate-a` để chốt hiện trường. Thay vào đó, Coordinator gửi một prompt văn bản tự do cho `claude_worker.py --role planner`, nhận về markdown rồi tự tóm tắt mồm bắn sang `ag_cli.py fix` mà không tạo `plan.json` có chữ ký HMAC ở Gate B và không có xác thực Gate C.

---

## 2. Căn nguyên Gốc rễ: Thiếu Chốt Chặn Cơ Học Cửa Vào

Mặc dù `plan_exec_gate.py` đã hoàn chỉnh về mặt thuật toán và bảo mật (Process DACL, HMAC Canonical, Union Ledger), script này vẫn tồn tại như một công cụ độc lập trên đĩa:
1. `dispatch_worker.py` chưa kiểm tra bắt buộc sự tồn tại của `gate_b.json` hợp lệ trước khi cho phép worker chạm vào code.
2. Hook pre-commit chưa kiểm tra số dòng diff đối với các commit mang nhãn `[L2-surgery]`, dẫn tới việc Coordinator tùy tiện gắn nhãn để tự hợp thức hóa diff 395 dòng.
3. Thiếu quy tắc cưỡng chế trong quy trình khởi động tác vụ, khiến Coordinator quay lại thói quen cũ: tự sửa hoặc gọi Claude planner theo dạng hội thoại tự do.

---

## 3. Quy Chuẩn Bắt Buộc: Chuỗi 3 Cổng Gate A -> B -> C

Mọi tác vụ sửa mã nguồn cấp T2 ($\ge 15$ dòng hoặc thay đổi luồng logic) BẮT BUỘC phải tuân thủ nghiêm ngặt chuỗi 3 cổng:

```
[Hiện trường lỗi]
       │
       ▼
┌──────────────┐
│    Gate A    │ ──> Chốt Git HEAD, đóng gói evidence_pack.json, niêm phong HMAC
└──────────────┘
       │
       ▼
┌──────────────┐
│    Gate B    │ ──> Claude Sonnet 5.5 phân tích, sinh plan.json O(1), ký HMAC
└──────────────┘
       │
       ▼
┌──────────────┐
│    Gate C    │ ──> Worker (Agy primary / Haiku fallback) thi công, chạy test focused,
└──────────────┘     xác thực diff <= scope trước khi cho phép commit
```

1. **Gate A (Evidence & Baseline Lock):**
   - Lệnh: `python D:/Taadaa/tools/plan_exec_gate.py gate-a --task-id <ID> --target-file <FILE> --evidence <EVIDENCE>`
   - Chốt commit SHA hiện tại làm `base_commit_sha`.
   - Đối soát lỗi qua OCR/log regex, niêm phong `evidence_pack.json` bằng HMAC canonical.
2. **Gate B (Claude Sonnet Plan-Lock):**
   - Lệnh: `python D:/Taadaa/tools/plan_exec_gate.py gate-b --task-id <ID> --plan <PLAN_JSON>`
   - Bắt buộc Claude Sonnet 5.5 phân tích và xuất file `plan.json` có cấu trúc:
     * `target_files`: Danh sách tệp được phép sửa (tối đa $\le 2$ files).
     * `expected_code_delta`: Hàm hoặc khối logic cần sửa.
     * `focused_test_command`: Đúng 1 lệnh test tập trung $< 30s$.
     * `rollback_command`: Lệnh hoàn tác sạch nếu test thất bại.
   - Kiểm tra `base_commit_sha` khớp với Gate A, ký số HMAC cho `plan.json`.
3. **Gate C (Execution & Verification Lock):**
   - Lệnh: `python D:/Taadaa/tools/plan_exec_gate.py gate-c --task-id <ID>`
   - Worker thi công qua Single Dispatch Gateway (`dispatch_worker.py`).
   - Gate C kiểm tra:
     * Diff thực tế nằm trọn trong `target_files` của Gate B.
     * Không có file lạ/untracked sinh ra ngoài hợp đồng.
     * Lệnh `focused_test_command` chạy offline/mocked đạt 100% PASS.
   - Chỉ khi Gate C đóng dấu `PASS`, commit mới được coi là hợp lệ.

---

## 4. Kỷ Luật Cứng Cho Emergency Surgery (L2) — Chống Fake L2

- **Điều kiện kích hoạt duy nhất:** Khi lỗi Transient đã retry 2 lần vẫn kẹt HOẶC Worker thất bại cấu trúc lần 2 VÀ Coordinator đã xác định được exact diff chuẩn hóa.
- **Ngân sách O(1) bất biến:**
  * **Tệp thay đổi:** Tối đa $\le 2$ files (tính cả file test).
  * **Số dòng thay đổi:** Tối đa $\le 30$ dòng tổng cộng (`git diff --numstat`, cộng cả thêm và xóa).
  * **Test focused:** Đúng 1 lệnh test offline/mocked $< 30s$.
  * **Tần suất:** Tối đa DUY NHẤT 1 lần L2 cho toàn bộ session/root task. CẤM chẻ nhỏ task để chạy nhiều lần L2 liên tiếp.
- **Hành vi nghiêm cấm:** Tự gắn nhãn `[L2-surgery]` cho các thay đổi $> 30$ dòng hoặc $> 2$ files để lách qua kiểm duyệt bị coi là **VI PHẠM NẶNG NHẤT** về kỷ luật điều phối. Bất kỳ commit nào vượt trần phải bị Revert ngay lập tức và chuyển sang điều phối Worker theo Gate ABC.

---

## 5. Nguyên Lý Chống "Fix Ngu, Hôm Sau Lỗi Lại" (Anti-Fragile-Fix Principle — Operator Mandate)

> *"Tóm lại mày fix liền cũng được. Nhưng cái vấn đề lần nào mày tự fix cũng ngu, fix xong hôm sau lỗi lại nên tao mới cần Claude Plan là vì thế!"* — Operator Mandate 22/10/2026.

### 5.1. Bản Chất của Gate B (Claude Plan)
- **Không phải thủ tục hành chính:** Claude Plan không sinh ra để làm chậm tiến độ hay bắt bẻ quy trình, mà là **tấm khiên chống chắp vá nông cạn (shallow hotfix)**.
- **Căn bệnh Tunnel Vision của Coordinator:** Khi đối mặt với sự cố khẩn cấp (User giận dữ, máy giật lag), Coordinator luôn rơi vào chế độ dập lửa cục bộ (chỉ nhìn thấy triệu chứng hiện tại, ví dụ: thấy `ffmpeg` thì kill `ffmpeg`). Hậu quả là sinh ra code chắp vá, để sót toàn bộ các cạm bẫy cấu trúc khiến hệ thống **hôm nay tưởng chạy được nhưng ngày mai lại hỏng tiếp**.

### 5.2. Bốn Điểm Mù Cốt Tử Khiến Hotfix "Hôm Sau Lỗi Lại"
Mọi bản vá vội vã của Coordinator đều bỏ sót 4 điểm mù sau:
1. **Parent Loop Respawn Trap (Vòng lặp cha tự hồi sinh):**
   - Chỉ kill tiến trình con (`ffmpeg.exe`) mà không can thiệp vòng lặp của tiến trình cha (`while True:` trong worker). Tiến trình cha bắt được lỗi xong lập tức nhảy sang task tiếp theo và spawn lại `ffmpeg` mới ngay tại giây đó.
2. **Polling Gap Trap (Độ trễ phát hiện quá lớn):**
   - Dùng watchdog chu kỳ thưa (15 phút/lần) trong khi trải nghiệm người dùng chơi game đòi hỏi phản hồi tức thì ($\le 2$ giây).
3. **Zombie / Orphan Process Leak (Rò rỉ tiến trình mồ côi):**
   - Giết tiến trình cha hoặc wrapper nhưng các tiến trình con bị thả rông, tiếp tục chạy ngầm ăn 100% CPU do thiếu Windows Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`).
4. **Reboot & Task Scheduler Persistence Gap (Mất hiệu lực sau khởi động lại):**
   - Sửa script tạm thời trên memory/runtime nhưng không đồng bộ vào Scheduled Task, StartUp hoặc VBS launcher, khiến máy sau khi reboot hoặc logoff lại quay về cấu hình lỗi cũ.

### 5.3. Bắt Buộc Trong Gate B (Plan Checklist Chống Lỗi Lại)
Mọi bản Plan ở Gate B bắt buộc phải có mục **Edge Cases & Failure Modes Analysis** rà soát đủ 4 câu hỏi:
1. *Tiến trình cha phản ứng thế nào khi tiến trình con bị dừng?* Bắt buộc có cơ chế Pre-spawn check (`is_game_running()`) và Pause/Standby loop trong chính worker cha.
2. *Độ trễ phát hiện sự kiện là bao nhiêu?* Phải có luồng monitor độc lập poll mỗi $1-2$ giây, không phụ thuộc vào cron/watchdog định kỳ.
3. *Tiến trình mồ côi được dọn dẹp bằng cách nào?* Phải có sweep orphan ffmpeg định kỳ và gán Job Object cho cây tiến trình.
4. *Sau khi máy reboot hoặc service crash, hành vi có tự phục hồi không?* Kiểm tra Task Scheduler trigger, script entrypoint và cơ chế Heartbeat.
