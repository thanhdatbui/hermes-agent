# Case UI-77: Bẫy Mode 2 Chiếm Dụng Thời Gian Gây Đói Mode 1 & Quy Chuẩn Fallback Bắt Buộc Mode 2 -> Mode 1 Chạy Bù Budget (2026-09-29)

## 1. Hiện trường Sự cố (Farm Ca 2 Ngày 29/09/2026)
- **Bối cảnh:** Ca 2 nuôi nick TikTok (Row 3). Toàn farm Kibe có 15 máy đủ điều kiện chạy Follow Hook (không dính ngày dưỡng sinh, không dính cooldown nhả follow, đã đủ >= 6 video).
- **Hiện tượng:**
  - Kết thúc ca chỉ duy nhất M16 follow được 1 lượt (qua anchor `@phungloan0138`).
  - 7 máy (M9, M11, M12, M24, M51, M54, M55) báo `đã follow sẵn (skip)` và dừng với 0 follow.
  - Phản hồi bức xúc từ người dùng: *"15 máy đủ điều kiện có 7 máy quét toàn bộ nick đã follow sẵn nên skip là sao? Module 2 có thất bại cũng phải qua module 1 chứ? Fix cho tao"*.

## 2. Nguyên nhân Cốt lõi (Root Cause Analysis)

### A. Hiểu nhầm "Quét hết toàn bộ nick"
- Thực tế bot **không hề quét hết 1.200 nick trong farm**.
- Kho UIDs nội bộ farm có hơn 1.240 tài khoản chưa follow. Tuy nhiên, mỗi máy chỉ kịp duyệt qua 1–3 nick thì bị ngắt phiên sớm do cơ chế deadline timeout.

### B. Bẫy Mode 2 chiếm dụng thời gian (Time Starvation of Mode 1)
- Chế độ `both` được thiết kế theo nguyên lý Hybrid (16/08): Mode 2 chạy trước (theo anchor Tik1/Tik2), nếu chưa đủ budget thì Mode 1 chạy bù sau.
- Nhưng Mode 2 được cấp 3 anchor ngẫu nhiên (`uids = uids[:3]`). Khi các anchor này gặp lỗi mở tab "Đã follow":
  - Mỗi anchor bị thử 2 lần (lần 1 + lần 2 sau ladder recovery).
  - Mỗi lần thử bị kẹt polling từ 25s đến 35s.
  - Kèm theo thời gian xem video ngẫu nhiên 8–15s và chạy recovery ladder 30s.
  - Tổng thời gian Mode 2 tiêu tốn cho 3 anchor lỗi lên tới **15 – 18 phút** trên tổng trần phiên 20 phút (`feed_timeout_seconds = 1200s`).

### C. Bẫy ngắt sớm `reserve_seconds = 180s`
- Trong `follow_engine.py` (line 855) và `mode1_search_follow.py` (line 50, 136):
  `if callable(has_time) and not has_time(reserve_seconds=180.0): break`
- Khi Mode 2 kết thúc sau 16–18 phút, thời gian còn lại của phiên chỉ còn 100s – 150s (vẫn còn gần 2.5 phút).
- Do ngưỡng `reserve_seconds` đặt quá cao (180s = 3 phút), `has_time_for_next_action` lập tức trả về `False`:
  - Các máy M51, M54, M55: Mode 1 bị bỏ qua 100%, không kịp kích hoạt.
  - Các máy M9, M11, M12, M24: Mode 1 chỉ kịp tìm kiếm đúng 1–2 UID đầu tiên trong danh sách (vô tình là các nick đã follow từ trước đó) thì chạm mốc `remaining < 180s` và thoát êm ái (`completing mode1 gracefully with 0 followed accounts`).

### D. Bẫy chặn luồng khi Mode 2 gán status khác `OK`
- Trong `follow_engine.py`:
  `if mode in ("1", "both") and res.status == STATE_OK:`
- Nếu Mode 2 gặp lỗi UI hoặc lỗi cuộn list và gán `res.status = "MANUAL_REVIEW"` (dù `follow_failed = False`, tức không bị TikTok phạt action block), điều kiện trên bị đánh trượt và Mode 1 bị chặn đứng hoàn toàn.

