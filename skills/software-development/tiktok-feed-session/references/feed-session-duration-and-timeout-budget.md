# Phân Tích Ngân Sách Thời Lượng & Target Video Feed Session (Galaxy S7 / S7 Edge)

## 1. Bản chất sự cố chạm trần `max_duration_seconds` (25 phút / 1500s)

Trên farm Android Samsung Galaxy S7 / S7 Edge thực tế:
- **Thời gian khởi động & preflight:** ~150s (2.5 phút) gồm force-stop app, launch TikTok, verify identity / switch account nếu cần, chờ splash load.
- **Thời gian xử lý trung bình mỗi video:** ~40 - 50s/video gồm:
  - Watch delay ngẫu nhiên: 2 - 8s (trung bình ~5s).
  - Thao tác swipe: 0.5 - 1s.
  - Chụp màn hình + dump UI XML qua ATX service (port 7912): 10 - 20s.
  - Quét qua danh sách ~17 popup/ad handler (live stream, shop CTA, reward, friend suggestion, verify bar...): 15 - 20s.

### Quy tắc khởi tạo Deadline (Preflight vs Feed Timeout):
- **Cấm tính thời gian Preflight vào ngân sách Feed:** `_deadline_monotonic` (1500s) chỉ được khởi tạo **sau khi** validation ADB và `prepare_tiktok_for_smoke` hoàn tất thành công, ngay trước lệnh gọi `feed_session_smoke(child_ctx)`.
- Nếu gán deadline ở đầu worker, toàn bộ thời gian khởi động app/verify profile (2-5 phút) sẽ bị trừ oan vào thời gian lướt, khiến các máy gặp popup/mạng chậm dễ bị ngắt phiên sớm (như máy 55 bị timeout ở video thứ 11).

### Công thức tính thời lượng phiên:
```
Total_Session_Seconds = Setup_Time (~150s) + (Total_Videos * Avg_Video_Seconds (~45s))
```

- **Khi cấu hình cũ (`15 - 30` video):**
  - Worst case (28 - 30 video): `150s + 30 * 50s = 1650s (~27.5 phút) > 1500s (25 phút)` -> Dẫn đến lỗi `run plan max_duration_seconds exceeded before capture swipe_XX_after attempt 1`.
  - Hàng loạt máy chậm bốc phải target cao (>25 video) đều bị ngắt phiên và giữ lock lỗi.

- **Khi cấu hình tối ưu (`10 - 14` video):**
  - Trường hợp trung bình (12 video): `150s + 12 * 45s = 690s (~11.5 phút)` (dư ~13.5 phút buffer).
  - Trường hợp chậm nhất kịch trần (14 video @ 50s): `150s + 14 * 50s = 850s (~14.2 phút)` (vẫn dư gần 11 phút an toàn trước trần 1500s, giải quyết triệt để tình trạng mạng chậm/lag retry).

---

## 2. Tiêu chuẩn phiên nuôi TikTok tự nhiên vs Tải máy 1 ngày

### A. Một phiên đơn lẻ (Single Session):
- Hành vi người dùng thật trên mobile: Thường mở app lướt 5 - 10 phút, tương đương **10 - 14 video**.
- Mức 25 - 30 video cho 1 lần vào app là quá dài đối với bot chạy tự động, dễ bị trễ nhịp và quá tải CPU/RAM của máy đời cũ.

### B. Tải phân bổ cả ngày (Daily Schedule):
- Lịch phân bổ theo Manifest (Phase 9/LANES):
  - **Block 1 (Sáng 06:00 - 10:30):** 3 phiên nhỏ (~10-15 phút/phiên), cách nhau 40-50 phút.
  - **Block 2 (Chiều 12:00 - 17:00):** 3 phiên nhỏ, cách nhau 40-55 phút.
  - **Block 3 (Tối 18:30 - 23:30):** 3 phiên nhỏ, cách nhau 45-55 phút.
  - **Đêm (00:00 - 06:00):** Nghỉ hoàn toàn.
- **Tổng tải:** 1 máy chạy 6 - 9 phiên/ngày (chia đều 2 nick), hoạt động thực tế 1.5 - 2.5h / 24h (~10% thời gian), xem 40 - 70 video/ngày -> Rất an toàn cho nick và máy.

---

## 3. Checklist khi điều chỉnh tham số Video / Timeout
1. Cập nhật hằng số trong `flows/multi_machine_feed_session.py`:
   - `FEED_SESSION_MIN_TOTAL_VIDEOS = 10`
   - `FEED_SESSION_MAX_TOTAL_VIDEOS = 14`
   - `DEFAULT_DEVICE_TIMEOUT_SECONDS = 1500.0` (25 phút)
2. Kiểm tra `python_runner/run_tiktok.py` và các wrapper cron (`scripts/run-feed-session.ps1`, `tiktok_runner.py`) xem có cờ override explicit (`--min-total-videos`, `--max-total-videos`) hay không.
3. Cập nhật toàn bộ unit tests liên quan trong `python_runner/tests/test_multi_machine_feed_session.py` và `test_feed_swipe_smoke.py`.
4. Audit Plan bằng `invoke_sol_audit.py` (`cx/gpt-5.6-sol` hoặc `ag/claude-opus-4-6-thinking`) để đảm bảo không vỡ validation manifest/picker.
5. **Hiểu rõ bản chất độ trễ 40-50s/video:**
   - Không phải do code dài/nhiều rule (duyệt cây XML trong RAM tốn < 0.005s).
   - Tốn thời gian do phần cứng Galaxy S7 cũ xử lý I/O: dump UI XML qua ATX (2-4s), UI render/settle (2-3s), buffering mạng proxy (2-5s), xử lý thoát overlay/story/ad (5-15s).
   - Tuyệt đối không giảm watch delay (giữ 3-7s) vì giảm 1-2s không giải quyết được vấn đề I/O mà làm tăng rủi ro bị TikTok bóp reach/flag bot. Giải pháp đúng luôn là kiểm soát trần video ở mức 10-14 video/phiên.
