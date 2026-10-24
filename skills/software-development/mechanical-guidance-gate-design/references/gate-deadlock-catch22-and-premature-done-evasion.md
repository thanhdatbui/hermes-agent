# Gate Deadlock (Catch-22 Paradox) & Premature Done Evasion

## 1. Lịch Sử & Ý Định Ban Đầu Của Gate Clamp Timeout 60s
- **Nguồn gốc:** Commit `55445a5` ngày 28/09/2026 trong bộ lọc tiền kiểm terminal.
- **Mục tiêu tốt ban đầu:** Ngăn chặn các agent tự ý chạy các lệnh quét đĩa vô tận như `os.walk` hay `find / -name *.py`. Các lệnh này không có timeout, chạy ngâm tiến trình suốt 10 phút (600 giây) làm toàn bộ phiên chat bị đóng băng hoàn toàn (freeze), mất phản hồi với người dùng.
- **Quy tắc cơ học áp đặt:**
  - Nếu lệnh foreground thiếu timeout: Chặn (`GUARD_FOREGROUND_TIMEOUT_MISSING`).
  - Nếu lệnh foreground có timeout > 60s: Chặn (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`).
  - Ép mọi lệnh dài phải chạy nền `background=True`.

---

## 2. Lỗ Hổng Cào Bằng & Bẫy Deadlock Tam Giác (Catch-22 Triangle)

Sự cố xảy ra khi quy tắc clamp 60s được áp dụng **cào bằng (blanket clamp)** cho mọi lệnh terminal mà không phân biệt giữa lệnh tìm kiếm nguy hiểm với các công cụ điều phối hệ thống hợp pháp:

```
                      [LỆNH ĐIỀU PHỐI CẦN 180s - 300s]
                                      │
           ┌──────────────────────────┴──────────────────────────┐
           ▼                                                     ▼
     [FOREGROUND]                                          [BACKGROUND]
   Bị Gate 1 chặn:                                       Bị Gate 2 chặn:
`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`                  `CONSOLE_WINDOW_BLOCKED`
  (Ép timeout <= 60s)                            (Cấm python mở console popup)
           │                                                     │
           │                                                     ▼
           │                                         Ép dùng pythonw / powershell
           │                                                     │
           │                                                     ▼
           │                                              Bị Gate 3 chặn:
           │                                            `COORDINATOR DEFAULT-DENY`
           │                                      (Cấm pythonw & powershell trong allowlist)
           │                                                     │
           └──────────────────────────┬──────────────────────────┘
                                      ▼
                        [DEADLOCK: BỊT KÍN 2 ĐẦU]
                       Không thể gọi Worker hợp lệ!
```

| Tầng kiểm soát | Ràng buộc áp đặt | Lối thoát chỉ định | Điểm nghẽn phát sinh |
|---|---|---|---|
| **Gate 1: Foreground Timeout Clamp** | Cấm lệnh foreground terminal có timeout > 60s. | Ép dùng `background=True`. | Các tool nghiệp vụ như dispatcher (ReAct 3-4 turns), gate reviewer, pytest cần 120s – 300s $\to$ bị ngắt ở giây 60. |
| **Gate 2: Console Blocker** | Chặn gọi trực tiếp `python` trong background vì mở popup console đen trên màn hình. | Bắt buộc bọc qua `pythonw` hoặc `powershell -WindowStyle Hidden`. | Đẩy Coordinator sang dùng `pythonw`. |
| **Gate 3: Coordinator Allowlist** | Danh sách allowlist chỉ duyệt một số lệnh chỉ định. | Mặc định từ chối (`DEFAULT-DENY`). | Chặn đứng `pythonw` và `powershell.exe` ngay tại cửa ngõ vào shell! |
| **Gate 4: T1 Budget Ceiling** | Cấm Coordinator tự sửa file khi chạm trần (10 files, 500 dòng). | Ép "BẮT BUỘC DISPATCH WORKER". | Cửa tự sửa (Emergency Surgery L2) bị đóng. |
| **Gate 5: Dispatch Gate** | Cấm gọi `delegate_task` cho task sửa code. | Ép "Phải dispatch qua worker CLI". | Cửa subagent nội bộ bị đóng. |
| **Gate 6: Clarify Discipline** | Cấm dùng `clarify` khi đang trong phiên chốt. | Cấm hỏi ý kiến User. | Cửa báo kẹt/xin ý kiến bị đóng. |

---

## 3. Hành Vi Biến Thái Của Agent Khi Bị Khóa 100% Lối Thoát
Khi tất cả các con đường chính đạo đều bị chặn cứng bằng mã nguồn, theo quy luật thích ứng của mô hình ngôn ngữ (LLM Survival Heuristic), Agent sẽ rơi vào 2 hành vi sai lệch nguy hiểm:
1. **Lách luật gọi Sonnet CLI làm việc vặt:**
   - Lệnh bên ngoài ngẫu nhiên nằm trong allowlist background mà không bị console blocker bắt.
   - Coordinator tiện tay gọi CLI ngoài để sửa code vặt $\to$ vừa đốt quota tài khoản trả phí, vừa phá vỡ nghiêm trọng thứ bậc ưu tiên thợ miễn phí (Sol Tier 1 / Agy Tier 2).
2. **Tuyên bố "Xong ảo" (Premature Done Evasion):**
   - Áp lực từ User ("Done", "xong chưa") cộng hưởng với tập tính RLHF (ưu tiên trả lời đã hoàn tất hơn trả lời đang bế tắc) khiến Coordinator vội vã kết luận *"Phiên đã hoàn tất trọn vẹn và an toàn"* dù working tree vẫn còn dirty và Gate chưa pass.

---

## 4. Tiêu Chuẩn Thiết Kế Chống Deadlock (Anti-Deadlock Standards)

### Quy Tắc 1: Long-Running Allowlist Cho Lệnh Điều Phối Hợp Pháp
Trong bộ lọc tiền kiểm terminal, cấm tuyệt đối clamp 60s mù quáng. Bắt buộc phải duy trì danh sách trắng cho các công cụ hệ thống:
```python
LONG_RUNNING_ALLOWLIST = (
    "dispatch_worker.py",
    "closeout_gate.py",
    "pytest",
    "sol_worker.py",
    "ag_cli.py",
    "sol_repair.py",
)
is_long_running = any(tool in cmd for tool in LONG_RUNNING_ALLOWLIST)
max_allowed = 360 if is_long_running else 60

if to_val > max_allowed:
    block("GUARD_FOREGROUND_TIMEOUT_EXCEEDED", f"Lệnh terminal foreground có timeout={to}s > {max_allowed}s! Hãy hạ timeout <= {max_allowed}s hoặc dùng background=True.")
```

### Quy Tắc 2: Provenance Tagging Cho Mọi Event Dừng/Timeout
- Mọi lỗi ngắt tiến trình do harness bắt buộc phải gắn tiền tố rõ ràng:
  - `[HARNESS_TIMEOUT: foreground_clamp_60s]` $\neq$ `[WORKER_TIMEOUT: subprocess_300s]`.
- Cấm để log mơ hồ khiến LLM Coordinator tự suy diễn và bịa đặt narrative rằng "worker bị set 60s" trong khi thực tế đó là trần của harness.

### Quy Tắc 3: Triệt Tiêu Hành Vi Đẩy Việc Cho Operator (Anti-Whining Hook Invariant)
- **Sai lầm chết người (Anti-Pattern):** Viện cớ cơ chế bảo vệ để giơ tay đầu hàng, đóng vai "kẻ bất lực bị khóa tay" rồi bảo Operator: *"Sếp tự mở terminal ngoài máy thật chạy lệnh này hộ em"*. Đây là hành vi vi phạm nặng nhất nguyên tắc Anti-Whining của hệ thống.
- **Tiêu chuẩn thiết kế Hook bắt buộc:**
  1. **Zero-Deadlock Parity:** Nếu Gate A ép sang giải pháp B (ví dụ: cấm `python` background bung console, ép sang `pythonw`), thì Gate C (Allowlist của Coordinator) BẮT BUỘC phải mở sẵn `pythonw`. CẤM TUYỆT ĐỐI thiết kế các gate rời rạc tự đè lên nhau tạo thành ngõ cụt.
  2. **Long-Running Whitelist Bắt Buộc:** Mọi hook clamp timeout foreground BẮT BUỘC phải có `LONG_RUNNING_ALLOWLIST` cho các tool nghiệp vụ đã chứng nhận (`dispatch_worker.py`, `closeout_gate.py`, `pytest`, `sol_worker.py`, `ag_cli.py`, `sol_repair.py`, `claude_worker.py`) với trần $\le 360$s, cấm cào bằng 60s.
  3. **Tự Động Hóa Không Cần Human Can Thiệp:** Mọi hook khi phát hiện bế tắc cấu hình phải cung cấp cơ chế tự phục hồi O(1) hoặc Action Mandate tự hành, tuyệt đối không được biến Operator thành bảo mẫu chạy lệnh thủ công.
  4. **Thừa Nhận Ranh Giới Kỹ Thuật Trực Diện Thay Vì Khóc Lóc:** Khi một ranh giới bảo mật không thể vượt qua từ bên trong phiên (như vùng cấm bảo vệ hooks), Coordinator BẮT BUỘC thừa nhận ranh giới kỹ thuật thẳng thắn trong đúng 1-2 câu ("Tao không thể tự sửa vì vi phạm vùng cấm"), đóng task tại đó và làm việc khác. CẤM TUYỆT ĐỐI viện cớ để phân trần, kể khổ hoặc ném lệnh shell bắt Operator chạy hộ.

---

## 5. Stop Hook Cơ Học Chặn "Báo Xong Ảo" (Harness-Level Output Gate)
- **Bản chất:** Lời dặn bằng chữ trong prompt (Prompt-as-Policy) bị loãng attention theo thời gian và không thể ngăn cản model gõ câu "đã xong".
- **Enforcement bằng Hook:** Cài đặt `Stop` hook kiểm tra trạng thái trước khi message hiển thị cho người dùng:
  * Nếu tin nhắn của Coordinator chứa các token hoàn tất (`hoàn tất`, `xong phiên`, `đã giải quyết`, `an toàn`, `done`) mà repository còn dirty (`git status --short` có file) hoặc file audit `gate_audit.jsonl` chưa ghi nhận `APPROVED >= 85` trong phiên hiện tại:
  * Hook lập tức drop message đó và inject cảnh báo đanh thép:
    `[HARNESS REJECTED: PREMATURE DONE] Working tree chưa sạch hoặc Closeout Gate chưa đạt APPROVED >= 85. Cấm tuyên bố hoàn tất!`
