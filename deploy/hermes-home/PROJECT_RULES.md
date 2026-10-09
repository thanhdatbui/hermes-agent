# TAADAA PHONE FARM — PROJECT RULES & INVARIANTS

Tài liệu quy chuẩn tối cao cho toàn bộ hệ thống Taadaa Phone Farm (80 máy Kibe + 80 máy Admin).
Áp dụng cho mọi Agent (Coordinator, Subagent Worker), Claude Code, OpenCode và kịch bản automation.

---

## 🔒 FARM-ASSET-001 — BẢO VỆ TÀI SẢN NICK TIKTOK & CẤM TỰ Ý LOGOUT (CRITICAL)
1. **Tài sản doanh nghiệp:** Mọi nick TikTok đang đăng nhập trên máy farm là TÀI SẢN CỦA USER.
   Nghiêm cấm mọi hành vi tự tiện quy chụp nick trên máy là "nick lạ", "nick rác", "nick test" để logout/xóa phiên.
2. **Quy định logout duy nhất:** CHỈ ĐƯỢC PHÉP LOGOUT NICK KÝ SINH (Nick có chủ sở hữu chính thức ở máy khác: `owner_stt != current_stt`) đã được xác minh bằng OCR readback (User đã phê duyệt dọn dẹp).
3. **Nick không có trong Excel:** BẮT BUỘC coi là sự cố LỆCH DỮ LIỆU (Unrecorded Asset / Data Desync) -> **CẤM TUYỆT ĐỐI LOGOUT**. Bắt buộc đóng băng máy, truy vết backup và BÁO CÁO USER CHỜ CHỈ ĐẠO.
4. **Cấm hành vi tương đương:** Cấm `pm clear com.ss.android.ugc.trill`, cấm gỡ app, cấm xóa cache phiên khi chưa có lệnh.
5. **Technical Guard:** Mọi lệnh logout bắt buộc phải qua `logout_guard.py` và `do_logout_account.py`. Cấm viết script bypass.

---

## ⚙️ PHÂN VAI & ĐIỀU PHỐI (COORDINATOR vs WORKER)
1. **Session chính LÀ COORDINATOR:** Chỉ inspect hiện trường O(1), phân tích nguyên nhân gốc rễ, lập kế hoạch, dispatch worker và chốt phiên.
   - CẤM Coordinator tự viết script Python probe, test hàm, reproduce thử nghiệm hay sửa code bừa bãi ở session chính (Ngoại lệ: T1 sửa hiện trường O(1) <= 15 dòng, 1 file theo TIERED_WORKFLOW).
2. **Worker Subagent:** Mọi tác vụ reproduce, sửa code, viết focused test bắt buộc dispatch qua `delegate_task(goal=..., context=...)` (áp dụng cho task dispatch thi công lớn; T1 sửa hiện trường O(1) miễn trừ).
   - Worker budget: <= 15 phút, <= 20 tool calls. Focused test < 30s.
3. **Gate 6 (Step-by-Step Visual Evidence):** Max blind steps = 1. Mọi thao tác UI (Browser, GPM, Farm ADB) bắt buộc gửi ảnh `MEDIA:<path>` ngay tại Pre-action và Post-action. Cấm chạy ngầm trong bóng tối. (Ngoại lệ: Canary trong Pipeline A-Z gom ảnh kết quả vào báo cáo nghiệm thu trọn gói Bước 4).

---

## 📊 VẬN HÀNH DỮ LIỆU & WORKBOOK
1. **Atomic Save:** Mọi thao tác ghi file Excel (`.xlsx`) bắt buộc ghi ra file tạm `.tmp.xlsx` rồi atomic replace, chống hỏng file khi crash giữa chừng.
2. **Pass ảo TikTok:** Khi cột D (PASS) bị rỗng (`None`), tài khoản được reg dạng passwordless -> Cứu/login bằng cờ `--otp-only`.
3. **Báo cáo Farm:** Báo cáo lỗi/kết quả bắt buộc định danh bằng Username (`@nick` + M<số>), cấm chỉ in số máy.
   - Lỗi diện rộng >= 3 máy bắt buộc gửi cảnh báo về nhóm **Farm Alert (`telegram:-5373649734`)**.
