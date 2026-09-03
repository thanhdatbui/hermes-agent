---
name: farm-schedule-preflight-check
description: Kiểm tra máy rảnh an toàn trước khi chạy các batch reg / login / upload — tránh xung đột với lịch Cron nuôi acc (TikTok feed/follow).
---

# Farm Schedule Preflight Check

Dùng trước khi khởi chạy bất kỳ batch tác vụ nào (Reg TikTok, Hotmail, Add Mail, Upload video, Reconcile...) để tìm danh sách máy rảnh, không đụng vào lịch nuôi acc tự động.

## 1. Nguyên Tắc An Toàn & Thực Thi
- **Khoảng đệm an toàn:** Máy được chọn ưu tiên **rảnh trong suốt thời gian chạy + cách lịch nuôi acc kế tiếp tối thiểu 1 tiếng (60 phút)** khi chạy batch lớn thảnh thơi.
- **Cơ chế Lock-Aware tự bảo vệ của Cron nuôi acc:**
  * Runner nuôi acc (`hermes_cron_runner`) luôn kiểm tra `device-locks` trước khi spawn.
  * Nếu máy đang bị lock do tác vụ Reg/Fix đang chạy, Cron nuôi acc sẽ **tự động ghi nhận `SKIPPED_DEVICE_LOCKED` và chỉ bỏ qua DUY NHẤT 1 phiên (slot) nuôi đó**, tuyệt đối KHÔNG can thiệp, KHÔNG chạy đè và KHÔNG làm hủy toàn bộ cả ca nuôi lớn. Các phiên sau khi máy đã mở khóa sẽ tiếp tục chạy bình thường.
- **Quy ước khi User yêu cầu on-demand chạy reg/task ngay:**
  * Khi user yêu cầu "chọn N máy chạy reg" hoặc "chạy batch ngay", agent thực hiện khóa máy (`DEVICE_LOCK_ENABLED=1`) và khởi chạy ngay các máy có target hợp lệ.
  * Nếu chỉ chạy một subset N máy (không chạy hết toàn bộ target phát hiện), dùng `TIKTOK_REG_SKIP_STTS="<list STT bỏ qua>"` khi gọi `_run_all_targets.py`.
- **Quy tắc Dữ liệu Kho Mail & Tracking:**
  * `gmail_clean_v2.xlsx` là **KHO MAIL LIVE**: Mail sau khi reg TikTok thành công **KHÔNG ĐƯỢC XÓA** khỏi `gmail_clean_v2.xlsx`. Chỉ xóa khi mail die/bị gỡ thực sự.
  * `taikhoan_dat_v2_updated .xlsx` là **BẢNG TRACKING TIKTOK**: ID TikTok đăng ký thành công bắt buộc phải nằm cùng dòng với Email thực tế đã dùng để đăng ký.
- **Quy ước ngầm định khi User yêu cầu "máy rảnh chạy reg TikTok":**
  * Tự động kết hợp 3 điều kiện: (1) Máy rảnh lịch cron (cách ca nuôi >= 60p), (2) Máy có target mail hợp lệ chưa đăng ký trong inventory/source workbook (`_detect_clean.py`), và (3) Máy đã kết nối VPN proxy an toàn (`verify_live_ip=True` / `GET_IP result=200`). Tuyệt đối không chỉ lọc máy rảnh lịch thuần túy rồi liệt kê máy không có mail hoặc chưa có VPN.
- **Quy tắc Lock & Error screen:**
  * Khóa thiết bị (`DEVICE_LOCK_ENABLED=1` / `acquire_device_lock`) khi bắt đầu chạy batch / on-demand theo lệnh user ("lock lại khi làm nhé").
  * **Vòng đời Lock:** Duy trì lock xuyên suốt toàn bộ quá trình chạy. **CHỈ mở khóa khi máy hoàn thành SUCCESS (đã lưu tracking & dọn dẹp app về Home) HOẶC khi User trực tiếp ra lệnh mở khóa.**
  * Script chạy batch / on-demand 2FA / reg: Nếu FAIL/Lỗi hoặc chờ OTP/Captcha/Anchor thì giữ nguyên hiện trường màn hình lỗi, chụp ảnh screencap gửi user, giữ nguyên lock, không tự ý đóng app hay unlock. Preflight ca nuôi 06:00 sẽ tự dọn trước khi swipe.
