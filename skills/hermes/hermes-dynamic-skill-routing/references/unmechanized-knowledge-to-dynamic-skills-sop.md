# Quy Trình Tự Động Định Tuyến Tri Thức Chưa Cơ Giới Vào Dynamic Skill (SOP 2026-10-24)

## 1. Vấn Đề Cốt Lõi: Bẫy Tràn Memory (2.200 Chars) vs Dynamic Skill
- **Bẫy cũ:** Mỗi khi User chỉ đạo một quy trình mới, sửa lỗi thao tác hoặc đưa ra bài học chưa được tự động hóa bằng code, Coordinator theo quán tính platform tự gọi `memory(action='add'/'replace')` để nhét vào `MEMORY.md`.
- **Hậu quả:** 
  - `MEMORY.md` bị chạm trần (2.148/2.200 ký tự ~ 97%), gây nghẽn và phải xóa bớt dữ liệu cũ.
  - Subagent / Worker chạy trong phiên cô lập (`dispatch_worker.py`) hoàn toàn KHÔNG đọc được `MEMORY.md` của Coordinator, dẫn đến việc Worker vẫn mù tịt và lặp lại lỗi cũ!

## 2. Nguyên Tắc Phân Luồng Tri Thức 3 Cửa
1. **Cửa 1 — Đã Cơ Giới Hoá (Code / Script / Hook / Database / Marker):**
   - Ví dụ: `guard_media_vision_gate.py`, `.manual_*_locked`, `vision_fallback_reader.py`.
   - **Quy tắc:** CẤM TUYỆT ĐỐI lưu vào `memory`, cấm viết thêm text thừa vào prompt. Chốt chặn cơ học (exit code != 0) tự đảm bảo an toàn.
2. **Cửa 2 — Tri Thức Chưa Cơ Giới Hoá (Quy trình thao tác, cạm bẫy, SOP, thứ tự fallback, bài học vận hành):**
   - **Quy tắc:** BẮT BUỘC lưu vào Thư viện Skill (`D:/Taadaa/Hermes/skills/`).
   - Sử dụng tool 1 chạm `D:/Taadaa/tools/record_skill_knowledge.py` để ghi vào `SKILL.md` hoặc `references/`.
   - Tự động tra cứu O(1) qua `skill_lookup.py` và nhúng vào prompt qua `skill_injector.py` (với cơ chế auto_heal) khi Worker làm việc.
3. **Cửa 3 — Persistent Memory (`MEMORY.md`):**
   - **Quy tắc:** CHỈ dùng cho thông tin cá nhân của User (User Profile, địa chỉ giao hàng, liên hệ, sở thích phong cách) hoặc đặc thù môi trường Windows mà không thuộc về quy trình nào.

## 3. Thao Tác 1 Chạm Với `record_skill_knowledge.py`
Khi phát hiện bài học / quy trình mới chưa có code:
```bash
python D:/Taadaa/tools/record_skill_knowledge.py \
  --skill "<tên_skill>" \
  --content "<nội_dung_quy_trình>" \
  [--kind body|reference] \
  [--ref-name "<tên_file>.md"]
```
- Tự động tìm đúng thư mục skill.
- Tự động ghi nguyên tử (atomic), chống trùng lặp, bảo toàn YAML frontmatter.
- Tự động rebuild `skills_index.json` tại chỗ.
- `skill_injector.py` có cờ `auto_heal=True` sẽ tự động làm mới index nếu có bất kỳ file skill nào bị stale.
