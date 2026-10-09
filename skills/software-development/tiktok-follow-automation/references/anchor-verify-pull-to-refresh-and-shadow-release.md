# Anchor Verify, Pull-to-Refresh & TikTok Backend Shadow Release

## 1. Cơ chế Verify Anchor trong Mode 2 (`_ensure_anchor_followed`)

Trước khi khai thác danh sách Following của một Anchor (Tik1/Tik2), runner bắt buộc phải follow Anchor đó theo quy trình tương tác tự nhiên:
1. **Mở video đầu tiên của Anchor**: Tìm video cover, chạm mở video.
2. **Dwell time**: Xem video 8 - 15 giây ngẫu nhiên.
3. **Thả tim ngẫu nhiên**: Tỷ lệ 50% - 70%.
4. **Follow trên màn hình video**: Bấm nút Follow overlay (dấu + hoặc content-desc `Follow`).
5. **Back về Profile Anchor**: Chờ 2 - 4 giây, nhấn back.
6. **Pull-to-Refresh Profile**: Gọi `pull_to_refresh_profile(adapter)` thực hiện cử chỉ vuốt từ `y1 ~ 35%` xuống `y2 ~ 78%` màn hình để ép TikTok app fetch lại dữ liệu quan hệ mới nhất từ server.
7. **Đọc trạng thái quan hệ sau reload**:
   - `followed`: Nút đổi sang `Nhắn tin` / `Message` hoặc `Đã follow` $\rightarrow$ Ghi nhận thành công 1 lượt (`res.followed.append(uid)`), tiếp tục mở tab Following.
   - `not_followed`: Nút văng ngược lại `Follow` (màu đỏ) $\rightarrow$ Đánh dấu `FOLLOW_FAILED: anchor @{uid} bị nhả sau vuốt — dừng session`.

---

## 2. Bản chất hiện tượng Shadow Release & Rollback của TikTok Server

### Vì sao Anchor 1 được nhận nhưng cuối phiên Web/DB lại không tăng?
- **Độ trễ kích hoạt ngưỡng chặn (Threshold Activation Latency)**:  
  Khi tài khoản bắt đầu phiên, ở lượt follow đầu tiên (Anchor 1), thuật toán chống bot của TikTok có thể chưa kích hoạt cờ hạn chế. Server tạm thời chấp nhận hoặc app nhận response thành công $\rightarrow$ nút chuyển thành `Nhắn tin`. Runner verify bằng pull-to-refresh thấy nút `Nhắn tin` nên **bắt buộc phải ghi nhận hợp lệ**.
- **Rollback khi chạm cờ ở lượt kế tiếp**:  
  Khi máy chuyển sang Anchor 2 hoặc thực hiện follow tiếp theo và bị server TikTok đánh cờ action limit:
  - Anchor 2 bị văng nút đỏ ngay lập tức (`anchor bị nhả sau vuốt`).
  - Phía TikTok backend âm thầm **drop hoặc rollback toàn bộ các action follow vừa thực hiện trong session đó**.
  - Kết quả: Bộ đếm `Following` của chính nick đó trên app lẫn trên TikTok Web DB không hề tăng (delta = 0).

### Không nhầm lẫn giữa "Runner không verify" và "TikTok backend rollback":
- Runner **thực sự có vuốt và có verify** từng anchor và từng row profile (Path B).
- Bằng chứng kiểm tra thực tế: Khi chạy lại canary độc lập trên chính con Anchor 1 khi tài khoản đã bị dính cờ, cú vuốt reload bắt dính ngay lập tức nút `Follow` màu đỏ và dừng session với `status: CANARY_FAILED`.

---

## 3. Quy tắc Đối soát cho Watchdog

Khi watchdog đối soát số liệu phiên nuôi/follow:
1. **Không phạt cứng lệch âm khi có cờ `FOLLOW_FAILED`**:  
   Nếu runner kết thúc với `status: FOLLOW_FAILED` (dính nhả follow), dù `followed_count > 0` (đã ăn được 1-2 nick trước đó), watchdog **không được kỳ vọng Web TikTok phải tăng đủ số lượng đó**.
2. **Phân loại nguyên nhân rõ ràng**:  
   Ghi chú rõ trong báo cáo: `Web +0 (Tài khoản dính FOLLOW_FAILED ở lượt sau, TikTok server rollback action)`, tránh báo lỗi sai lệch ảo làm nhiễu quy trình vận hành.

---

## 4. Lưu ý Kỹ thuật về Targeted Canary Hook (`run_follow.py`)

Khi chạy kiểm thử canary đơn lẻ với `--canary-hook open_following_tab`:
- `FollowEngine` bắt buộc phải được truyền instance `FollowState` hợp lệ:
  ```python
  try:
      state = FollowState(args.machine, cfg, account_row_index=args.account_row_index)
  except TypeError:
      state = FollowState(args.machine, cfg)
  engine = FollowEngine(adapter, cfg, mapping, state)
  ```
- Tuyệt đối không truyền `state=None` vì các hàm con bên trong Mode 2 đều gọi `engine.state.budget_remaining()`, nếu truyền `None` sẽ crash với lỗi `AttributeError: 'NoneType' object has no attribute 'budget_remaining'`.
