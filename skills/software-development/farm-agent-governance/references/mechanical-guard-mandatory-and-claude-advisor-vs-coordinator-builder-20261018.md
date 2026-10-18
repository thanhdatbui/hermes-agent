# Bất Biến Chấm Dứt Khóa Luật Bằng Prompt & Phân Định Claude Advisor vs Coordinator Builder (18/10/2026)

## 1. Bối cảnh & Sự cố (17-18/10/2026)

### Sự cố 1: Bẫy "Dặn dò suông bằng Prompt / Memory"
Khi phát hiện sự cố 10 máy dính lỗi rớt mạng do bị gán proxy dạng tên miền (`mirotik1.taadaa.click`), Coordinator đã tự động ghi chú vào `Hermes Memory` và thêm văn bản vào `PROJECT_RULES.md`.
**Phản ứng quyết liệt từ Operator:**
> *"Ngừng khoá luật bằng prompt. T đã thiết kế cái gate guard hook bằng claude cli là từ h mọi rule phải thi công guard hook gate đéo đc dùng prompt r mà?"*

**Bản chất:**
- Prompt, Markdown, và Persistent Memory là **Ràng buộc mềm (Soft Constraints)**. Mọi LLM khi gặp context compaction hoặc session mới đều sẽ bị "lú", trôi context và tiếp tục vi phạm.
- **Quy tắc bất biến mới:** CẤM TUYỆT ĐỐI dừng lại ở việc dặn luật bằng prompt / text. Bất kỳ quy tắc vận hành nào được User chốt đều BẮT BUỘC phải thi công thành **Gate Hook cơ học (Python code)** chặn trực tiếp ở tầng OS/PreToolUse hook, kèm bộ unit test độc lập.

---

### Sự cố 2: Hiểu sai vai trò "Claude CLI Thi Công vs Hermes Thi Công"
Khi được yêu cầu làm Gate Hook, Coordinator lại định đùn việc cho Claude CLI vào viết code và ngồi hỏi xin mở quota:
> *"Tại sao lại claude cli thi công? Nó chỉ việc tư vấn còn mày thi công mà! H quota nó hồi r đó"*
> *"Claude cli duyệt chưa" -> "Thi công đến khi claude cli duyệt"*

**Phân định vai trò chuẩn hóa:**
- **Claude CLI (Sonnet 5.5 / Planner / Reviewer):** CHỈ ĐÓNG VAI TRÒ TƯ VẤN (Consultant / Advisor) & KIỂM TOÁN (Reviewer). Cung cấp bản vẽ kiến trúc, phát hiện edge cases, bypass vectors, và thẩm định diff (APPROVED / REJECTED).
- **Hermes Coordinator (Omni Worker / Gemini):** LÀ NGƯỜI ĐIỀU PHỐI & THI CÔNG (Builder / Implementer). Trực tiếp viết code Python hoặc dispatch worker Haiku O(1), thiết kế Hook, viết test suite `pytest` và chạy nghiệm thu.

---

## 2. Quy trình Bắt Buộc: "Thi Công Đến Khi Claude CLI Duyệt" (The 5-Round Reviewer Loop)

Quy trình chuẩn hóa khi Operator ra lệnh đưa một Rule mới vào Gate:

```
1. OPERATOR MANDATE: "Mọi rule phải thi công guard hook gate, đéo được dùng prompt"
       │
       ▼
2. CLAUDE SONNET CONSULT (claude_worker.py --role planner)
   → Lấy bản vẽ kiến trúc, Fail-Closed strategy, Regex & Allowlist
       │
       ▼
3. BUILD & TEST (Coordinator / Haiku Worker O(1))
   → Viết hook tại D:/Taadaa/tools/guard_<name>.py
   → Viết unit test tại D:/Taadaa/tools/tests/test_guard_<name>.py
   → Chạy pytest nghiệm thu 100% pass
       │
       ▼
4. CLAUDE SONNET REVIEW (claude_worker.py --role reviewer)
   → Phân tích tĩnh đối kháng (adversarial hand-tracing)
   → NẾU REJECTED: Bóc tách cụ thể các bypass vectors & false positives
       │
       ├────────────────────────────────────────┐
       ▼                                        │
5. RE-IMPLEMENT & EXPAND TESTS                  │ Loop lặp lại
   → Vá đúng các lỗi P1/P2 do Reviewer chỉ ra    │ (Trung bình 3-5 rounds)
   → Bổ sung regression tests cho từng lỗi      │
   → Quay lại Bước 4 ───────────────────────────┘
       │
       ▼
6. VERDICT: APPROVED
   → Đồng bộ hook sang D:/OneDrive/Taadaa_Sync_Shared/hermes-sync/hooks/
   → Cấu hình PreToolUse hook qua manage_hermes_config.py
   → Commit & push lên git repository
```

---

## 3. Case Study Thực Chiến: `guard_android_proxy.py` (Từ 6 test lên 48 tests)

### Đề bài
CẤM TUYỆT ĐỐI gán domain/hostname (`mirotik1.taadaa.click`, `test.taadaa.click`...) vào Android `http_proxy`. BẮT BUỘC dùng IP LAN RFC1918 (`192.168.110.2:<port>`) hoặc `:0` (clear). Lý do: Domain ngoài phân giải ra WAN IP bị tường lửa router chặn Hairpin NAT, gây mất mạng ("Wi-Fi ! Không có Internet").