- **Lệnh thực thi trực tiếp (Không dừng lại hỏi / Không dừng ở bước mua mail):** Khi user yêu cầu "chọn N máy chạy <task>" hoặc "mua N hotmail reg các máy...", agent BẮT BUỘC thực hiện luồng khép kín liên tục không ngắt quãng:
  1. Mua tài khoản (BoxTaiKhoan API gói 60 OAuth2) & xác thực OAuth2 token.
  2. Nạp tài khoản vào `gmail_clean_v2.xlsx`.
  3. Khởi chạy NGAY batch reg `_run_all_targets.py` (`DEVICE_LOCK_ENABLED=1`, background + monitor), tuyệt đối không dừng lại ở bước mua/nạp để báo cáo nửa chừng khiến user phải giục.
  4. Đồng bộ CSDL ngay sau khi batch kết thúc (`scripts/apply_deferred_tracking_results.py`).
- **Không áp đặt giới hạn cứng dải máy:** Việc giới hạn số lượng máy ở bất kỳ dải nào (như 75-80) chỉ thực hiện khi user yêu cầu cụ thể trong phiên, không tự động đặt rule cứng.

## 2. Phân Bổ Khung Giờ Máy Rảnh & Chiến Lược Vận Hành Farm (80 Máy)
- **Lịch nuôi acc (3 Ca/ngày):**
  - Ca 1: `06:00` → `09:30` - `10:00`
  - Ca 2: `12:30` → `16:00` - `16:30`
  - Ca 3: `19:00` → `22:30` - `23:00`
- **Chuỗi đêm tự động (Reg Gmail ➔ Reg TikTok):** Chạy lúc `01:00` sáng qua Hermes Cron `night-chain-reg-pipeline`. Luồng chạy tuần tự (blocking): hoàn tất 100% Reg Gmail $\rightarrow$ nghỉ 10s flush Excel $\rightarrow$ khởi động Reg TikTok với giới hạn an toàn `--max-targets=30` và `--max-workers=6` (6 worker cuốn chiếu, giãn cách 2–8s, xong trước `02:00`).
- **Giới hạn dung lượng máy (Max 6 accs/máy):** Mỗi máy tối đa 6 tài khoản TikTok. Khi máy đã có $\ge 6$ TikTok ID trong tracking workbook $\rightarrow$ loại vĩnh viễn khỏi detector reg, không cấp thêm mail. Tuyệt đối không reg dư rồi mang tài khoản mới sang máy khác logout/login (tránh checkpoint thiết bị đột ngột).
- **Khung giờ rảnh cho tác vụ on-demand/tay:**
  - **Khung Đêm - Sáng sớm (`23:30` → `05:30`):** Toàn bộ 80 máy rảnh, mạng & proxy ổn định. Runner nuôi acc silent từ `02:00` đến `05:59`.
  - **Khung Trưa (`10:00` → `11:45`):** Thích hợp chạy on-demand (Login kiểm kê, Reg TikTok bù/fix tay).
  - **Khung Chiều (`16:30` → `18:15`):** Thích hợp chạy on-demand lẻ/canh tay.

## 2. Lệnh / Script Check Nhanh Máy Rảnh
Chạy đoạn Python sau từ terminal để lấy danh sách máy rảnh theo thời gian thực:

```python
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Đảm bảo import được module hermes_cron từ runner
sys.path.insert(0, r"D:\Taadaa\tiktok-luot nuoi acc")
from python_runner.hermes_cron.models import StatePaths, parse_hcm_timestamp
from python_runner.hermes_cron.manifest import load_active
from python_runner.hermes_cron.source_config import SourceConfig

root = Path(r"D:\Taadaa\runtime\kibe\cron-state")
source_file = Path(r"D:\Taadaa\runtime\kibe\cron-source\hermes_cron_source_config.json")
source = SourceConfig.from_json(source_file)

now_dt = datetime.now().astimezone(parse_hcm_timestamp("2026-08-18T00:00:00+07:00").tzinfo)
day_str = now_dt.strftime("%Y-%m-%d")
active = load_active(StatePaths(root, root), day_str, source)

all_farm_machines = set(range(1, 81)) # kibe 1-80
busy_window_end = now_dt + timedelta(hours=1.0) # đệm 1 tiếng

busy_machines = set()
upcoming_slots = {}
for entry in active.payload.get("entries", []):
    m = entry["machine"]
    s_start = parse_hcm_timestamp(entry["slot_time"])
    s_end = parse_hcm_timestamp(entry["slot_end"])
    if s_start >= now_dt:
        if m not in upcoming_slots or s_start < upcoming_slots[m]:
            upcoming_slots[m] = s_start
    if (s_start <= now_dt < s_end) or (now_dt <= s_start < busy_window_end):
        busy_machines.add(m)

idle_machines = sorted(all_farm_machines - busy_machines)
print(f"Máy rảnh an toàn (cách ca nuôi >= 60p): {idle_machines}")
```

