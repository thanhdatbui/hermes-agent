# Organic Feed Follow Safety, Cooldown & Young Account Gating (2026-09-24)

## 1. Bối cảnh & Hiện Tượng
- Trong repo `tiktok-luot nuoi acc`, ngoài luồng Follow chéo có chủ đích (`_run_follow_hook` qua Mode 1/2), phiên lướt feed (`feed_session_smoke` trong `feed_swipe_smoke.py`) có cơ chế **Follow tự nhiên (Organic Feed Follow)** với tỷ lệ mặc định 5% ngoài FYP (và 20% trên video Deep Inspect).
- **Vấn đề phát sinh**:
  1. Khi một nick đang bị phạt nhả follow (Action Block / Silent Drop) hoặc đang trong chu kỳ hạ nhiệt Cooldown, nếu tiếp tục bấm follow tự nhiên khi lướt feed thì backend TikTok vẫn tiếp tục rollback $\rightarrow$ Tụt tỷ lệ *Follow Persistence Ratio* $\rightarrow$ Tăng nguy cơ bị gắn cờ bot dai dẳng hoặc phạt nặng hơn (Shadowban, cấm tương tác).
  2. Nick đang trong ngày dưỡng sinh (1/3) theo quy tắc Lifecycle: *"Dưỡng sinh = 0 Follow + 0 Upload"* $\rightarrow$ Nếu không chặn ở tầng feed session thì nick vẫn bị bấm follow tự nhiên 1–3 lượt ngoài FYP.
  3. Nick non / trẻ (< 10 video, chưa ngâm đủ ngày tuổi) không tham gia follow chéo nên không có file state cooldown (`follow_state_*_row_*.json`) $\rightarrow$ Các bộ lọc cooldown bị lọt lưới $\rightarrow$ Nick non vẫn bị bấm follow tự nhiên.

## 2. Bẫy Signal-to-Noise: Vì Sao Cấm Dùng Tracker Bắt Nhả Trên Nick Non?
- **Ngụy biện thường gặp**: "Dùng data từ Tracker cào profile sau phiên lướt, nếu `followingCount` tụt -1 hoặc không tăng thì cắm cờ nhả follow rồi tống nick non vào dưỡng sinh".
- **Thực tế kỹ thuật (Anti-Overengineering Trap)**:
  - Một phiên lướt feed thực tế chỉ phát sinh 1–3 lượt follow tự nhiên. Delta quá nhỏ ($\Delta = +1, 0, -1$) nằm hoàn toàn trong vùng **Nhiễu Tín Hiệu (Noise)**:
    * Delta -1 có thể do 1 kênh nick từng follow tuần trước bị ban/xóa/đổi tên.
    * Delta 0 có thể do web cache TikTok cập nhật trễ vài phút.
    * $\Delta FollowingCount = -1$ **KHÔNG ĐỒNG NGHĨA** với việc tài khoản vừa bị TikTok phạt nhả follow.
  - Sử dụng count delta lẻ làm hard trigger phán xét sẽ gây **False Positive tràn lan**, giam oan hàng loạt nick non vào chu kỳ dưỡng sinh đóng băng.
- **Quy tắc vàng (Sol High Review & Consensus)**:
  - **NON / TRẺ (< 10 video) = 0 AUTOMATED FOLLOW**: Giải quyết dứt điểm bằng chính sách chặn ở đầu vào (`follow_probability = 0`), tuyệt đối không cố xây hệ thống tracking đối soát delta lẻ 1–2 ở đầu ra.

## 3. Kiến Trúc Chốt Chặn 3 Lớp Bắt Buộc

### Lớp 1: Gating trong `_maybe_follow_video` (`feed_swipe_smoke.py`)
Mọi hành vi bấm nút Follow trên video FYP đều phải vượt qua 3 cổng tuần tự:
```python
# Cổng 1: Kiểm tra Cooldown nhả follow (phân tách theo machine và row)
if is_account_in_follow_cooldown(ctx):
    # Log skipped: account is in follow cooldown (imprisoned)
    return False

# Cổng 2: Kiểm tra Ngày Dưỡng Sinh (1/3)
cfg = getattr(ctx, "config", {}) or {}
if cfg.get("_is_organic_rest") or cfg.get("rest_day_no_follow"):
    # Log skipped: account is in organic rest day (0 follow)
    return False

# Cổng 3: Kiểm tra Ngưỡng Video (Nick non)
video_count = cfg.get("_video_count")
if video_count is not None and int(video_count) < 10:
    # Log skipped: account has under 10 videos (natural follow disabled)
    return False
```

### Lớp 2: Gating Cấu Hình Tầng Launcher (`multi_machine_feed_session.py`)
Trước khi điều phối worker mở luồng `feed_session_smoke(child_ctx)`:
1. Đọc số video: `video_count = getattr(account, "video_count", None) or getattr(account, "video_posted", None) or 0`.
2. Kiểm tra ngày dưỡng sinh: `is_organic = _is_account_organic_rest_day(account.machine, account.account_row_index)`.
3. Gán metadata rõ ràng: `child_config["_is_organic_rest"] = is_organic`, `child_config["_video_count"] = video_count`.
4. **Triệt tiêu cấu hình follow**: Nếu `is_organic` hoặc `video_count < 10` hoặc `rest_day_no_follow`:
   `child_config["_follow_rate"] = {"for_you": 0, "following": 0, "friends": 0}`.

### Lớp 3: Popup & Thẻ Đề Xuất
- `follow_back_suggestion` (`feed_swipe_smoke.py`): Nếu nick đang trong cooldown, tap nút "Không quan tâm" để đóng thẻ.
- `dismiss_follow_friends_suggestion_popup` (`benign_popup.py`): Nếu nick trong cooldown, set `follow_limit = 0`, bỏ qua việc tap 2 nút follow bạn bè, đóng thẳng bằng nút `X` / semantic close.

## 4. Chuẩn Hóa Telemetry & Bẫy Chấm Điểm Sol Reviewer (Closeout Gate >= 85)
- **Bẫy Silent Roll Skip (82đ -> >= 85đ)**:
  + Khi `random.randint(1, 100) > int(follow_rate_percent)`, KHÔNG ĐƯỢC im lặng `return False`.
  + BẮT BUỘC ghi log telemetry rõ ràng:
    `action="follow_video", result="skipped", error="roll skipped by follow rate percent", extra={"follow_rate_percent": follow_rate_percent}`.
- **Tiêu Chí Kiểm Thử 2 Chiều (Bi-directional Test Evidence)**:
  + Khi viết unit tests cho follow gating, ngoài 2 test case chặn (Organic Rest Day và < 10 video), BẮT BUỘC phải có test case đối chứng:
    1. `test_maybe_follow_video_permitted_when_eligible`: Chứng minh tài khoản sạch, không dưỡng sinh, >= 10 video VẪN FOLLOW BÌNH THƯỜNG.
    2. `test_multi_machine_child_config_gating_contract`: Chứng minh `child_config` truyền đúng contract từ `multi_machine_feed_session.py` xuống worker.