### Nhật ký 5 Vòng Thẩm Định Của Claude Sonnet 5.5 Reviewer:

| Vòng | Quyết định | Bệnh lý & Bypass do Claude Reviewer bóc trần | Cách khắc phục đã thực thi |
| :--- | :---: | :--- | :--- |
| **V1** | **REJECTED** | 1. Dùng `search()` chỉ bắt match đầu tiên, lọt lệnh kép nối `&`.<br>2. Chặn nhầm `settings get` và `settings delete`.<br>3. Chặn oan biến môi trường `$SERIAL` của thiết bị.<br>4. Test allow không kiểm tra `returncode == 0`. | • Bổ sung regex check get/delete.<br>• Quét dynamic `$` chỉ trên proxy value.<br>• Assert `proc.returncode == 0` trong test.<br>*(Số test: 6 -> 18)* |
| **V2** | **REJECTED** | 1. Tách segment bằng `[;&|\n]` làm mất context `adb shell` ở các câu lệnh sau (P1-1).<br>2. Shell ghép chuỗi nháy `'192.168.110.2'.evil.com` qua mặt regex (P1-2).<br>3. Shortcut get/delete bị fail-open (P1-3).<br>4. Locale cp1252 trên Windows làm crash stdin khi gặp ký tự UTF-8 lạ (P2-4). | • Quét `DEVICE_PROXY_RE` và `finditer` trên toàn bộ lệnh.<br>• Viết hàm `unwrap_token` cấm mixed/concatenated quotes.<br>• Match `verified_ends` cho từng occurrence của `http_proxy`.<br>• Đọc `sys.stdin.buffer.read().decode('utf-8', errors='replace')`.<br>*(Số test: 18 -> 26)* |
| **V3** | **REJECTED** | 1. Lỗ hổng P1: Regex `WRAPPER_CLOSE_QUOTE_RE = ([^"']*)["']` dùng dấu `*` nên token chỉ có 1 dấu nháy `"` bị unwrap thành rỗng `""`, lọt lưới như một lệnh xóa proxy hợp lệ (Ví dụ: `http_proxy " evil.com"`). | • Đổi `*` thành `+` (`([^"']+)["']`), ép lone quote token phải rơi vào nhánh từ chối `malformed`.<br>• Thêm test case cho lone quote với space.<br>*(Số test: 26 -> 34)* |
| **V4** | **REJECTED** | 1. False positive với dấu nháy lồng nhau (single-quote bên trong double-quote wrapper: `"settings put ... '192.168.110.2:1'"`).<br>2. Chặn nhầm lệnh đọc `dumpsys \| grep http_proxy` hoặc `grep 'http_proxy'`.<br>3. Yêu cầu ghi rõ phạm vi deliberate key-splitting trong docstring. | • Hoàn thiện logic unwrapping nháy đa tầng.<br>• Bổ sung hàm `is_read_only_mention` miễn trừ cho read tools (`grep`, `findstr`, `dumpsys`, `select-string`, `sls`) khi không có write verb.<br>• Ghi rõ phạm vi agent mistake trong docstring.<br>*(Số test: 34 -> 48)* |
| **V5** | **APPROVED** | **CHÍNH THỨC PHÊ DUYỆT.** Toàn bộ 48/48 unit tests pass 100%. Mọi vector bypass nháy, nối lệnh, decode stdin và RFC1918 đều đạt chuẩn. | • Bổ sung thêm `insert`, `update`, `call`, `export` vào danh sách write verbs.<br>• Đồng bộ sang `Taadaa_Sync_Shared/hermes-sync/hooks/`.<br>• Commit `e4d7ac7` trên repo `D:/Taadaa/tools`. |

---

## 4. Bài Học Xương Máu Về Thiết Kế Gate Cực Đoan (Hard Gate Invariants)

1. **CẤM DỪNG Ở TEST PASS SƠ SÀI:**
   - 6 test ban đầu của Coordinator tự viết đều pass 100%, nhưng thực chất chứa đầy lỗ hổng bypass chết người (P1 lone-quote, P1 shell quote-concatenation, P1 segment-split context loss).
   - **Bắt buộc Reviewer đối kháng:** Phải để Claude Sonnet 5.5 đóng vai Reviewer khó tính đọc từng ký tự regex, hand-tracing các góc khuất trước khi cho phép đưa vào production.
2. **KỸ THUẬT XỬ LÝ DẤU NHÁY SHELL (Shell Quoting Pitfall):**
   - Shell Unix/Bash có cơ chế tự động nối chuỗi cạnh nhau: `'a'"b"` trở thành `ab`.
   - Một token proxy nếu chứa dấu nháy bên trong (mixed quotes) hoặc nháy đơn lẻ đi kèm dấu cách bắt buộc phải coi là `malformed` và Block ngay lập tức.
3. **CẤM ĐÙN VIỆC CHO CLAUDE CLI:**
   - Khi Operator hỏi *"Claude cli duyệt chưa"*, điều đó có nghĩa là Operator muốn thấy kết quả kiểm toán từ Reviewer, KHÔNG PHẢI bảo Claude CLI nhảy vào viết code.
   - Coordinator phải tự điều phối thi công sửa code, fix test, rồi nộp lại bài cho Claude Reviewer chấm.
