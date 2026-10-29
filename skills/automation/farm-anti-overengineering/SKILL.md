---
name: farm-anti-overengineering
description: Kỷ luật thực thi chống over-engineering và cấm viết lại script canonical trên Taadaa Farm.
---

# Farm Anti-Overengineering Discipline

## 1. Nguyên Tắc Cốt Lõi (Invariants)
- **Cấm viết lại script Canonical:** Luôn tái sử dụng các công cụ chuẩn (`inspect_machine.py`, `admin_ssh.py`, `run_avatar_batch_3accs.py`, `do_logout_account.py`, `tiktok_login_v1.py`). Cấm đẻ script ad-hoc.
- **Tiêu chuẩn Gate chuẩn O(1) & Chống Bureaucratic Theater:**
- Gate chỉ đo sự kiện quá trình thật sự (`tool_called == "browser_vision"`), tuyệt đối không dùng proxy nội dung (text OCR để đoán pixel ảnh).
- **Triệt tiêu bẫy Token Grounding Gap & Self-Fulfilling Inception:** Tuyệt đối không dùng OCR text để bảo lãnh cho ảnh visual/proposal. Khi script tự in chữ lên canvas (`cv2.putText`), OCR đọc lại đúng chữ đó tạo bằng chứng tuần hoàn giả mạo. Ảnh visual bắt buộc phải có receipt từ `browser_vision` thật của Coordinator trước khi gửi thẻ `MEDIA:`.
- Một predicate duy nhất (~15 dòng code), fail-closed với đúng 1 lệnh hành động duy nhất, cấm thông điệp mắng mỏ gây vòng lặp khóc lóc / tê liệt.
- Tách rời 100% Phiên Vận Hành (không có code delta) khỏi Closeout Code Review: tự động PASS trong < 0.2s, cấm quét commit cũ, cấm gọi Sol Repair sửa code ma.
- **Xóa bỏ triệt để Security Theater (Mật mã giả cầy trên cùng OS user):**
  - Cắt bỏ lớp DACL process memory (`win32security`) và HMAC tự ký tự duyệt: Khi Coordinator, Gate và Worker chạy chung quyền user Windows, DACL và HMAC chỉ là ảo tưởng bảo mật làm nặng máy và sinh lỗi rác.
  - Cắt bỏ cơ chế Blockchain Hash Chain (`prev_chain_hash`, `self_hash` trong log JSONL): Biến file log thành sổ cái băm SHA-256 gây sập toàn bộ luồng closeout khi có 1 dòng log ngoại lai. Hàm đọc hash phải fallback an toàn về `GENESIS` thay vì văng `RuntimeError`.
  - Bỏ chấm điểm cảm tính 85/100 của LLM Reviewer và vòng lặp Sol Repair: Thước đo duy nhất của code là kiểm thử cơ học (`py_compile` + `pytest` focused pass/fail). Dẹp sạch trường `"score": 100` trong JSON output `--operational` của `closeout_gate.py`, báo cáo chốt phiên cấm nhắc điểm số hình thức.
  - Cắt bỏ các wrapper cản trở `git push` dựa trên đọc ngược log cũ (`safe_push.py`): xóa bỏ hoàn toàn dead code `_verify_closeout_gate_approval` và audit JSONL cũ.
- **Quy Tắc Tối Cao: User Sudo Supremacy (Cấm Đảo Ngược Phân Cấp Chặn Lệnh User):**
  - Lệnh của User (`tao cho phép`, `làm luôn`, `làm đi`, `làm hết đi`, `force`, `bypass`, `xử lý đi`, `sudo`, `override`) có thẩm quyền TỐI CAO TUYỆT ĐỐI, vượt lên trên mọi rào cản hook và guardrails.
  - Mọi hook bảo vệ (`_on_pre_tool_call`) BẮT BUỘC cắm kiểm tra `_is_user_sudo_active(session_id)` tại **Ưu tiên Số 0** (dòng đầu tiên). Nếu User Sudo active -> lập tức trả về `None` (PASS), cấm tuyệt đối ném lỗi `GUARD SELF-PROTECTION` chặn ngược lệnh User.
  - CẤM cơ chế cấp vé giả cầy phức tạp (`sudo_grant.json`, HMAC token, lock file) gây kẹt chết chùm; nhận diện User Sudo trực tiếp từ nội dung tin nhắn user gần nhất trong database session.
- **Kỷ Luật Chống Bại Liệt & Chống Hỏi Thừa (Anti-Paralysis Execution):**
  - Khi User gửi `?` hoặc thể hiện bức xúc vì tiến trình dừng lại: CẤM TUYỆT ĐỐI hỏi lại *"Anh có muốn tiếp tục không?"* hay *"Làm tiếp cái gì?"*.
  - BẮT BUỘC hành động ngay lập tức: Kiểm tra session qua `preserve_in_flight_sessions`, xác định các tiến trình đang dở dang (ví dụ background upload, runner batch) và tự động resume xử lý dứt điểm.
- **Phân biệt rõ Gate cản trở vs Watchdog quan sát (BẮT BUỘC GIỮ WATCHDOG):**
  - *Gate cản trở (Nên cắt/tinh gọn):* Chặn luồng thực thi vô lý, bắt bẻ thủ tục hành chính, đòi điểm số AI.
  - *Watchdog quan sát & Hardware Safety (BẮT BUỘC GIỮ 100%):* `gate_compliance_watchdog.py` (báo cáo 6h theo dõi kỷ luật Agent gọi worker, quét root), `with_device_lock.py` (JIT lock phần cứng 80 máy), `guard_android_proxy.py` (chống lộ IP farm), `ui_policy_check.py` (cấm spam dump XML trên S7), `claude_quota_guard.py` (bảo vệ hạn mức).
  - *Safe Flags cho Quota Lookup:* Mọi hook kiểm soát CLI (`guard_claude_cli_lock.py`) bắt buộc đưa cờ `--check-quota` vào `SAFE_FLAGS` để tra cứu hạn mức local không bao giờ bị chặn nhầm.
