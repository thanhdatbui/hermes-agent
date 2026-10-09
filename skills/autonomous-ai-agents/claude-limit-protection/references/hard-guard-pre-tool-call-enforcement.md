# Hard Guard PreToolUse Enforcement for Claude CLI Quota (Taadaa Phone Farm)

## 1. Bối Cảnh Sự Cố Thực Tế (06/09/2026)
- **Quy tắc ban đầu:** Cấm gọi Claude CLI khi chạm 85% phiên 5h và 90% weekly quota.
- **Sự cố:** Agent sơ suất chạy lệnh:
  `claude -p --model opus --effort max "..."`
  nhồi toàn bộ codebase audit mà không kiểm tra quota trước. Kết quả: tài khoản Claude Pro bị đẩy từ dưới 85% vọt thẳng lên 100% quota và bị Anthropic khóa session limit tới 16:40.
- **User phản hồi:** *"ơ mà claude cli t đã khoá chặt là nếu quota 5h đạt 85% thì k đc hỏi nữa mà???? sao vẫn vi phạm"*.
- **Nguyên nhân cốt lõi:**
  1. *Soft Rule Zero Enforcement:* Quy tắc chỉ nằm ở dạng văn bản trong `SKILL.md` và Memory. Khi Agent bị phân tâm hoặc xử lý task khó, Agent tự giác không đảm bảo 100%.
  2. *API Blindness:* Lệnh `claude auth status --text` trên tài khoản Claude Pro chỉ trả về:
     ```text
     Login method: Claude Pro account
     Organization: ...
     Email: ...
     ```
     Hoàn toàn KHÔNG có trường nào hiển thị `% quota remaining`. Do đó agent không thể parse % một cách tự động qua lệnh auth.

---

## 2. Kiến Trúc Hard Guard (`farm-coordinator-guard`)
Để ngăn chặn vĩnh viễn, giải pháp là đặt một **chốt chặn vật lý bằng code (Hard Intercept)** trong hook `_on_pre_tool_call` của plugin `farm-coordinator-guard`.

### 2.1 Sơ đồ luồng hoạt động
```text
Agent gọi: terminal(command="claude -p ...")
         │
         ▼
┌─ PRE_TOOL_CALL HOOK (_check_claude_cli_guard) ───────────┐
│                                                           │
│  1. Regex: cmd chứa /\bclaude\b/i ?                       │
│     ├─ NO  ──→ ALLOW (chạy bình thường)                   │
│     └─ YES ──→ Tiếp tục kiểm tra                          │
│                                                           │
│  2. Kiểm tra Lockout Cache (claude_lockout.json):         │
│     now < locked_until ?                                  │
│     ├─ YES ──→ ⛔ BLOCK VẬT LÝ NGAY LẬP TỨC               │
│     │          Báo: "Claude CLI đang bị lockout tới..."   │
│     │          Ép fallback: OmniRoute Review :20129       │
│     └─ NO  ──→ Xóa cache lockout cũ nếu đã hết hạn        │
│                                                           │
│  3. Kiểm tra Self-Tracking Usage (claude_usage.json):     │
│     Cửa sổ 5h (now - 5 * 3600):                           │
│     - Lệnh thường: weight = 1                             │
│     - Thêm --model opus: weight *= 2                      │
│     - Thêm --effort max: weight *= 2 (tổng weight = 4)    │
│                                                           │
│     total_weight + weight >= 38 (~85% của 45 calls)?      │
│     ├─ YES ──→ ⛔ BLOCK VẬT LÝ                            │
│     │          Báo: "85% Quota Exceeded (38/45 calls)"    │
│     │          Ép fallback: OmniRoute Review :20129       │
│     └─ NO  ──→ ALLOW (cho phép thực thi)                  │
└───────────────────────────────────────────────────────────┘
```

---

## 3. Ba Nguyên Tắc Thiết Kế Sống Còn (Tránh Bẫy Hiệu Năng)

1. **CẤM TUYỆT ĐỐI gọi subprocess trong Hook:**
   - Nếu hook tự chạy `subprocess.run(["claude", ...])` để check limit, nó sẽ kích hoạt lại chính hook `pre_tool_call` $\rightarrow$ **Infinite Loop (Treo vĩnh viễn)**.
   - Toàn bộ cơ chế Hard Guard chỉ dựa trên File I/O thuần túy (`claude_lockout.json`, `claude_usage.json`).
2. **Độ trễ siêu thấp (< 1ms):**
   - Đọc JSON nhỏ trên ổ cứng Windows SSD chỉ tốn `< 1ms`, hoàn toàn không ảnh hưởng tới tốc độ thực thi của terminal tool.
3. **Fail-Safe Fallback:**
   - Khi bị Hard Guard chặn đứng, output thông báo lỗi cung cấp ngay giải pháp thay thế cụ thể:
     `HÀNH ĐỘNG BẮT BUỘC: Fallback sang OmniRoute Review (:20129) qua model review hoặc auto/claude-opus.`

---

## 4. Kiểm Chứng Trạng Thái Lockout & Auto-Recovery
- Khi dính lỗi limit từ Anthropic: ghi nhận ngay `locked_until` (epoch timestamp) vào file `claude_lockout.json`.
- Trong suốt thời gian bị khóa: 100% lệnh `claude` bị chặn đứng tại cửa ngõ.
- Khi qua mốc thời gian reset: hook tự động `unlink()` file lockout và cho phép lệnh Claude CLI hoạt động bình thường mà không cần thao tác thủ công.
