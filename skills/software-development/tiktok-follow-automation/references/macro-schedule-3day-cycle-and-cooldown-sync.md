# Quy Trình Vận Hành Farm TikTok: Chu Kỳ 3 Ngày & Khắc Phục Phạt Nhả

Tài liệu đúc kết từ thực chiến farm 160 máy của đối tác và phản biện kiến trúc của Sol (GPT-5.6 Sol High), đã được kiểm chứng và vá lỗi code state.

---

## 1. Móng Tài Khoản (Bắt buộc trước khi đi follow)
- **Hard Gate $\ge 10$ video**: Tài khoản bắt buộc phải đăng đủ $\ge 10$ video mới được cấp budget đi follow chéo.
- **Giai đoạn ngâm mồi (0-30 ngày đầu)**:
  - Tuyệt đối 0 follow chéo nội bộ.
  - Chỉ chạy script lướt feed nuôi tự nhiên + đăng video vào các khung giờ vàng (9h sáng, 16h chiều, tối muộn).
  - Tích lũy trust score và định hình tệp đề xuất tự nhiên trước khi bước vào mạng lưới tương tác.

---

## 2. Chu Kỳ Vận Hành Vĩ Mô 3 Ngày (4 - 4 - Nghỉ)
Thay vì cày dồn dập mỗi ngày, chia 8 slot trên mỗi máy theo chu kỳ 72h:
- **Ngày 1**: Chạy **Slot 1, 2, 3, 4** (2 phiên follow/ngày $\times$ 10-15 follow/phiên; kẹp 1 phiên đăng video).
- **Ngày 2**: Chạy **Slot 5, 6, 7, 8** (Tương tự Ngày 1).
- **Ngày 3**: **Toàn farm nghỉ follow chéo 100%**, chỉ chạy script lướt feed nuôi giải trí (organic follow 5% tab Đề xuất nếu nick sạch).
- **Ngày 4**: Lặp lại Ngày 1.
$\Rightarrow$ Từng slot có **trọn vẹn 48h nghỉ ngơi** giữa các lần cày follow để xóa điểm bất thường (anomaly score).

### Lưu ý nâng cao (Rolling Rest):
Để tránh tạo nhịp tim mạng tập thể (toàn farm cùng ngừng thở Ngày 3 rồi bùng nổ Ngày 4), khi quy mô lớn nên cho các cụm máy nghỉ so-le (Cụm A nghỉ Day 3, Cụm B nghỉ Day 1, Cụm C nghỉ Day 2).

---

## 3. Tỷ Lệ Phiên & Nhịp Vận Hành
- **Tỷ lệ 2 Follow : 1 Up Video**: Cứ 2 phiên chạy follow phải xen kẽ 1 phiên đăng video mới lên profile để giữ vững trạng thái Creator active.
- **Hạn mức phiên**: 10 – 15 follow/phiên (tối đa 20 – 30 follow/ngày).
- **Staggering delay**: Khởi động lệch nhau 30s – 40s giữa các máy trong cụm.
- **Xóa cache app**: Xóa cache TikTok trong Settings trước khi switch account giữa các slot.

---

## 4. Kiến Trúc State Machine & Auto-Expiry Cooldown (Đạt 9.3/10)
Hàm `is_account_in_follow_cooldown()` tại `feed_swipe_smoke.py` và `FollowState` tại `follow_runner/core/follow_state.py`:
1. **Row Isolation**: Chỉ match file `follow_state_{machine}_row_{row}.json`, cấm tuyệt đối fallback sang `follow_state_{machine}.json` để tránh 1 slot bị phạt kéo theo cả máy.
2. **Chuẩn hóa UTC 100%**: Sử dụng `datetime.now(timezone.utc)` và parse ISO UTC, loại bỏ lỗi lệch ngày giữa giờ Windows local và UTC.
3. **Auto-Sync Expiry (Diệt Zombie State)**:
   - Khi `now_utc >= until_dt`, hàm kiểm tra tự động dọn sạch cờ `follow_failed = False`, reset `fail_streak = 0`, xóa các trường `cooldown_until_*`, `last_failed_*` và ghi đè file JSON bằng cơ chế atomic (`.json.tmp` $\to$ `os.replace`).
   - Tài khoản tự động được mở lại quyền follow khi lướt feed và chuyển từ bấm "Không quan tâm" sang "Follow lại" ở popup gợi ý mà không cần can thiệp tay.
4. **Progressive Backoff**:
   - Dính nhả lần 1 (Streak 1): Cooldown đến hết ngày hôm đó (23:59:59 UTC).
   - Dính nhả lần 2 (Streak 2): Cooldown +4 ngày (1 chu kỳ).
   - Dính nhả $\ge 3$ lần: Cooldown +7 ngày.
