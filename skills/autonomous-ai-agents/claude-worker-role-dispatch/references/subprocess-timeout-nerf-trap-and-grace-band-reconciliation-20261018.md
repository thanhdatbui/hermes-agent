# Bẫy Hard-Timeout 60s Dàn Thợ Sửa Code & Đối Soát Grace Band Closeout Gate

**Ngày ghi nhận:** 18/10/2026  
**Nguyên nhân gốc:** Kế thừa mù quáng cấu hình 60s từ thời worker chỉ đọc/sửa text đơn giản (không chạy test, không deep think) sang worker chạy Bash + Pytest và Sol Deep Think.

---

## 1. BẪY TIMEOUT 60S TRONG `claude_worker.py`, `sol_repair.py` VÀ `ag_cli.py`

### 1.1 Hiện tượng
- Worker (`claude_worker.py --role worker`) thực tế đã hoàn thành nhiệm vụ, sửa file và chạy `pytest` pass 100% (ví dụ: pass 90/90 tests trong 13s, hoàn thành ở giây thứ 67.6).
- Nhưng tiến trình mẹ vung đao kill worker ở đúng giây 60, in lỗi: `ERROR: timed out after 60s` (exit code 124).
- Dispatcher hiểu nhầm là lỗi transient, retry lần 2 rồi fallback sang `ag_cli.py fix`.
- `ag_cli.py` lại thừa hưởng timeout 60s, chạy hết 60.5s và tiếp tục bị chém chết (exit code 124) lần 2!
- `sol_repair.py` gọi OmniRoute (:20129) với `timeout_sec: 60.0`, trong khi ChatGPT-Web Sol Deep Think cần 70–90s để suy luận và stream toàn bộ JSON patch. Kết quả: `OmniRoute call failed: timed out` (proposal `valid: false`).

### 1.2 Nguồn gốc lịch sử (Vì sao bị nerf xuống 60s?)
1. **Ngày 14/10/2026 (`haiku_worker.py`):**
   - Tool ban đầu chỉ cấp `allowed_tools: "Read,Edit"` (HOÀN TOÀN KHÔNG CÓ BASH, KHÔNG CHẠY TEST).
   - Agent ca đó quan niệm: *"Haiku sửa ốc vít O(1) chỉ mất 6–15 giây"*, kết hợp với rule *"Terminal foreground max 60s"*, nên hardcode `DEFAULT_TIMEOUT = 60`.
2. **Ngày 15/10/2026 (`claude_worker.py`, Commit `824c4ad`):**
   - Tiến hóa lên đa vai trò, mở thêm công cụ `Bash` cho Worker (`allowed_tools: "Read,Edit,Write,Bash"`) và cho phép chạy tới **15 turns**.
   - Agent copy nguyên xi `default_timeout: 60` từ `haiku_worker.py` cũ.
3. **Thực tế thời gian chạy Agentic trên Windows:**
   - Khởi động Bash MSYS + load environment: 3–5s.
   - 1 lần chạy `pytest` bộ test farm: 12–25s.
   - Vòng lặp ReAct 4–8 turns (Read -> Edit -> Bash pytest -> Phân tích -> Viết tổng kết): mỗi turn 8–15s.
   - **Tổng thời gian bắt buộc:** **65 – 120 giây**. Cấu hình 60s chắc chắn sẽ giết chết mọi worker làm việc tử tế!

### 1.3 Quy chuẩn Timeout mới (Invariants)
1. **Worker có chạy Test:** BẮT BUỘC đặt `--timeout 180` (hoặc tối thiểu 150s).
2. **Sol Repair (:20129 Deep Think):** BẮT BUỘC nâng `timeout_sec` từ 60s lên `180.0`.
3. **Gọi từ Coordinator:** Lệnh dispatch worker BẮT BUỘC bọc trong `terminal(background=True, notify_on_complete=True, timeout=300)` để không bị Coordinator Terminal Guard (chặn foreground > 60s) quật ngã.

---

## 2. ĐỐI SOÁT GRACE BAND (80–84 ĐIỂM) VS BẪY CÀY ĐIỂM 85

### 2.1 Mâu thuẫn giữa Prompt/Memory và Codebase thực tế
- **Sai lầm của Coordinator:** Nhiều phiên Coordinator bị ám ảnh bởi câu từ cũ *"Strict >= 85 (Xóa bỏ Grace Band)"*, dẫn đến việc khi Reviewer chấm 78–84 điểm thì dừng lại khóc lóc hoặc bắt Sol/Sonnet cày điểm vụn vặt (sửa docstring, telemetry râu ria).
- **Codebase thực tế đang chạy:**
  * `closeout_policy.json`: `{"threshold": 85, "grace_threshold": 80}`.
  * `gate_common.py` (Hàm cấp HMAC Token): `score >= grace_threshold (80)` là PASS.
  * `closeout_gate.py` (dòng 1722-1725): `if 80 <= total < pass_threshold: return "APPROVED", scorecard` (gắn cờ `grace_band: True`).
  * `safe_push.py` (dòng 108): Cho phép push ngay khi `score >= 80`.
  * User Profile: *"Closeout: Grace 80-84 / Mechanical test xanh auto-push, cấm lưu local khóc; CẤM SONNET CÀY ĐIỂM"*.

### 2.2 Quy tắc vận hành dứt điểm
- **Đạt Grace Band (>= 80 điểm) + Unit Test XANH 100%:** Gate tự động duyệt `APPROVED` ➔ Tự sinh HMAC Token ➔ Tự động `git push`. CẤM TUYỆT ĐỐI sửa thêm bất kỳ ký tự nào để cày lên 85!
- **Dưới 80 điểm (76–79):** Chỉ sửa các lỗi logic thực chất (như nhận diện cờ bitmask, chống traversal, chống chặn nhầm lệnh farm thật). Khi chạm ngưỡng >= 80 điểm là lập tức push, không chần chừ.

---

## 3. SCOPE CONTAMINATION TRONG PRE-CLOSEOUT (`refusing partial committed scope`)

- Khi trong repo đã có commit local chưa push (`origin/main..HEAD`), `closeout_gate.py` từ chối review cục bộ (`--files`) nếu danh sách file đó không khớp với toàn bộ scope của các commit chưa push.
- **Cách xử lý chuẩn:**
  1. Nếu commit cũ đã được review ở ca trước: BẮT BUỘC push commit cũ trước hoặc đồng bộ `origin/main` trước khi review working tree mới.
  2. Nếu là code mới của ca hiện tại: Đảm bảo working tree và commit scope đồng nhất, tránh commit dở dang một phần rồi review phần còn lại.