## 3. Lock Transient & Mapping Machine↔Serial (live 2026-08-24)

- **Lock file CÓ THỂ TRANSIENT**: thấy `machine_XX.lock.json` ở lần check này rồi biến mất vài phút sau (case máy 33: lock 22:52 → mất ~22:55). Quy tắc an toàn khi chọn máy cho task giới hạn: máy TỪNG xuất hiện lock trong cửa sổ chọn → coi là đang có hoạt động quanh nó, TRÁNH; chỉ chọn máy 0 lần thấy lock suốt cả phiên chọn + re-check ngay trước preflight.
- **Mapping nhanh machine→serial**: đọc thẳng `D:\Taadaa\runtime\kibe\cron-source\hermes_cron_source_config.json` — `feed_source.accounts[]` mỗi entry có `{account_id, machine, serial}`. Lưu ý: một số máy KHÔNG có entry feed_source (vd 75–80) → NO-SERIAL, loại khỏi ứng viên cần serial cụ thể. Nguồn thay thế đầy đủ hơn: `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (cột A=Máy, B=device ID) — có cả máy không nằm trong feed_source (vd máy 76). Đừng đoán mapping từ tên máy/hostname — luôn đi qua 1 trong 2 nguồn này.

### 3a. Active-cohort takeover gate (bổ sung từ live review 2026-08-31)

Khi user yêu cầu takeover đúng một máy đang nằm trong phiên feed đa máy, **không suy ra quyền takeover từ PID/run ID cũ hoặc artifact FINAL_BLOCKED trước đó**. Trước mọi side effect (ghi target, sửa nguồn mail, acquire lock, launch runner):

1. Đọc đồng thời cả hai alias lock của máy/serial; ghi hash, status, owner PID/host/project/run ID và `owner_active`.
2. Re-verify process identity/command line ngay tại thời điểm hành động. Nếu PID cũ đã chết nhưng lock đã được một owner mới nhận, owner mới là trạng thái có thẩm quyền.
3. Kiểm tra code path chính thức xem có **per-machine exclusion/relinquish** khỏi active cohort hay chỉ có guarded takeover cho lock inactive. Cờ `--full-scope-takeover` không tự chứng minh được takeover từng máy.
4. Nếu không có cơ chế official tách riêng máy khỏi active cohort, dừng fail-closed trước side effect với `FINAL_BLOCKED` và mã `DEVICE_LOCK_CONFLICT_ACTIVE_OWNER`; giữ nguyên lock active và không chạy runner thay thế.
5. Cấm dùng kill/taskkill parent, xóa/ghi đè lock, pause cả cron, hoặc chạy ad-hoc để “làm máy rảnh”. Artifact kết quả phải ghi `runner_started=false`, takeover chưa thực hiện, lock được preserve, và bằng chứng parent/current owner.

Reference: `references/active-cohort-takeover.md`.

## 4. Đọc lịch theo ROW nick (2026-08-25)

- Manifest cron mỗi entry có field `account_row` — khi user hỏi/nêu điều kiện kiểu "hôm nay cron chạy row X", PHẢI group theo `account_row` rồi báo số máy từng row, đừng trả lời tổng quát. Lịch xen kẽ theo NGÀY (vd 21/08=row1+3, 22/08=row2+4, 23/08=row1+3) — row hôm nay ≠ row hôm qua.
- Slot của 1 máy có thể trải dài nhiều khung trong ngày; check "đang bận" phải xét TẤT CẢ slot hôm nay + mai (load_active cho 2 ngày), không chỉ block kế tiếp: máy có thể vừa nhả ca này nhưng còn ca khác sau <60'.
- Gate script mẫu (ready/busy/near<60'/offline/locked, JSON out): `C:\Users\Kibe\AppData\Local\hermes\scripts\f2a_row1_gate_check.py`.
