# Post-Registration Feed Warmup (Lướt Nuôi Ngay Sau Khi Reg TikTok)

## 1. Bối cảnh & Mục đích
Khi một tài khoản TikTok vừa đăng ký thành công trên thiết bị:
- **Hành vi người dùng thật**: Người dùng thường ở lại ứng dụng lướt xem một số video (dwell time từ 3–10 phút), tạo lịch sử xem ban đầu.
- **Rủi ro của bot pattern**: Nếu vừa reg xong là thực hiện `_post_reg_cleanup` (`am force-stop` và `KEYCODE_HOME` ngay với dwell time = 0s), hệ thống Risk Control & Telemetry của TikTok dễ dàng nhận diện đây là script reg tự động, làm tăng tỷ lệ checkpoint hoặc shadowban/gắn nhãn nick rác.
- **Giải pháp**: Cho chính tài khoản vừa đăng ký trên thiết bị lướt feed ngay tại chỗ (Warmup session) trước khi đóng app và nhả máy.

## 2. Các Ràng Buộc & Nguyên Tắc An Toàn Bắt Buộc

### A. Dữ liệu tài khoản phải an toàn tuyệt đối (Data-First)
- BẮT BUỘC ghi nhận và lưu trữ toàn bộ dữ liệu đăng ký (ID, mật khẩu, email, deferred tracking JSON hoặc workbook) **TRƯỚC** khi gọi flow lướt feed.
- Vị trí can thiệp trong `social_reg_v1.py`: trong hàm `ensure_profile_completed_and_track()`, ngay sau `write_deferred_tracking_result` hoặc `upsert_tracking_account`, và TRƯỚC KHI gọi `_post_reg_cleanup(device_id, stt=stt)`.
- Bọc toàn bộ lời gọi feed bằng `try...except Exception`: nếu feed fail hoặc timeout, chỉ log warning và vẫn tiếp tục dọn dẹp để không làm gián đoạn kết quả reg đã thành công.

### B. Thời lượng Warmup ngắn (Light Warmup)
- **Không bê nguyên phiên nuôi đầy đủ (30–60 phút)** của repo `tiktok-luot nuoi acc`.
- **Thời lượng chuẩn**: 3 – 5 phút, lướt 5 – 8 video ngẫu nhiên.
- Lý do: Batch reg chạy nhiều máy song song. Nếu mỗi máy lướt quá lâu sẽ giữ `device_lock`, gây nghẽn tiến độ farm và có nguy cơ đâm xuyên vào khoảng đệm an toàn của Ca 1 nuôi acc.

### C. TUYỆT ĐỐI CẤM Follow Hook & Like/Comment
- Repo `tiktok-luot nuoi acc` có hook gọi `tiktok-follow` để follow chéo.
- Tài khoản mới tinh có 0 video, độ trust bằng 0. Nếu vừa tạo xong đã đi follow chéo sẽ bị TikTok kích hoạt Action Block hoặc bắt xác minh danh tính ngay lập tức.
- Phiên warmup sau reg CHỈ lướt tab For You (Đề xuất) thuần túy, không like (`allow_like = False`), không comment, không follow.

### D. Chu trình kết thúc
- Sau khi hoàn thành N video lướt feed, script mới thực hiện `_post_reg_cleanup(device_id, stt=stt)`:
  1. `am force-stop com.ss.android.ugc.trill`
  2. `input keyevent 3` (KEYCODE_HOME)
  3. Nhả `device_lock` máy an toàn.

## 3. Cạm bẫy kỹ thuật khi gọi runner từ `tiktok-luot nuoi acc` (Verified 2026-09-06)

### Cạm bẫy 1: Cấm cờ `--full-scope-takeover` cho tác vụ đơn máy
- Script `python_runner/run_tiktok.py` kiểm tra:
  ```python
  if args.full_scope_takeover and args.mode != "multi-machine-feed-session":
      print("CONFIG_ERROR: --full-scope-takeover is only supported for multi-machine-feed-session", file=sys.stderr)
      return ExitStatus.CONFIG_ERROR.code
  ```
- Nếu truyền `--full-scope-takeover` trong tác vụ đơn máy/sau reg, script lập tức dừng với exit code 3 (`CONFIG_ERROR`).
- **Quy tắc:** Tuyệt đối KHÔNG truyền cờ `--full-scope-takeover` khi gọi feed đơn lẻ sau reg.

### Cạm bẫy 2: Lựa chọn Mode & Giới hạn `--max-swipes`
- `--mode feed-swipe-smoke`: Bị hard-cap tối đa 3 swipes (`1 <= --max-swipes <= 3`).
- `--mode feed-session-smoke`: Cho phép cấu hình từ 1 đến 15 video (`1 <= --max-swipes <= 15`), phù hợp với mức cấu hình 5–8 video làm ấm nick mới.
- Khi dùng `feed-session-smoke`, bắt buộc thêm `--no-verify-profile` vì tài khoản mới đăng ký đang sẵn ở màn hình và chưa có cấu hình account slots file.

### Cạm bẫy 3: Xung đột PYTHONPATH khi gọi subprocess venv khác
- Khi chạy script từ Hermes hoặc môi trường cha có biến môi trường `PYTHONPATH`, Python interpreter của `D:/Taadaa/python-envs/automation` sẽ nạp nhầm `site-packages` của môi trường cha, dẫn đến lỗi:
  ```text
  ImportError: cannot import name '_imaging' from 'PIL'
  ```
- **Khắc phục:** Luôn xóa `PYTHONPATH` khỏi môi trường con trước khi spawn subprocess:
  ```python
  sub_env = os.environ.copy()
  sub_env.pop("PYTHONPATH", None)
  ```

## 4. Mẫu lệnh CLI thực thi chuẩn xác
```bash
D:/Taadaa/python-envs/automation/Scripts/python.exe \
  "D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py" \
  --device <serial> \
  --account <handle> \
  --machine <stt> \
  --mode feed-session-smoke \
  --max-swipes 5 \
  --allow-feed-swipe \
  --allow-navigation-only \
  --allow-benign-popup-dismiss \
  --no-verify-profile
```
