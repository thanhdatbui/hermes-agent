# Operator Mandate "Gọi Planner Vào" & Evidence-Staging Protocol (2026-10-21)

## 1. Bối Cảnh Thực Tế & Lệnh Trực Tiếp Từ Operator
Khi Operator đối soát tiến độ farm hoặc phát hiện các vấn đề kiến trúc mang tính hệ thống (ví dụ: bẫy kẹt receipt dở dang giam lỏng 18 máy suốt 16 ngày, hoặc thiết bị rớt socket transport ADB chỉ được cứu gián đoạn sau khi có lỗi), Operator ra lệnh trực tiếp:
> *"Các máy đc cứu là đã thiết kế script tự động cứu chưa chứ k lẽ chạy lỗi ms đi cứu? Gọi planner vào"*

Lệnh `"Gọi planner vào"` là một chỉ thị điều phối đặc biệt (High-Precedence Operational Trigger). Nó kích hoạt ngay lập tức cơ chế **Claude Sonnet 5.5 Planner** và cấm tiệt Gemini Coordinator tự ý lên plan chắp vá hay tự tiện sửa code.

---

## 2. Quy Trình 3 Bước Xử Lý Lệnh "Gọi Planner Vào"

```
[Operator: "Gọi planner vào"]
       │
       ▼
[Bước 1: Gemini Gom Evidence]
  - Thu thập file:line, logs, error states, công cụ hiện có.
  - Ghi toàn văn ra file đĩa: D:/Taadaa/tools/evidence_planner_prompt.txt
  - *CẤM SUY DIỄN NGUYÊN NHÂN, CẤM KẾT LUẬN GIẢI PHÁP*
       │
       ▼
[Bước 2: Dispatch Claude Planner Sonnet 5.5]
  - python D:/Taadaa/tools/claude_worker.py --role planner --max-turns 10 --timeout 1200 ...
  - BẮT BUỘC: background=True, notify_on_complete=True
  - Chỉ định file plan đích: .hermes/plans/YYYY-MM-DD_<slug>.md
       │
       ▼
[Bước 3: Nhả Session & Đợi Harness Wakeup]
  - Báo cáo ngắn gọn cho Operator: đã dispatch Planner PID <x>, mục tiêu nạp vào.
  - Kết thúc lượt trả lời để harness tự đánh thức khi Planner hoàn tất.
  - Tuyệt đối CẤM tự ý code hay dispatch worker thi công khi Plan chưa được phê duyệt.
```

---

## 3. Các Cạm Bẫy Kỹ Thuật Khi Dispatch Planner & Cách Khắc Phục

### A. Cạm Bẫy Giới Hạn Chiều Dài Dòng Lệnh Windows (`lpCommandLine` 32,767 ký tự & Multiline Truncation)
- **Hiện tượng:** Nếu Coordinator nội suy toàn bộ log, bối cảnh, và các đoạn code vào chuỗi command `-p "..."`, trên Windows MSYS bash prompt sẽ bị ngắt sau dòng đầu tiên hoặc ném lỗi `The command line is too long.`.
- **Kỹ thuật Evidence-Staging (Khắc phục triệt để):**
  Coordinator gom toàn bộ dữ liệu hiện trường và yêu cầu kiến trúc vào một file text thuần ASCII trên đĩa:
  `D:/Taadaa/tools/evidence_planner_prompt.txt`.
  Prompt truyền vào CLI chỉ là một dòng mệnh lệnh duy nhất:
  ```bash
  python D:/Taadaa/tools/claude_worker.py --role planner --max-turns 10 --timeout 1200 "Read D:/Taadaa/tools/evidence_planner_prompt.txt and design the complete architectural plan. Write the final markdown plan to D:/Taadaa/.hermes/plans/<date>_<slug>.md. Follow all 6 required sections: RCA, Non-Goals, Atomic Steps O(1), Failure Modes, Acceptance Criteria, Rollback."
  ```

### B. Cạm Bẫy `GUARD_FOREGROUND_TIMEOUT_EXCEEDED` (> 60s)
- **Hiện tượng:** Quá trình reasoning sâu của Claude Sonnet 5.5 khi đọc file và xây dựng kiến trúc cần từ 40–120s. Nếu chạy foreground với timeout > 60s, Host Guard sẽ chặn đứng lệnh (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`).
- **Khắc phục:** BẮT BUỘC gọi qua `terminal(background=True, notify_on_complete=True, timeout=1200)`.

### C. 6 Thành Phần Bắt Buộc Của Bản Vẽ Do Planner Xuất Bản
Một bản plan được coi là hợp lệ khi và chỉ khi có đầy đủ 6 phần:
1. **Root Cause Analysis (RCA):** Dẫn chứng chính xác `file:line` gây ra sự cố thực tế.
2. **Non-Goals:** Ranh giới phạm vi nghiêm ngặt — những thứ cấm đụng tới (không đụng file nhạy cảm, không quét đĩa diện rộng, không phá vỡ logic an toàn).
3. **Atomic Steps O(1):** Chia nhỏ thành từng bước thi công độc lập cho Worker Haiku 5.5 ($\le 2$ files, $\le 30$ dòng diff mỗi bước).
4. **Failure Modes & Fail-Closed:** Định nghĩa rõ hành vi khi gặp trạng thái lạ (stale lock, parse error, timeout) phải fail-closed an toàn, không được ngộ nhận PASS.
5. **Acceptance Criteria:** Các câu lệnh test thực tế chạy được kèm output kỳ vọng (không mô tả văn xuôi chung chung).
6. **Rollback Plan:** Lệnh hoàn nguyên trạng thái ngay lập tức nếu bước thi công gặp sự cố.

---

## 4. Case Study Thực Chiến (2026-10-21)
- **Đề bài:** Tự động hóa dọn dẹp Idempotency Receipt Trap (`post-attempts/` kẹt > 24h) và Pre-Session Auto-Recovery cho thiết bị treo socket ADB.
- **Thực thi:**
  - Coordinator gom bằng chứng về `state_machine.py`, `post-attempts/*.json`, `recover_stuck_s7.py`, và `tiktok_runner.py` vào `evidence_planner_prompt.txt`.
  - Dispatch Claude Sonnet 5.5 Planner (`proc_636ab66b6061`) xuất plan ra `D:/Taadaa/.hermes/plans/2026-10-21_farm-auto-recovery-and-receipt-lifecycle.md`.
  - Đảm bảo hệ thống đi đúng quy trình phân vai, triệt tiêu hoàn toàn thói quen tự sửa ngọn của Gemini.
