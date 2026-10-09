# PHÂN TÍCH THỰC NGHIỆM HỒI PHỤC SHADOWBAN, GEMPHONEFARM COMPARISON & PROTOCOL CHỐNG NHẢ FOLLOW (2026-09-12)

## 1. Bản chất hiện tượng "Nhả Follow" (Silent Follow Drop) & Cơ chế Risk Control TikTok
- **Thực nghiệm thiết bị thật (Máy 24 - Row 2, `ce0117112b2a0e3a04`):**
  - Bấm nút Follow trực tiếp bằng ADB thô (`input tap 288 855`) trên profile `@lipsellczaw`.
  - Trên local UI: Nút chuyển sang "Nhắn tin" và giữ nguyên suốt 60 giây đứng im.
  - Sau đó thoát app về Home, 5s sau mở lại đúng profile: **Nút đỏ `Follow` lập tức xuất hiện trở lại**; vuốt reload (pull-to-refresh) vẫn trơ trơ nút đỏ.
  - $\rightarrow$ **Kết luận thực nghiệm:** Không phải bot tự phán sai, không phải lag UI. **Server TikTok thật sự đã DROP (Silent Drop) lượt follow ngay tại backend do tài khoản nằm trong Dynamic Quarantine / Action Block.**

- **Tại sao ngâm Cooldown đơn thuần (chỉ đếm ngày) thất bại 100% (0/127 acc tự hồi phục)?**
  - Backend Anti-Abuse của ByteDance tính điểm Trust Score dựa trên **telemetry hoạt động thực tế** (Sliding Window 14–21 ngày, hàm phân rã EWMA).
  - Không có traffic tương tác lành mạnh = backend không ghi nhận event = Trust Score không tăng.
  - Khi ngâm 4–7 ngày mà tài khoản chỉ lướt feed "zombie" (do bug nút Like 0 like suốt từ 18/08 đến 12/09) $\rightarrow$ Trust Score vẫn = 0. Hết hạn cooldown bấm follow lại lập tức bị server dập tiếp và tăng streak lên 2 hoặc 3.

- **Về trick "Chuyển nick ngâm qua đêm (Account Switcher trước 7-8 tiếng)":**
  - **Phân tích kỹ thuật & Claude Opus khẳng định:** Hoàn toàn **KHÔNG CÓ TÁC DỤNG** tăng độ trâu hay giảm nhả follow.
  - Ban đêm máy tắt màn hình, app idle không gửi telemetry lên server $\rightarrow$ backend coi đó là khoảng trống (gap), không tính điểm ngâm.
  - Sáng hôm sau mở app vẫn là Cold Start, Play Integrity token chỉ có hiệu lực vài phút nên vẫn phải attest lại từ đầu.
  - Ngược lại, nếu đêm nhà mạng tự xoay IP/proxy reconnect $\rightarrow$ phiên tạo ở IP cũ nhưng dùng ở IP mới gây **Lệch Network Context (Network Mismatch)**, càng dễ dính cờ bot!
  - **Quy trình chuẩn:** Đến đúng giờ ca chạy mới mở app $\rightarrow$ check mạng $\rightarrow$ switch nick $\rightarrow$ lướt feed 15-25 phút $\rightarrow$ mới follow/upload.

---

## 2. Các mắt xích đã khắc phục & Nâng cấp toàn diện (12/09/2026)

### A. Sửa triệt để lỗi 0 Like trên Feed (Repo `tiktok-luot nuoi acc`)
- **Nguyên nhân gốc rễ:** Đêm 17/08/2026, TikTok gộp node icon `ImageView` có `content-desc="Thích"` vào chung button ngoài `content-desc="Thích video. 41,3K lượt thích"`. So sánh bằng tuyệt đối `== "Thích"` làm tê liệt tính năng like suốt 26 ngày.
- **Bản vá:** Quét tiền tố `desc.lower().startswith("thích video")` hoặc `"like video"` hoặc `txt.lower().startswith("thích")`, đồng thời loại trừ header tab navigation (`center[1] < 350`).
- **Báo cáo Watchdog:** Đã tích hợp chỉ số tổng lượt thả tim vào Telegram watchdog (`feed_session_watchdog.py`) để kiểm soát realtime.

### B. Tăng số lượng video & Nâng Timeout an toàn
- Nâng số video lướt mỗi phiên từ `8 - 11` lên **`16 - 22` video (Max 28 swipes)**.
- Phân bổ: 70% Đề xuất (xen kẽ Fast Swipe 2–4s và Deep Inspect 8–15s), 15% Đang follow (Deep 4–12s), 15% Bạn bè (Deep 5–15s).
- Nâng `DEFAULT_DEVICE_TIMEOUT_SECONDS` từ `2100.0` (35 phút) lên **`3000.0` (50 phút)** để đảm bảo máy chạy đủ 25–35 phút mà không bao giờ văng timeout.

### C. Triển khai lớp Post-Cooldown Warm-up (Repo `tiktok-follow`)
- Trong `follow_state.py`: Thêm cờ `is_post_cooldown_warmup` cho nick có `fail_streak > 0` và `follow_failed == False`.
- Khi vừa ra tù: Chỉ cấp budget thăm dò **3 – 5 follow / phiên** (thay vì 6–10 follow).
- Follow 3–5 nick thành công $\rightarrow$ tự động xóa `fail_streak = 0`, gỡ cờ hồi phục hoàn toàn.

### D. Tích hợp Ad Fast-Skip (học từ script GemPhoneFarm anh Khoa)
- Trong `feed_swipe_smoke.py`: Bổ sung quét `iter_elements` phát hiện chữ `"Được tài trợ"` hoặc `"Sponsored"`.
- Phát hiện video quảng cáo $\rightarrow$ quẹt lướt bỏ qua ngay trong 0.5s (`skip_sponsored`), không xem lâu và không thả tim nhầm vào quảng cáo.
