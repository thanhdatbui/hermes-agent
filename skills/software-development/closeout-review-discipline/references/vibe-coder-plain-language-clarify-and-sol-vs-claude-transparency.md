# Vibe Coder Plain-Language Clarify & Sol vs Claude Transparency

## 1. Bối cảnh & Tín hiệu phản hồi từ User (Incident 2026-10-09)
Khi Closeout Gate chạm ngưỡng 3 lần REJECT (kẹt ở 82–84/100), `closeout_gate.py` kích hoạt cơ chế `[REVIEWER_HANDOFF_TRIGGERED]`.
Coordinator dừng lại và gọi `clarify` với câu hỏi kỹ thuật:
> *"Closeout Gate đã chạm ngưỡng 3 lần thẩm định (điểm hiện tại 84/100, thiếu 1 điểm so với ngưỡng >=85). Sếp có duyệt cho gọi Claude CLI (Sonnet) tự sửa nốt để chốt phiên không?"*

User lập tức phản hồi bối rối:
> **"Là sao tự sol sửa hay m sửa?"**

## 2. Nguyên nhân gốc rễ gây hiểu lầm
1. **Thiếu minh bạch về vai trò:**
   - User nắm invariant: *"Gate reject: Sol High (:20129) vá thẳng, cấm Gemini mò 3 vòng"*.
   - Do đó, khi Coordinator nhảy vào hỏi *"có cho gọi Claude không"*, User ngỡ rằng Sol High không hề tham gia sửa, hoặc AI đang đùn đẩy việc mà không giải thích vì sao Sol không tự vá được.
2. **Không báo cáo trạng thái Sol Auto-Repair:**
   - Trong phiên thực tế, `closeout_gate.py --auto-repair` đã gọi Sol High nhưng model streaming bị timeout:
     `[SOL_REPAIR_FAILED: Model call failed: Timeout exceeded during streaming]`.
   - Coordinator không thông báo việc Sol Auto-Repair bị timeout mà nhảy cóc sang hỏi quyền Claude CLI, khiến User hoang mang giữa Sol vs Gemini vs Claude.
3. **Từ ngữ học thuật / jargon:** Dùng các thuật ngữ *"thẩm định 3 lần"*, *"ngưỡng >= 85"*, *"reviewer handoff"* với một Vibe Coder gây nhiễu nhận thức.

---

## 3. Quy chuẩn Clarify Plain-Language khi chạm 3-Strike / Gate Reject

Khi bắt buộc phải gọi `clarify` để xin quyền chạy Claude CLI hoặc quyết định rẽ nhánh closeout, Coordinator **BẮT BUỘC** tuân thủ cấu trúc 3 phần ngôn ngữ bình dân:

### Mẫu chuẩn (Plain-Language Template):
```text
Dạ báo cáo sếp:
1. Trọng tài Sol High chấm bài: Đạt 84/100 (cần >=85 mới được đóng phiên).
2. Tình trạng sửa bài: Sol Auto-Repair bị [timeout / không ra patch], em và Worker đã tự sửa nâng điểm từ 82 -> 84đ nhưng Sol vẫn bắt bẻ [nêu đúng 1 lý do cốt lõi bằng tiếng Việt dễ hiểu].
3. Lựa chọn xử lý:
   - Cách 1: Cho Claude (Sonnet) vào sửa dứt điểm đúng ý trọng tài (ăn chắc >=85đ để đóng phiên ngay).
   - Cách 2: Để em tự nắn lại [chi tiết sửa] thêm 1 lần nữa rồi nộp lại cho Sol chấm.
```

### Các điều cấm kỵ (Anti-Patterns):
- **CẤM** hỏi cộc lốc *"có duyệt gọi Claude CLI không"* mà không giải thích Sol High và Coordinator đã làm gì trước đó.
- **CẤM** dùng thuật ngữ trừu tượng (`scope_hash`, `rubric scorecard breakdown`, `reviewer handoff`).
- **LUÔN** nêu rõ ai là người chấm (Sol High), ai đã sửa (Sol / Coordinator / Worker), và tại sao cần đến Claude CLI.
