# Case Máy 8: Cạm Bẫy "Hypothesis Roulette", Ngộ Nhận Toạ Độ Tâm Container & Cơ Chế Khóa Cứng "Ground Truth First" (07/09/2026)

## 1. Hiện Tượng Thực Tế & Cảnh Báo Từ User (Sự Cố Máy 8)
- **Cảnh báo farm:** `[FARM ALERT: MÁY 8] DỪNG PHIÊN - Nick: tolmavhj12k - profile username still mismatched after switch`.
- **Phản ứng gay gắt từ User:** *"Mày lại bắt đầu over engineer r phải k"*, *"Hqua t vs claude đã siết chặt để mày k bị over engineer. Nay lại tái diễn, gọi claude cli ra điều tra cho tao"*.
- **Diễn biến vòng lặp suy diễn của Coordinator (Hypothesis Roulette - 6 lần xoay tua):**
  1. *Lần 1 (Pattern-matching cũ):* Cho rằng bị Feed Drift theo Case 79 -> dispatch worker kiểm tra `feed_swipe_smoke.py`.
  2. *Lần 2 (Canary thất bại):* Chạy Canary B4 dính `swipes completed: 0`, profile username still mismatched.
  3. *Lần 3 (Ngộ nhận hình học sơ đẳng):* Thấy runner tap vào `x=540` trên container `[0, 600][1080, 816]`, ngộ nhận `x=540` là "khoảng trống chết (dead whitespace) bên phải" -> dispatch worker sửa `_find_account_switch_option` để tap vào inner `TextView` ($x \approx 393$) hoặc clamp về nửa trái.
  4. *Lần 4 (Kẹt lock):* Đẻ tiếp Canary và bị vướng lock do tiến trình nền `multi-machine-feed-session` đang chạy.
  5. *Lần 5 (Chạy đồng bộ timeout):* Chạy lệnh PowerShell Canary trực tiếp tại session chính dính trần timeout 600s làm nghẽn toàn bộ phiên làm việc.
  6. *Lần 6 (Đổi tiếp giả thuyết):* Đọc log thấy tap trúng `[393, 708]` nhưng nick vẫn không đổi -> lập tức suy diễn lệnh tap 0ms bị Android nuốt và dispatch worker đổi sang `input swipe 120ms`.

---

## 2. Kết Luận Audit Độc Lập Từ Claude CLI Opus High
> **"VERDICT: Hermes Coordinator CÓ TỘI over-engineering tái diễn.**
> Điểm sai chí tử: Đổi giả thuyết nhanh hơn tốc độ kiểm chứng giả thuyết. Debug bằng cách đọc XML/log rồi tưởng tượng ra cơ chế mà không một lần quan sát màn hình thật sau tap để lấy Ground Truth!
> Lỗi logic đáng xấu hổ: `x=540` trên màn hình $1080$ là **tâm ngang chuẩn xác ($1080/2$)** của một row full-width, là điểm tap đáng tin cậy nhất. Việc clamp về $393$ được xây dựng trên sự ngộ nhận. Tap vào $393$ trúng child `TextView` có `clickable="false"` bị Android nuốt sự kiện, chính là nguyên nhân làm TikTok không switch."

---

## 3. Sự Thật Trần Trụi Khi Lấy Ground Truth
1. Khi bấm thủ công vào đúng tâm container `540 708`: **TikTok chuyển ngay lập tức sang nick `tolmavhj12k`!**
2. Thủ phạm gây lỗi: Commit `60b3253` lúc 07:07 sáng do worker trước tự ý đổi toạ độ từ $540$ sang $393$ (chạm vào view không clickable).
3. Hiện trường sau switch: TikTok đổi nick thành công sang `@tolmavhj12k` (Display name là `Linhnguyen1707`), kèm popup gợi ý kết bạn ("Follow bạn bè của bạn").
4. Khắc phục: `git revert 60b3253` (commit `6da1ba9`), khôi phục toạ độ tap chuẩn tâm $x=540$.
5. Canary B4 trên Máy 8: **PASS 2/2 swipes** (`final_status: success`, exit code 0).

---

## 4. Ba Tầng Khóa Cứng Phòng Chống Over-Engineering (Plugin `farm-coordinator-guard`)

Không tin vào kỷ luật tự giác bằng prompt của LLM, toàn bộ cơ chế đã được cài đặt thành **Hard Gates cơ học**:

### Tầng 1: Ground Truth First Hard Guard (Cấm Sửa Code Khi Chưa Có Bằng Chứng)
- Can thiệp vào hook `_on_pre_tool_call` khi `fn_name == "delegate_task"`.
- Nếu goal/context yêu cầu: sửa code, fix code, patch contract...
- Kiểm tra bắt buộc phải có bằng chứng hiện trường thực tế (`screencap`, `screenshot`, `inspect_machine`, `.png`, `.xml`, `màn hình hiện trường`, `ảnh hiện trường`).
- **Nếu CHƯA CÓ:** Chặn đứng vật lý (`action: block`), ném lỗi `⛔ [COORDINATOR GUARD - GROUND TRUTH FIRST BLOCKED]`. Ép Coordinator phải chụp ảnh màn hình hoặc inspect O(1) trước khi dispatch sửa code.

### Tầng 2: Dispatch Budget Hard Guard (Tối đa 3 Worker / Ca Alert)
- Quản lý `dispatch_count` theo từng `session_id`.
- Giới hạn cứng `MAX_COORDINATOR_DISPATCHES = 3`.
- Nếu Coordinator dispatch đến lần thứ 4: Chặn đứng vật lý (`⛔ [COORDINATOR GUARD - DISPATCH BUDGET EXHAUSTED]`). Bắt buộc dừng lại báo cáo blocker cho user hoặc gọi Claude CLI thẩm định độc lập.

### Tầng 3: Ưu Tiên Farm Alert Tuyệt Đối
- Trong `_on_pre_llm_call`: Farm Alert regex luôn được đối soát trước Closeout regex để tránh template prompt chứa chữ "closeout" vô tình kích hoạt phase CLOSEOUT làm lọt guard.
