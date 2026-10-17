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

**Phân định vai trò chuẩn hóa:**
- **Claude CLI (Sonnet 5.5 / Planner / Reviewer):** CHỈ ĐÓNG VAI TRÒ TƯ VẤN (Consultant / Advisor) & PHẢN BIỆN (Reviewer). Cung cấp bản vẽ kiến trúc, phát hiện edge cases, bypass vectors, và thẩm định diff.
- **Hermes Coordinator (Omni Worker / Gemini):** LÀ NGƯỜI THI CÔNG TRỰC TIẾP (Builder / Implementer). Tự tay viết code Python, thiết kế Hook, viết test suite `pytest` và chạy nghiệm thu.

---

## 2. Quy trình 4 bước chuyển hóa Rule thành Gate Cơ Học

```
1. OPERATOR RULE
       │
       ▼
2. CLAUDE SONNET CONSULT (claude_worker.py --role planner)
   → Lấy bản vẽ kiến trúc, Fail-Closed strategy, Regex & Allowlist
       │
       ▼
3. COORDINATOR IMPLEMENTATION (Hermes Coordinator)
   → Viết hook tại D:/Taadaa/tools/guard_<name>.py
   → Viết unit test tại D:/Taadaa/tools/tests/test_guard_<name>.py
   → Chạy pytest nghiệm thu pass 100%
       │
       ▼
4. CLAUDE SONNET REVIEW / DEPLOY
   → Review diff & test suite
   → Đồng bộ sang D:/OneDrive/Taadaa_Sync_Shared/hermes-sync/hooks/
   → Cấu hình PreToolUse hook qua manage_hermes_config.py
```

---

## 3. Case Study Mẫu: `guard_android_proxy.py`

### Đề bài
CẤM TUYỆT ĐỐI gán domain/hostname (`mirotik1.taadaa.click`, `test.taadaa.click`...) vào Android `http_proxy`. BẮT BUỘC dùng IP LAN RFC1918 (`192.168.110.2:<port>`) hoặc `:0` (clear). Lý do: Domain ngoài phân giải ra WAN IP bị tường lửa router chặn Hairpin NAT, gây mất mạng ("Wi-Fi ! Không có Internet").

### Tư vấn kiến trúc từ Claude Sonnet 5.5
- Không dùng denylist chuỗi (dễ lọt domain mới).
- Dùng **Fail-Closed Allowlist** kết hợp thư viện `ipaddress`.
- Chặn đứng biến động (`$VAR`, `%VAR%`, backticks) fail-closed.
- Bóc tách host/port, kiểm tra `ipaddress.ip_address(host)`.
- Nếu văng `ValueError` $\rightarrow$ Tên miền $\rightarrow$ Block ngay.
- Nếu là IP $\rightarrow$ Bắt buộc thuộc RFC1918 (`10/8`, `172.16/12`, `192.168/16`). Không phải LAN $\rightarrow$ Block ngay.
- Cho phép `:0`, `0`, `null`, `none` để xóa proxy.

### Thi công & Nghiệm thu
- **Hook:** `D:/Taadaa/tools/guard_android_proxy.py`
- **Tests:** `D:/Taadaa/tools/tests/test_guard_android_proxy.py` (6/6 tests PASS in 1.18s)
- **Commit:** `697c64e` trên repo `D:/Taadaa/tools`.