### E. Selector Drift RecyclerView trên TikTok 47.x
- Hàm `_classify_follower_surface(nodes)` kiểm tra:
  `has_recycler = any(node.get("resource_id") in FOLLOWER_LIST_RECYCLER_IDS for node in nodes)`
- Biến `FOLLOWER_LIST_RECYCLER_IDS` là tuple chứa các obfuscated resource-id cố định (`id/u5r`, `id/u_q`, `id/uoc`, `id/uo1`, `id/uvz`, `id/uzs`).
- Khi TikTok 47.x đổi sang ID mới không nằm trong tuple, `has_recycler` trả về `False` và hàm kết luận bề mặt là `invalid` khi `selected_count != "0"`, dẫn tới việc loop chờ đủ 35s rồi fail.

## 3. Quy chuẩn Khắc phục (Standard Architecture Fix)

### 1. Cơ chế Fallback Bắt buộc Mode 2 ➔ Mode 1
Trong `follow_engine.py`:
```python
if mode == "both" and res.status != STATE_OK and not res.follow_failed and not (self.state is not None and self.state.follow_failed):
    # Mode 2 gặp lỗi UI/anchor nhưng KHÔNG bị TikTok chặn follow (follow_failed=False).
    # Chuyển mode2_degraded=True và reset status về OK để Mode 1 tiếp tục chạy bù budget.
    res.details["mode2_degraded"] = True
    if res.reason:
        res.details.setdefault("mode2_degraded_reasons", []).append(res.reason)
    res.status = STATE_OK
    res.failed = False
    res.reason = ""
```

### 2. Điều phối Ngân sách Thời gian (Yielding to Mode 1)
- Trong `mode2_follow_followers.py`: Khi chạy ở chế độ `both`, Mode 2 bắt buộc phải dành tối thiểu **300 giây (5 phút)** cho Mode 1:
  ```python
  mode2_reserve_seconds = 300.0 if getattr(cfg, "mode", "both") == "both" else 60.0
  for uid in uids:
      if callable(getattr(engine, "has_time_for_next_action", None)) and not engine.has_time_for_next_action(reserve_seconds=mode2_reserve_seconds):
          logger.info("Session deadline approaching for mode2, yielding to mode1 gracefully with %d followed accounts", len(res.followed))
          break
  ```
- Trong `follow_engine.py` và `mode1_search_follow.py`: Hạ `reserve_seconds` từ **180s xuống 60s**. Mỗi thao tác tìm kiếm UID chỉ mất 15–25s, 60s là hoàn toàn đủ an toàn để thực hiện thêm 2–3 lượt follow trước khi trả về Feed.

### 3. Nhận diện Bền vững RecyclerView Class
Trong `_classify_follower_surface(nodes)`:
```python
has_recycler = any(
    node.get("resource_id") in FOLLOWER_LIST_RECYCLER_IDS
    or "recyclerview" in (node.get("class") or "").lower()
    for node in nodes
)
```
Không phụ thuộc duy nhất vào resource-id obfuscated dễ bị trôi sau mỗi bản cập nhật TikTok.

## 4. Bài học Vận hành & Dispatch Guard Hook (Hard Gate #3)
Khi điều phối Worker subagent qua `delegate_task`:
1. **Tuyệt đối không để markdown triple backticks trong `OLD_STRING:`**: Hook `guard_dispatch_contract.py` cắt dòng và so khớp nguyên văn với nội dung file đĩa. Chèn ` ```python ` sẽ làm rớt tỷ lệ match về 0 và kích hoạt lỗi `'OLD_STRING' KHÔNG TỒN TẠI trong file`.
2. **Kỷ luật 1 file nghiệp vụ**: Mỗi subagent task chỉ được phép chứa đúng 1 file `.py`. Muốn sửa nhiều file phải chẻ nhỏ thành các task tuần tự.
3. **Bắt buộc có `FOCUSED_TEST:`**: Lệnh test hoặc compile phải cụ thể (< 30s) và không chứa thêm file `.py` thứ hai để tránh vi phạm quy tắc single-file.
4. **Sol Plan ID**: Phải nạp `SOL_PLAN_ID: sol_plan_xxx` sinh từ `sol_planner.py` còn trong thời hạn 10 phút.
