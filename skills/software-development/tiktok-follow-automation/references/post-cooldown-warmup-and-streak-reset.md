# Post-Cooldown Recovery & Warmup Budget Pitfalls

## 1. Bản chất về hiện tượng tài khoản hồi phục sau khi bị nhả follow
- **Quan niệm sai lầm**: Nghĩ rằng nick TikTok một khi đã bị phạt nhả follow (`FOLLOW_FAILED` / shadow release) thì coi như "hỏng hẳn" và không bao giờ follow lại được.
- **Thực tế vận hành Phone Farm**:
  - TikTok áp dụng cơ chế shadow-ban tạm thời (soft trừng phạt) từ 24h đến vài ngày đối với các hành vi bất thường.
  - Khi tài khoản được đưa vào danh sách Cooldown (ngưng follow hoàn toàn từ 1 đến 4 ngày) nhưng **vẫn duy trì lướt Feed, xem video, thả tim và tương tác người dùng thật**, tài khoản sẽ tích lũy lại trust.
  - Sau khi mãn hạn cooldown, TikTok sẽ tự động mở lại quyền follow. Minh chứng thực tế ngày 15/09/2026 trên dàn Phone Farm Kibe: Hàng loạt nick Row 1 từng dính `FOLLOW_FAILED` liên tiếp trong quá khứ (như M4, M20, M26, M27, M29, M35, M42, M43, M60, M72) đều đã follow thành công trở lại và được xác nhận trực tiếp trên profile.

## 2. Quy tắc ngân sách dò lại (Warmup Budget - `is_post_cooldown_warmup`)
- Khi nick vừa mãn hạn cooldown (`fail_streak > 0` và `follow_failed == False`):
  - **TUYỆT ĐỐI KHÔNG** cấp full budget thông thường (15 - 20 lượt hoặc 6 - 10 lượt).
  - BẮT BUỘC chỉ cấp ngân sách thử nghiệm: **3 – 5 lượt follow/phiên** (`return _random.randint(3, 5)`).
  - Mục đích: Thăm dò xem TikTok đã thực sự gỡ nhãn phạt shadow-ban hay chưa mà không làm bùng phát lại cờ spam.

## 3. Cạm bẫy kỹ thuật nghiêm trọng: Xóa `fail_streak` quá sớm trong `FollowState.mark()`
- **Vấn đề phát hiện**:
  Trong hàm `FollowState.mark(uid, status)`:
  ```python
  if status == self.STATUS_FOLLOWED:
      self._data["followed"][uid] = now_iso
      if last_failed_at is None or now_utc >= last_failed_at:
          self._data["fail_streak"] = 0  # <--- CẠM BẪY LỚN!
          self._data["follow_failed"] = False
  ```
- **Hậu quả**:
  - Ngay khi nick vừa follow thành công **phát đầu tiên** ở Phiên 1, `fail_streak` bị xóa ngay về `0`.
  - Việc này làm cho `is_post_cooldown_warmup` lập tức trở thành `False`.
  - Đến Phiên 2 trong cùng ngày, hệ thống nhận diện nick như một tài khoản "sạch 100%" và cấp full budget (như trường hợp Máy 4 bị cấp vọt lên 17 lượt follow ở Phiên 2).
  - Việc này phá vỡ hoàn toàn chu trình "chạy dò nhẹ" và khiến nick đối mặt với nguy cơ tái phạt lập tức.
- **Giải pháp kiến trúc**:
  - Không được xóa `fail_streak` ngay lập tức chỉ sau một lần follow thành công.
  - Cần duy trì streak warmup trong tối thiểu **24 giờ** hoặc **qua ít nhất 2 phiên chạy thành công liên tiếp** trước khi reset hoàn toàn về 0.