- **Quy tắc Vòng Đời Subprocess Hook & Không Cần Restart Gateway:**
  - Các hook khai báo trong `config.yaml` (`pre_tool_call`, `post_tool_call`) được Hermes kích hoạt theo dạng CLI subprocess độc lập (`python D:/Taadaa/tools/...`).
  - Mọi thay đổi sửa chữa trên file script hook/tool có hiệu lực ngay lập tức ở lần gọi tiếp theo, **TUYỆT ĐỐI KHÔNG CẦN restart Gateway** (trừ khi can thiệp core `gateway/run.py` hoặc daemon in-memory).
- **Targeted Scoping cho Closeout v2 (`--target-file`):**
  - Khi repo có nhiều file dirty tồn đọng từ các ca làm việc trước, chạy full dirty detection sẽ gây timeout hoặc dính test fail của file khác.
  - `closeout_v2.py` bắt buộc hỗ trợ cờ `--target-file <path>` để chỉ chạy syntax compile và focused pytest cho đúng file vừa sửa trong phiên hiện tại.
- **Cấm rải Git hook (pre-push/pre-commit) phân tán vào 20 repo con (Bureaucratic Theater):** Farm vận hành hằng ngày qua Task Scheduler và Python Cron, hoàn toàn không chạy `git push`. `git push` chỉ xảy ra khi dev/agent kết thúc phiên code. Mọi chốt chặn Invariant bắt buộc tập trung tại 1 điểm duy nhất.
- **Phân định dứt khoát Regression Gate vs Protection Regression Gate:**
  - *Regression Gate:* Chạy suite unit test (`pytest`) của repo để kiểm tra tính đúng đắn của logic chức năng.
  - *Protection Regression Gate:* Quét diff cơ học bằng `GuardGate` (`D:/Taadaa/tools/guardgate/rules.json`) và `infra_regression_gate.py` để khóa cứng các luật bất biến sống còn (sàn timeout USB 20s, trần follow limit 0, cấm uiautomator dump, cấm scan đĩa diện rộng D:/, khóa cấu hình OmniRoute/Hermes). Vi phạm Invariant là đạp phanh ngay tại chỗ (DENY).
- **Budget điều phối Worker:**
  - Tối đa 1 file code, diff <= 30 dòng, 1 focused test < 30s.
  - Ngân sách <= 15 calls. Nếu trong 3 turn đầu không tìm thấy anchor rõ ràng -> BẮT BUỘC ABORT, không đốt budget mò mẫm.
  - Không tự ý mở rộng Scope: Khi gặp lỗi kẹt, chỉ giải quyết đúng blocker tại chỗ; không tự chế thêm wrapper, không tự refactor kiến trúc khi chưa có yêu cầu.

## 2. Thang Leo Thang Khi Kẹt (Escalation Ladder)
- **L0:** Retry TRANSIENT (mạng, timeout, rớt kết nối) tối đa 2 lần.
- **L1:** Re-dispatch Worker với scope chia nhỏ và Patch Contract O(1).
- **L2 (Emergency Surgery):** Coordinator tự sửa tối đa 1 file <= 30 dòng kèm 1 test focused < 30s khi đủ điều kiện.
- **L3 (BLOCKED):** Đánh dấu BLOCKED kèm bằng chứng thực tế (log/OCR/diff), chuyển sang task độc lập khác.
- **L4 (Clarify):** Chỉ dùng khi cần quyết định nghiệp vụ, thiếu credentials hoặc thao tác tốn phí tiền thật.

## 3. Tài Liệu Tham Khảo (References)
- Báo Cáo & Quy Trình Đại Phẫu Cắt Tỉa Hệ Thống Gate / Guard Over-Engineered (2026-10-27): [`references/complete-farm-gate-pruning-and-hash-chain-eradication-20261027.md`](references/complete-farm-gate-pruning-and-hash-chain-eradication-20261027.md)
- Bóc Tách Token Grounding Gap & Cắt Tỉa Security Theater: [`references/visual-gate-token-grounding-gap-and-security-theater-pruning.md`](references/visual-gate-token-grounding-gap-and-security-theater-pruning.md)
- Kỷ Luật Thiết Kế Gate Chuẩn O(1) & Tách Rời Phiên Vận Hành Khỏi Closeout Review: [`references/o1-gate-discipline-and-closeout-operational-decoupling.md`](references/o1-gate-discipline-and-closeout-operational-decoupling.md)
- Toàn bộ hồ sơ quy tắc và case study lịch sử: [`references/historical-anti-overengineering-archive.md`](references/historical-anti-overengineering-archive.md)
- Bounded Review Loop: [`references/claude-cli-bounded-review-loop.md`](references/claude-cli-bounded-review-loop.md)
- Script Codification vs Memory: [`references/script-codification-vs-memory-hygiene-and-concise-reporting-20261002.md`](references/script-codification-vs-memory-hygiene-and-concise-reporting-20261002.md)
- Quản Trị Pool Web Reverse & Kỷ Luật Cooldown Tự Động (Gemini Web Argon / ChatGPT Sol 2026-10-29): [`references/gemini-web-argon-pool-cooldown-and-cdp-population-20261029.md`](references/gemini-web-argon-pool-cooldown-and-cdp-population-20261029.md)
