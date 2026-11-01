# Upload Batch Alert: Post Verification Timeout & Proof Insufficient Triage

> Reference: Sự cố Farm Alert "11 máy lỗi script Upload" ca 2 phiên 2/2 ngày 2026-10-31 (Run: `row-0-140009`).

## 1. Cơ Chế Bắn Alert Lỗi Script Upload Hàng Loạt
Trong `feed_session_watchdog.py`:
```python
tot_up_err = sum(len(b.get("up_error", [])) + len(b.get("up_timeout", [])) for b in cluster_stats)
has_script_alert, alert_reasons = should_trigger_farm_alert(
    tot_fl_err, tot_up_err, feed_errors=tot_feed_err, threshold=DEFAULT_FARM_ALERT_THRESHOLD
)
```
- Ngưỡng kích hoạt: `DEFAULT_FARM_ALERT_THRESHOLD = 8` máy.
- **Đặc điểm cạm bẫy:** Watchdog cộng dồn cả `up_error` (lỗi script/xác minh) lẫn `up_timeout` (timeout quá giờ) vào `tot_up_err`, tạo tiêu đề chung `X máy lỗi script Upload`.
- Cần phân rã chính xác tỷ lệ giữa Timeout mạng vs Lỗi script thực tế trước khi kết luận lỗi logic.

## 2. Đường Dẫn Log & Artifacts Tra Cứu Nhanh O(1)
Tuyệt đối tuân thủ Invariant Farm Safety: CẤM dùng `grep -r`, `os.walk`, `glob(recursive=True)` quét mù đĩa.
Truy cập trực tiếp theo cấu trúc thư mục O(1):
- Kibe Local:
  `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/<run_id>/<timestamp>/machines/machine_<N>/<timestamp>/upload_result.json`
- Admin Remote:
  `D:/Taadaa/runtime/admin/live/<YYYY-MM-DD>/<run_id>/<timestamp>/machines/machine_<N>/<timestamp>/upload_result.json`
- Báo cáo chi tiết của TikTok Workflow Runner:
  `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<date>_<time>/report.json` và `execution.log`.
- Với WinRT OCR kiểm tra ảnh hiện trường: Bắt buộc dùng dấu gạch chéo ngược Windows (`\`) để tránh lỗi path PowerShell:
  `python D:/Taadaa/tools/run_winrt_ocr.py "D:\CodexRuntime\...\soft-reboot-video_pick-before.png"`

## 3. Phân Loại 3 Dạng Lỗi Điển Hình Khi Upload Batch

### A. Post Verification Timeout (`Post verification inconclusive/failed: TIMEOUT`)
- **Vị trí:** `scripts.tiktok_workflow.state_machine:14323` sau khi `post_verifier.verify_post(timeout_seconds=120)`.
- **Bản chất:** Sau khi bấm Đăng, giao diện TikTok không xuất hiện marker thành công hoặc điều hướng về feed trong 120s (thường gặp trên cụm Admin Remote qua proxy trễ).
- **Hành vi an toàn:** Script tự động kích hoạt `_recheck_ambiguous_post()` để mở lại Profile đếm video grid. Nếu việc load profile cũng bị timeout/unreliable, script dừng tại `MANUAL_REVIEW` để bảo vệ tài khoản, tránh đăng trùng.

### B. Generic Success Marker Rejected (`[POST_VERIFY_PROOF_INSUFFICIENT]`)
- **Vị trí:** `state_machine.py:14286-14300`.
- **Bản chất:** `post_verifier` nhận diện được text thông báo dạng "đã đăng" / "posted", nhưng:
  1. `_verify_current_post_surface()` (so khớp exact hashtag + target account + owner markers) trả về `False`.
  2. `_verify_profile_post_increment()` (tăng video tile trên profile) trả về `False` hoặc scan không đủ tin cậy (`viewports < 2`).
- **Kỷ luật:** Text chung chung "đã đăng" có thể là notification cũ hoặc của acc khác trong session. Script từ chối công nhận thành công nếu thiếu bằng chứng chính chủ, đưa về `MANUAL_REVIEW`.

### C. Video Picker Stalled (`Editor Next tapped but caption composer did not open`)
- **Vị trí:** `state_machine.py:11540`.
- **Bản chất:** Script đã tap chọn video trong Media Picker và bấm "Tiếp" (Next), nhưng TikTok bị đơ UI hoặc modal video editor không bung ra màn hình caption composer trong 60s.
- **Xử lý:** Script thử lại 3 lần kèm ATX reset. Nếu vẫn kẹt -> kích hoạt Soft-Reboot Recovery. Nếu proxy watcher không đạt ready sau reboot -> dừng an toàn, dọn Recent apps về Home.
