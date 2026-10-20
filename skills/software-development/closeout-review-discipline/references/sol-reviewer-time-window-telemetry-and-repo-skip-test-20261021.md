# Sol Reviewer Time-Window Telemetry, Boundary Testing & Repo Skip-Test Trap (2026-10-21)

## 1. Context & Bẫy `--skip-test` Trong Repo Mode
Khi chạy `closeout_gate.py` ở chế độ `--repo`, cờ `--skip-test` bị cấm hoàn toàn (`[Gate] FATAL: --skip-test is forbidden in repo mode! Closeout Gate requires verified test execution`).
- **Nguyên tắc:** Repo mode bắt buộc phải chạy bộ kiểm thử tự động (focused test do gate tự phát hiện hoặc test suite tương ứng). Cấm Coordinator dùng `--skip-test` để đốt cháy giai đoạn.
- **Khắc phục:** Luôn cung cấp hoặc để Gate phát hiện test suite phù hợp (ví dụ `pytest tests/test_<stem>.py`). Nếu repo có test tổng thể quá nặng (>120s timeout), phải chỉ định file test focused siêu nhẹ (<30s).

---

## 2. Rubric Chấm Điểm Sol Reviewer Đối Với Logic Khung Giờ (Time Windows)
Khi sửa đổi logic kiểm tra khung giờ an toàn (ví dụ trong các watchdog như `cron_night_tiktok_2fa_watchdog.py` hay `tiktok_rename_rolling_watchdog.py`), Sol Reviewer (OmniRoute :20129) trừ điểm nặng (chấm 70-75 REJECT) nếu phát hiện các lỗi sau:

### Các lỗi bị Sol Reviewer gắn cờ:
1. **Chồng lấn ranh giới (Overlapping Window Boundaries):**
   - Viết các câu lệnh `if` lồng nhau hoặc ghép nối rời rạc dẫn đến việc cùng một phút rơi vào nhiều điều kiện khác nhau (ví dụ: `05:05 <= m < 05:35` chồng lấn với `05:15 <= m < 09:30`).
2. **Thiếu khả năng quan sát (Lack of Observability / Telemetry):**
   - Khi hàm trả về `False` (bị chặn ngoài khung an toàn), log chỉ in chung chung: `Ngoài khung giờ an toàn: 05:20` mà không chỉ rõ **khung nào / lý do gì** đã kích hoạt chặn.
   - Reviewer coi đây là lỗi nghiêm trọng vì Farm Operator không thể biết watchdog bị chặn do ca nuôi, do dọn cache hay do đệm ca.
3. **Thiếu kiểm thử ranh giới cụ thể (Edge-case Boundary Coverage):**
   - Dù test suite có 29/29 pass, reviewer vẫn từ chối nếu không thấy test khẳng định riêng biệt cho từng mốc biên (ví dụ: phút 04, 05, 34, 35).

---

## 3. Pattern Chuẩn Hóa Kiến Trúc Vượt Gate (Grace / Approved >= 80–85)

### Pattern 1: Bảng Tra Cứu Cấu Hình Hằng Số Tập Trung
Thay vì viết một chuỗi `if (h == 5 and ...) or ...` dài dòng và dễ trùng lặp, gom toàn bộ các khoảng thời gian bị chặn vào một cấu trúc dữ liệu tường minh:
```python
ROLLING_BLOCK_WINDOWS = (
    ("dọn cache", (4, 0), (4, 30)),
    ("ca nuôi sáng", (5, 5), (9, 30)),
    ("đệm ca trưa", (11, 5), (11, 35)),
    ("ca nuôi trưa", (11, 45), (15, 30)),
    ("đệm ca chiều", (17, 5), (17, 35)),
    ("ca nuôi chiều", (17, 45), (21, 30)),
)
```

### Pattern 2: Helper Phân Loại & Telemetry Tường Minh
Tạo hàm helper trả về chuỗi nhãn ngữ nghĩa (hoặc `None` nếu an toàn):
```python
def rolling_block_reason(now_dt: datetime) -> str | None:
    hm = (now_dt.hour, now_dt.minute)
    for label, start, end in ROLLING_BLOCK_WINDOWS:
        if start <= hm < end:
            return label
    return None

def is_safe_rolling_window(now_dt: datetime) -> bool:
    return rolling_block_reason(now_dt) is None
```

### Pattern 3: Log Ghi Rõ Nhãn Khung Giờ
Tại entrypoint `main()`:
```python
if not is_safe_rolling_window(now) and not args.force and not args.dry_run:
    logger.info("Ngoài khung giờ an toàn (%s): %s", rolling_block_reason(now), now.strftime("%H:%M"))
    return 0
```

---

## 4. Kỷ Luật Điều Phối Khi Dính Reviewer Hand-Off (Strike 4)
Khi Gate in ra:
`[REVIEWER_HANDOFF_TRIGGERED: 4 consecutive rejections reached for scope_hash=... Coordinator/Worker/Sol Repair MUST STOP guessing/repairing and hand the keyboard to the Reviewer...]`

- **Cấm:** Không dùng `clarify` để hỏi user xin phép hay đùn việc.
- **Hành động bắt buộc:** Gọi ngay `dispatch_worker.py` (chạy Claude Haiku 5.5 CLI với role reviewer) truyền contract cụ thể yêu cầu:
  1. Hợp nhất logic ranh giới không chồng lấn.
  2. Thêm telemetry helper và log rõ nhãn chặn.
  3. Chạy lại test suite để bảo đảm xanh 100%.
- Sau khi worker hoàn tất, chạy lại `closeout_gate.py` để lấy Token HMAC phê duyệt (Approved/Grace).
