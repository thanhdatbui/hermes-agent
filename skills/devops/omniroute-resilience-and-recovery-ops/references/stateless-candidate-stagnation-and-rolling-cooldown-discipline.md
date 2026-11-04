# Kỷ Luật Chống Bẫy Kẹt Lì Ứng Viên (Stateless Candidate Stagnation), Rolling Cooldown & Zero-Silence On Failure

## 1. Bản Chất Sự Cố & Bệnh Lý (The Infinite Stagnation Trap)
Khi thiết kế watchdog hoặc cronjob xử lý theo đợt (batch) trên farm tài nguyên (GPM profiles, ChatGPT Web accounts, Gmail 2FA, phone farm devices) với cấu trúc `LIMIT N` (ví dụ: bốc 5 hoặc 10 candidates mỗi chu kỳ tick):
- **Tử huyệt thiết kế (Anti-Pattern):** Viết hàm `get_candidates()` theo kiểu **Stateless** (hoàn toàn không lưu vết hoặc không đọc state lịch sử), query thẳng vào database dạng `SELECT ... ORDER BY Id ASC LIMIT N`.
- **Hậu quả vận hành nghiêm trọng:**
  1. Khi $N$ ứng viên đầu tiên trong danh sách gặp sự cố khách quan (văng session Google Auth, vướng checkpoint xác minh điện thoại S7, proxy 4G die, Cloudflare 403, lỗi UI) $\rightarrow$ lượt chạy thất bại hoàn toàn (`0/N`).
  2. Ở chu kỳ cron tiếp theo (5 phút hoặc 15 phút sau): Vì $N$ tài khoản này vẫn chưa hoàn thành mục tiêu, hàm `get_candidates()` lại thực hiện đúng câu query cũ và **LẠI BỐC TIẾP ĐÚNG $N$ TÀI KHOẢN ĐÃ CHẾT ĐÓ RA CHẠY LẠI**!
  3. Cron rơi vào vòng lặp kẹt lì vô tận (**Infinite Stagnation Loop**), cày nát $N$ tài khoản lỗi cả ngày, trong khi **bỏ rơi 100% hàng trăm tài khoản khỏe mạnh phía sau không bao giờ được chạm tới**!
  4. Nếu script lại dính thêm bẫy "nuốt lỗi" (`if success_list:` mới print báo cáo hoặc cron để `deliver: local`), hệ thống sẽ hoàn toàn im lặng, người vận hành tưởng cron vẫn chạy êm nhưng thực chất toàn bộ dây chuyền tự động hóa đã tê liệt.

---

## 2. Ba Quy Chuẩn Kỹ Thuật Bắt Buộc (Mandatory Invariants)

Mọi watchdog/cron có logic bốc tập con ứng viên (`LIMIT N`) từ kho tài nguyên BẮT BUỘC phải tuân thủ 3 nguyên tắc cơ học sau:

### Invariant 1: State-Aware Candidate Filtering (Lọc Ứng Viên Nhận Thức State)
Hàm lấy ứng viên `get_candidates()` **BẮT BUỘC PHẢI ĐỌC STATE FILE / LỊCH SỬ THỬ** trước khi tuyển chọn:
- Phải nạp danh sách các tài khoản đã xử lý trong ngày (`last_run_date == today`) hoặc đang trong thời gian cooldown tạm thời (12h – 24h).
- Tự động loại trừ toàn bộ tập hợp này ra khỏi pool tuyển chọn:
  ```python
  # Chuẩn hóa loại trừ tài khoản đã thử/thất bại trong ngày
  excluded_today = set()
  if STATE_FILE.exists():
      data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
      if data.get("last_run_date") == today_str:
          for item in data.get("failed", []) + data.get("success", []) + data.get("pending", []):
              email = item.split(":")[0].strip().lower()
              if email:
                  excluded_today.add(email)

  # Trong vòng lặp tuyển chọn candidate:
  if email in excluded_today:
      continue
  ```

### Invariant 2: Rolling Cooldown & FIFO Rotation (Xoay Vòng Cuốn Chiếu)
- Đối với các cron chạy dày (mỗi 5 – 15 phút): Nếu tài khoản thất bại, phải ghi nhận `failed_at = now_ts` vào file cooldown (như `failed_candidates_cooldown.json`).
- Trong vòng 12 tiếng tiếp theo, script bắt buộc phải bỏ qua tài khoản đó để nhường slot cho các tài khoản phía sau.
- Nhờ cơ chế này, $N$ worker sẽ **cuốn chiếu liên tục qua toàn bộ hàng trăm tài khoản trong kho**, đảm bảo mọi tài khoản đều có cơ hội được xử lý.

### Invariant 3: Zero-Silence On Failure (Không Bỏ Rơi Lỗi Trong Bóng Tối)
- **CẤM TUYỆT ĐỐI** viết điều kiện `if success_list:` để bọc khối báo cáo.
- Khi toàn bộ batch thất bại (`success_cnt == 0`), script **BẮT BUỘC PHẢI BÁO CÁO** (bắn tin nhắn Telegram về kênh chuyên trách như `-5256944036` hay `-5373649734`).
- Bản tin báo cáo bắt buộc liệt kê rõ danh sách các tài khoản kẹt kèm lý do ngắn gọn (ví dụ: `NO_SESSION`, `CHECKPOINT_S7`, `PROXY_UNREACHABLE`) để người vận hành nhìn thấy và can thiệp thủ công ngay lập tức.