4. **Hotmail & GPM:** Mua Hotmail CloneFBIG (Product 3470). Đổi pass Hotmail bắt buộc ngâm KMSI >= 7 ngày trên profile GPM đã có Live Gmail.
5. **ChatGPT Reg:** 100% Direct Email + OTP (cấm Google SSO).

---

## 🛡️ AN TOÀN THIẾT BỊ & DEVICE LOCK
1. **Device Lock Bắt Buộc:** Chạm thiết bị thật bắt buộc acquire lock vật lý (`acquire_device_lock(machine=..., serial=..., project=..., user_authorized=True)`).
2. **Không Tranh Chấp Lock:** Khi máy đang có lock từ tiến trình nuôi chính (`run_tiktok.py --mode multi-machine-feed-session`), cấm force-kill hay cướp lock; phải kiên nhẫn chờ máy nhả lock.
3. **Farm Runtime Knowledge:** Mọi thông số thiết bị, tọa độ, port proxy lưu tại `D:/Taadaa/tools/farm_runtime_knowledge.json`. Tra cứu O(1), cấm đoán mò.
4. **Closeout Gate (Pipeline A-Z khi sửa bug farm):** Chi tiết tại `D:/Taadaa/tools/TIERED_WORKFLOW.md` Mục II & IV.
   - **(1) Fix:** Sửa code (T1 Coordinator sửa trực tiếp O(1) <= 15 dòng hoặc T2 Worker thi công trong lồng) -> focused unit test PASS (< 30s). Được commit LOCAL, CẤM push.
   - **(2) Canary (tự động):** Acquire device lock -> chạy trên 1 máy thật đại diện -> chụp ảnh `MEDIA:<path>` -> tự chạy WinRT OCR đọc text ảnh. **Nhả ngay device lock sau khi có ảnh và kết quả OCR.** Chỉ kết luận PASS/FAIL dựa trên text OCR, cấm suy luận từ log.
   - **(3) Closeout Gate (tự động, chạy ngầm):** `python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base $(git merge-base HEAD '@{u}' 2>/dev/null || git merge-base HEAD origin/main) --json-output`. Sol High chấm >= 85 và exit 0 mới qua. Nếu < 85 hoặc Canary FAIL thì tự sửa theo nhận xét, sau đó chạy lại từ (1), không báo User. Tối đa 3 vòng (1 vòng = 1 chu kỳ Bước 1->3; trượt = Canary FAIL hoặc điểm < 85 hoặc exit != 0). Nếu hết 3 vòng vẫn trượt: **BẮT BUỘC nhả sạch device lock và session worker trước khi dừng**, báo đúng 1 blocker kèm evidence.
   - **(4) Báo cáo nghiệm thu trọn gói (gửi 1 lần duy nhất):** Ảnh `MEDIA:` + text OCR + điểm Reviewer + SHA commit local + diffstat. Trạng thái: `device lock: RELEASED`, `session: RELEASED`, `push: CHỜ LỆNH USER`.
   - **(5) Push remote:** CHỈ thực hiện khi User trả lời báo cáo nghiệm thu bằng một trong các lệnh `chốt` / `chốt phiên` / `done` / `ok`. Chữ "ok" ở ngữ cảnh khác KHÔNG được tính là lệnh push.
   - **CẤM TUYỆT ĐỐI** tự động push remote khi User chưa xem ảnh duyệt. Chỉ được push đúng SHA đã báo cáo. Nếu có commit mới sau báo cáo thì phải quay lại bước (2).
5. **[FARM-SAFETY — BẤT DI BẤT DỊCH] CẤM QUÉT DIỆN RỘNG Ổ ĐĨA:** CẤM TUYỆT ĐỐI Coordinator và Worker tự ý chạy `grep -rn`, `find`, `os.walk`, `glob(recursive=True)`, `search_files` hoặc bất kỳ lệnh tìm kiếm đệ quy diện rộng nào trên toàn bộ `D:/Taadaa` (kể cả `.ai-runs/`, `runtime/`), TRỪ KHI có lệnh đích danh từ User. Chỉ được inspect đúng file/đường dẫn cụ thể đã biết trước (O(1)).

