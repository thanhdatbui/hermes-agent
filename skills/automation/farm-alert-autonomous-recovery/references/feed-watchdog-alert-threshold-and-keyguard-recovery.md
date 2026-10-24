# Feed Session Mass Failure & Farm Alert Mechanization

> Case Reference: Case 82 (24/10/2026) - Khắc phục lỗi mở/focus TikTok do bẫy Keyguard SystemUI, vòng lặp Auto-healing đa tầng và cơ chế kích hoạt Farm Alert khi lỗi nuôi feed hàng loạt.

## 1. Hiện Tượng Sự Cố & Bẫy "Báo Cáo Đối Phó"
Trong các ca nuôi acc hàng loạt (Ca 1 Phiên 1/2), 20 máy báo lỗi (8 Kibe, 12 Admin), trong đó 10 máy dính `Lỗi mở/focus App TikTok` (`prepare-tiktok failed to focus TikTok after launch`), cá biệt M69 kẹt 56 phút.
- **Bẫy điều phối (Bị cấm):** Chỉ đọc `inspect_machine.py`, phân loại máy rớt cáp hay sleep rồi báo cáo tình trạng phần cứng ("đối phó"), bảo "sẵn sàng vào phiên sau" mà không truy tìm nguyên nhân gốc trong code khiến các ca sau tiếp tục rớt lặp lại.
- **Quy tắc bắt buộc:** Khi phát hiện lỗi hàng loạt, BẮT BUỘC đọc log phiên gần nhất (`runtime/<cluster>/live/<date>/row-<N>/log.jsonl`), bóc tách traceback code và thực hiện bản vá logic O(1).

---

## 2. Nguyên Nhân Cốt Lõi & Giải Pháp Kỹ Thuật

### A. Bẫy Keyguard SystemUI (`flows/device_prepare.py`)
- **Nguyên nhân:** Hàm `recover_systemui_occlusion` khi phát hiện `com.android.systemui` chỉ gửi `am broadcast CLOSE_SYSTEM_DIALOGS` và `input keyevent 4` (phím BACK). Trên Samsung S7 Android 8, phím BACK hoàn toàn không có tác dụng dismiss Keyguard khi máy ở màn hình khóa, khiến máy tiếp tục bị occlude bởi SystemUI và dumpsys bị nghẽn (45-60s/lần).
- **Giải pháp:** 
  - Gửi ngay `input keyevent 82` (KEYCODE_MENU) để mở khóa non-secure Keyguard.
  - Trang bị nhịp fallback vuốt màn hình `input swipe 540 1400 540 500 300` nếu keyevent 82 chưa qua.

### B. Bẫy Timeout 1 Lần Trong Auto-Healing (`flows/device_prepare.py`)
- **Nguyên nhân:** Khi TikTok khởi động lần 1 thất bại, nhánh auto-healing gọi `am start` rồi chỉ ngủ 2.0s (`time.sleep(2.0)`) và đọc focus duy nhất 1 lần (`read_focus()`). Trên Galaxy S7 tải cao khi 80 máy chạy đồng thời, TikTok cold boot thường mất 3-8 giây để SplashActivity chiếm focus. Kiểm tra 1 lần sau 2s khiến hệ thống phán đoán sai và báo fail sớm.
- **Giải pháp:**
  - Mở vòng lặp thăm dò 4 nhịp x 1.0s.
  - Ở nhịp 2 nếu chưa focus, chủ động kích hoạt thẳng SplashActivity tường minh:
    ```bash
    am start -n <package>/com.ss.android.ugc.aweme.splash.SplashActivity
    ```
  - Thoát vòng lặp ngay khi TikTok chiếm foreground.

### C. Lỗ Hổng Cơ Chế Farm Alert (`watchdog/alerts.py` & `scripts/feed_session_watchdog.py`)
- **Nguyên nhân:** Hàm `should_trigger_farm_alert` nguyên bản chỉ kiểm tra lỗi Follow (`fl_errors`) và Upload (`up_errors`), hoàn toàn bỏ quên khâu Nuôi Feed (`feed_errors`). Khi 20 máy lỗi Feed/ADB/Focus, watchdog vẫn chỉ gửi header chúc mừng `📊 [TIKTOK NUÔI ACC] Ca 1 hoàn tất` và không bắn alert sang nhóm khẩn cấp.
- **Giải pháp:**
  - Bổ sung tham số `feed_errors` vào `should_trigger_farm_alert`: nếu `feed_errors >= threshold` (mặc định 8 máy ~ 10% farm), kích hoạt alert: `"{feed_errors} máy lỗi nuôi Feed/ADB/Focus"`.
  - Trong `feed_session_watchdog.py`, tổng hợp `tot_feed_err = sum(len(b.get("fail", [])) for b in cluster_stats)`.
  - Trong `dispatch_split_reports`, nếu phát hiện lỗi Feed hàng loạt (`tot_feed >= 8` hoặc có cờ `[FARM ALERT]`), tự động bắn thêm một bản tin cảnh báo khẩn cấp sang đúng nhóm **Telegram Farm Alert** (`-5373649734`).

---

## 3. Cập Nhật Routing Trong Canary Runner (`tools/canary_runner.py`)
Để chạy được Canary tự động cho repo `tiktok-luot nuoi acc`:
1. **Routing runner:** Đăng ký command cho `tiktok-luot nuoi acc` / `tiktok-feed` gọi `python_runner/run_tiktok.py --mode multi-machine-feed-session --machines <m> --account-row-index <row> --recovery-test-swipes 2 --account-workbook <wb_path> --device-map-workbook <devmap_path> ...`.
2. **Xử lý Cooldown Directory:** Bọc hàm `_machines_in_cooldown` kiểm tra `state_dir.is_dir()`, trả về `set()` an toàn nếu repo không dùng cơ chế follow cooldown, tránh crash `ValueError`.
3. **Parse kết quả Feed:** Kiểm tra chuỗi `"Status: success"` và tự động bốc file `screen.png` từ thư mục artifacts sang `out_screencap` để phục vụ hậu kiểm WinRT OCR và Gate 6 Vision.

---

## 4. Bộ Tiêu Chuẩn Kiểm Thử Hồi Quy (Protection Regression Checklist)
Trước khi báo hoàn thành (DONE) bất kỳ task fix automation nào:
1. `pytest D:/Taadaa/tools/guardgate` (100% mechanical rules & regression vectors pass).
2. `pytest <repo>/tests/test_<module>.py` (unit test của module sửa đổi pass 100%).
3. `python D:/Taadaa/tools/canary_runner.py --repo <repo> --machine <id>` (chạy thật trên thiết bị rảnh, pass exit 0).
4. `python D:/Taadaa/tools/done_gate.py --task-type automation --repo "<repo_path>"` (xác thực receipt hợp lệ).
5. Gate 6 Vision: Soi mắt ảnh chụp nghiệm thu xác nhận đúng UI thật, không lỗi đen/popup trước khi gửi thẻ `MEDIA:<path>`.
