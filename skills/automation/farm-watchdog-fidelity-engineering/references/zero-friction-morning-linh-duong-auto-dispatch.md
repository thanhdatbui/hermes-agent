# Zero-Friction Morning Priority Auto-Dispatch (Linh Duong Cron Architecture)

## 1. Context & Pitfall
- **The Friction Trap:** Bắt user phải tự gõ lệnh hoặc nhớ set topic / session "Linh Dương" (việc đòn bẩy lớn nhất) vào cuối ngày là thiết kế tồi, chắc chắn thất bại sau 1-2 ngày vì ma sát nhận thức (cognitive friction).
- **The Dopamine/Zeigarnik Trap:** Sáng sớm mở Telegram, user thấy hàng loạt bot và session báo cáo dở dang sẽ rơi vào phản xạ đọc hết ("mắc bệnh đọc hết"), làm kiệt quệ năng lượng tinh thần đầu ngày vào các việc lặt vặt (bắt chuột đồng).
- **The Agent Guard Trap:** Cronjob tạo mới trên hệ thống bị chặn bởi `[CRON_AGENT_POLICY_BLOCKED]` nếu không có `no_agent: true`. Không được tạo cronjob chạy LLM trực tiếp trong runtime cron của Hermes.
- **The Deleted Topic & Ephemeral Origin Delivery Trap:** 
  - Khi User làm xong việc thường có thói quen xoá hẳn Topic Telegram cho sạch mắt ("săn xong thịt xong thì xoá để làm chi").
  - **BẪY CHÍ MẠNG CỦA `deliver: 'origin'`:** Khi tạo/cập nhật cronjob trong một topic Telegram Forum, Hermes ghi nhớ `origin` là `platform:chat_id:thread_id` (cụ thể topic hiện tại).
  - Khi topic đó bị xoá: Cron chạy lúc 06:00 sáng sẽ bị Telegram trả về `message thread not found`. Hermes Gateway kích hoạt fallback `delivered without thread_id`. Trên Telegram Forum, gửi không có `thread_id` sẽ **rơi thẳng vào topic "General" (Chung)**! User không nhận được notification ở topic làm việc mới và tưởng cronjob bị mất tích.
  - **KHẮC PHỤC TRIỆT ĐỂ:** Bắt buộc User tạo 1 **Topic cố định vĩnh viễn** (vd: `🦁 Linh Dương` hoặc `Báo Cáo Sáng`) và cấu hình `deliver: telegram:<chat_id>:<permanent_thread_id>`, TUYỆT ĐỐI KHÔNG dùng `deliver: 'origin'` tạo từ topic nhiệm vụ tạm bợ sẽ bị xóa.
- **The ID Searching Frustration:** Nếu gửi tin nhắn về DM điều phối mà chỉ ghi text ID topic (vd `Thread ID: 324110`) sẽ làm User bực mình vì phải đi soi/lùng từng ID trên app. BẮT BUỘC phải đính kèm Direct Link 1-click `https://t.me/c/<chat_id>/<thread_id>`.

## 2. Core Architecture
- **Tự động 100% (Zero User Input):** Chạy cronjob script Python độc lập với `no_agent: true` lúc 06:00 sáng.
- **State DB Inspection:** Script tự truy vấn trực tiếp SQLite `state.db` của Hermes (`sessions` & `messages`), lấy các session có tương tác gần nhất trong 24h.
- **Phân vai Model (Reviewer vs Daily Runner):**
  - **Claude CLI:** Chỉ dùng độc quyền cho vai trò **Auditor / Reviewer** khi User yêu cầu review nghiệm thu mã nguồn.
  - **Gemini AG Pool (`ag-gemini-pool-3` qua OmniRoute local `:20129`):** Đóng vai trò **Daily Morning Runner**. Gọi trực tiếp endpoint local `/v1/chat/completions` với timeout 20s. Tốc độ cực nhanh (< 1.5s), không tốn tiền API bên ngoài và đồng bộ với model chính của Agent.
- **Fail-safe Fallback:** Nếu endpoint LLM bị lỗi hoặc timeout, script tự động chuyển sang Heuristic Regex để đảm bảo 100% không bao giờ trượt tin nhắn sáng sớm.
- **Giao diện 1-Click Direct Link & Topic Delivery Lifecycle:**
  - **Đích đến:** Bắt buộc cấu hình đích đến là **Topic Cố Định** (`deliver: telegram:<chat_id>:<permanent_thread_id>`), cấm để `origin` từ topic task tạm bợ vì khi xoá topic tin sẽ bị trôi vào General.
  - Soạn tin nhắn có link markdown trực tiếp: `[👉 BẤM VÀO ĐÂY ĐỂ VÀO PHIÊN ĐANG DỞ](https://t.me/c/<chat_id>/<thread_id>)`.
  - User thức dậy chỉ cần chạm 1 phát từ Topic Cố Định là Telegram tự nhảy vào đúng Topic làm dở. Làm xong việc, User bấm Xoá Topic nhiệm vụ thoải mái, tin nhắn sáng mai vẫn sẽ nổ chuông đều đặn tại Topic Cố Định.

## 3. Production Engineering Checklist (Senior Review Findings)
1. **SQLite Read-Only URI & Timeout:**
   - Bắt buộc mở với `file:{urllib.parse.quote(db_path)}?mode=ro`, `uri=True`, `timeout=10.0` để không tranh chấp khóa ghi (locked) với Hermes Gateway đang phục vụ chat. Đóng kết nối trong khối `finally`.
2. **Subprocess Timeout on Windows (Process Tree Kill):**
   - Khi gọi CLI bên ngoài, nếu dùng `subprocess.Popen` kèm timeout 30s thì bắt buộc dùng `taskkill /F /T /PID {proc.pid}` trên Windows để diệt tận gốc tiến trình con.
3. **Anti-Hallucination Thread Guard:**
   - LLM có thể bịa `thread_id`. Script bắt buộc kiểm tra `str(parsed['thread_id']) in valid_threads`. Nếu không khớp, lập tức fallback, cấm gán bừa candidate khác làm lệch pha mission và thread.
4. **Regex Word Boundaries & Sentiment Disambiguation:**
   - Heuristic phải dùng `\b<word>\b` để tránh false positive ("bot" trong "both", "fix" trong "prefix").
   - Nhận diện rõ sắc thái: `closeout\s+rejected` / `blocked` là việc nghẽn nặng -> CỘNG điểm ưu tiên cao (+15); `closeout\s+approved` là việc đã xong -> TRỪ điểm triệt để (-20).
5. **Stdout UTF-8 on Windows:**
   - Bắt buộc `getattr(sys.stdout, "reconfigure", None)(encoding="utf-8")` ở đầu script để chống lỗi `UnicodeEncodeError` khi cron engine redirect pipe trên Windows.