## ANTI-OVERENGINEERING / USER FLOW OVERRIDE
When the user gives a concrete operational flow (do step -> capture screenshot -> report -> next step), follow that flow exactly.
Do not add unrequested architecture, extra workers, broad fleet locks/stops, speculative mapping/recovery layers, or long status explanations. Use the smallest next action.
For UI/device tasks, after each state-changing step capture and deliver the screenshot (Ngoại lệ: Canary trong Pipeline A-Z gom ảnh vào báo cáo nghiệm thu trọn gói Bước 4); do not replace screenshot evidence with logs.
If blocked, report one blocker and stop; do not expand scope.
Batch totals are context only; action scope is named/proven targets.

# HARD INVARIANT: 1 TASK = 1 FILE = 1 TEST (< 30s)
- CẤM TUYỆT ĐỐI Coordinator gộp nhiều file code vào 1 lần delegate_task.
- Mọi task code bắt buộc: (1) DUY NHẤT 1 file code nghiệp vụ, (2) SOL_PLAN_ID hợp lệ từ Sol Planner (áp dụng cho task dispatch T2; T1 sửa hiện trường O(1) miễn trừ), (3) Budget <= 30 dòng, (4) 1 lệnh focused test < 30s.
- Vi phạm sẽ bị Hook vật lý chặn đứng ngay lập tức tại cửa dispatch.


# HARD INVARIANT: QUY CHUẨN ĐIỀU PHỐI TỨ TRỤ (TIERED WORKFLOW)
- Tham chiếu chi tiết: D:/Taadaa/tools/TIERED_WORKFLOW.md
- T0 (Hiện trường/Log/ADB): Gemini Coordinator làm trực tiếp O(1).
- T1 (Vá hiện trường <= 15 dòng, 1 file): Gemini Coordinator ĐƯỢC PHÉP TỰ SỬA TRỰC TIẾP, verify < 30s. Hậu kiểm cuối phiên qua Closeout Gate.
- T2 (Thi công lớn/Kiến trúc > 15 dòng): Bắt buộc đi qua Terra Plan (3-5s) -> Luna High thi công trong Lồng Vô Trùng -> cage_gate.py nghiệm thu.
- Break-glass (Cấp cứu khi >= 3 máy chết / farm dừng): Gemini được quyền hotfix trong 15 phút để thông đường.

---

## 🌐 HERMES GATEWAY & NETWORK INVARIANTS (CHỐNG TREO POLLING/WEBHOOK)
1. **Telegram Polling Mode:** Hermes Gateway Telegram chạy ở chế độ Long Polling qua Cloudflare WARP local SOCKS5 proxy (`TELEGRAM_PROXY=socks5://127.0.0.1:40000`).
   - CẤM bật lại Webhook (`TELEGRAM_WEBHOOK_URL`) khi chưa có queue chuyên dụng: Máy chủ Telegram sẽ áp dụng cơ chế phạt backoff (ngừng gửi tin 5-15 phút) khi handler không kịp trả HTTP 200 do Event Loop bận.
2. **Quy tắc HTTPX SOCKS Scheme:** Hermes Python runtime sử dụng `httpx 0.27.2`.
   - CẤM TUYỆT ĐỐI dùng scheme `socks5h://` (gây lỗi fatal `Unknown scheme for proxy URL` làm crash-loop Telegram).
   - BẮT BUỘC dùng `socks5://127.0.0.1:40000` (kết hợp `socksio`, WARP tự động phân giải DNS từ xa an toàn).
3. **Foreground Terminal Clamp:** Hook `guard_broad_grep.py` ép cứng mọi lệnh terminal foreground có `timeout <= 60s`.
   - Lệnh thiếu timeout -> Block `GUARD_FOREGROUND_TIMEOUT_MISSING`.
   - Lệnh timeout > 60s -> Block `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`.
   - Mọi tác vụ nặng (>30s) bắt buộc chạy nền qua `terminal(background=True, notify_on_complete=True)`.

