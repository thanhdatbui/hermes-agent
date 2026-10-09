# Gating Follow Hook Nới Lỏng: Tối Thiểu 3 Swipes Hoặc Kế Thừa Session Trong Ca (2026-09-05)

## 1. Bối cảnh & Bản chất nghiệp vụ
- **Chống Cold Follow:** Mở TikTok lên nhảy vào tìm kiếm để follow ngay là bot pattern 100%, TikTok sẽ silent rollback (nhả follow sau 3-5 phút) hoặc bóp reach/rate-limit. Bắt buộc phải có telemetry lướt feed (thời gian xem video, thao tác cuộn) để tạo session ấm.
- **Vấn đề trước đây:** Chỉ cho phép gọi follow hook khi feed session `final_status in {"success", "degraded"}` hoặc fail do chạm trần swipe (`feed_swipe_limit_reached`). Nếu nick đã lướt được 3-7 video nhưng ở cuối phiên gặp popup vặt (ví dụ khảo sát, thông báo cập nhật, timeout cuộn), phiên feed bị đánh dấu `failed` và follow hook bị hủy bỏ oan toàn bộ, gây lãng phí tài nguyên và không đạt quota follow.
- **Giải pháp nới lỏng:** Cho phép chạy follow hook khi thỏa mãn **BẤT KỲ ĐIỀU KIỆN NÀO** trong 2 phương án dưới đây.

---

## 2. Hai phương án kích hoạt Follow Hook

### Phương án 1: Warm-up tối thiểu (≥ 3 swipes trong phiên hiện tại)
- Kiểm tra `total_swipes_completed >= 3` từ `child_result` (qua helper `_extract_completed_swipes`).
- Kể cả khi phiên kết thúc với `final_status == "failed"` hoặc `stop_reason` là lỗi UI/timeout giữa chừng (như kẹt popup vặt, hết giờ vuốt), nếu đã lướt $\ge 3$ video thì session đã đủ telemetry ấm để chuyển tiếp sang follow hook.

### Phương án 2: Kế thừa Session Trust trong Ca (Shift Session Trust)
- Áp dụng khi phiên hiện tại vuốt $< 3$ video hoặc gặp lỗi sớm: Helper `_has_prior_successful_feed_session_in_shift` kiểm tra xem trong cùng ngày hôm nay (`YYYY-MM-DD`), trong cùng ca của row, nick/máy này đã có ít nhất 1 phiên lướt đạt `final_status == "success"` hay chưa.
- **Phân bổ ca chuẩn của Farm:**
  - **Ca 1:** Row 1, Row 2 (thường chạy khung sáng)
  - **Ca 2:** Row 3, Row 4 (thường chạy khung trưa/chiều)
  - **Ca 3:** Row 5, Row 6 (thường chạy khung tối)
- **Thư mục tra cứu:** `D:/Taadaa/runtime/kibe/live/{today}/row-{row}-*`. Tìm các file `summary.txt` hoặc `run_manifest.json` của `machine_{machine}` có `final_status == "success"`, loại trừ thư mục run hiện tại (`child_ctx.artifacts.run_dir`).
- Nếu phiên trước trong ca đã lướt thành công trọn vẹn, thiết bị và tài khoản đã có session trust trong ca, cho phép tiếp tục chạy follow hook.

---

## 3. Chốt chặn an toàn Fail-Closed tối thượng (Không bao giờ bypass)

1. **Lỗi tài khoản nặng (`_SENSITIVE_ACCOUNT_WORDS`):**
   - Danh sách: `checkpoint`, `banned`, `suspended`, `suspend`, `logged_out`, `logout`, `captcha`, `login`, `manual_challenge`, `otp`, `2fa`, `security_check`, `password_prompt`, `account_locked`, `account_blocked`, `account_mismatch`, `profile_mismatch`, `wrong_account`, `unauthorized`.
   - Nếu xuất hiện bất kỳ từ khóa nào trong `combined_status_tokens`: **BẮT BUỘC skip ngay lập tức** với `sensitive-skip-*`, tuyệt đối không chạy follow hook.
2. **Video Gate $\ge 5$:** Nick $< 5$ video đăng trên TikTok luôn skip với `under-5-videos-follow-disabled`.
3. **Warmup Phase Row 3–6:** Row 3..6 luôn skip với `tik{row}-warmup-feed-only`.
4. **Daily Release Cooldown:** Nick đang trong thời gian cooldown nhả follow (`follow_state_<M>_row_<index>.json`) luôn skip với `follow-released-daily-cooldown`.

---

## 4. Chuẩn hóa nhãn Preflight: `blocked-proxy-vpn`
- Farm đã chuyển đổi 100% sang Router Transparent Proxy (MikroTik + Sing-box), không còn sử dụng app ViChanger.
- Các nhãn legacy đã được chuẩn hóa trong `multi_machine_feed_session.py` và `multi_machine_smoke.py`:
  - `final_status`: `blocked-proxy-vpn` (thay cho `blocked-vichanger-vpn`).
  - `blocker_type`: `proxy-vpn` (thay cho `vichanger-vpn`).
  - Hàm verifier: `require_proxy_connected` (giữ alias `require_vichanger_connected` cho tương thích ngược).
  - Hard deadline: `proxy/vpn preflight`.

---

## 5. Pitfalls khi Viết Unit Test & Verification

1. **MagicMock Integer Coercion Pitfall (`int(MagicMock()) == 1`):**
   - Trong Python, `int(MagicMock())` mặc định trả về `1` do `MagicMock` cài sẵn `__int__`.
   - Khi viết helper `_extract_completed_swipes`, nếu truy cập thuộc tính trên một mock object chưa set (ví dụ `mock.total_swipes`), getattr trả về child mock và `int(val)` sẽ ra `1` thay vì fallback xuống details dict.
   - **Fix:** Luôn kiểm tra loại trừ mock types:
     ```python
     def _is_mock(obj: Any) -> bool:
         return type(obj).__name__ in ("MagicMock", "Mock", "NonCallableMagicMock") or hasattr(obj, "_mock_return_value")
     ```
2. **Follow State Cooldown Test Isolation:**
   - `_run_follow_hook` đọc file cooldown thực tế tại `D:/Taadaa/tiktok-follow/runs/state/follow_state_<M>_row_<index>.json`.
   - Nếu test dùng `machine=1`, runner sẽ đọc trúng state live của Máy 1 trên đĩa và tự skip với `follow-released-daily-cooldown`.
   - **Fix:** Trong unit test, cấu hình `ctx.config["follow_state_dir"] = temp_dir` hoặc dùng machine ID không có file live (ví dụ 99).
3. **Hard Deadline Timeout Mock Sequence:**
   - Trong `_run_follow_hook`, `_remaining_hard_timeout` được gọi tối đa 4 lần: (1) trước start, (2) trước subprocess, (3) sau queue lease, (4) sau run.
   - Khi mock side_effect, cần cung cấp đủ giá trị (ví dụ `[100.0, 100.0, 100.0, 0.0]`) để target chính xác nhịp deadline mong muốn.
4. **Environment & PYTHONPATH Isolation (Tránh lỗi Pillow _imaging):**
   - Trên Windows host, đường dẫn Python chuẩn của automation là: `D:/Taadaa/python-envs/automation/Scripts/python.exe`.
   - Khi chạy pytest từ shell agent, môi trường có thể kế thừa virtualenv của agent dẫn đến xung đột gói thư viện `PIL` (`cannot import name '_imaging' from 'PIL'`).
   - Bắt buộc set tường minh `PYTHONPATH="python_runner;D:/Taadaa/automation-core"` trước lệnh gọi pytest:
     ```bash
     PYTHONPATH="python_runner;D:/Taadaa/automation-core" D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest python_runner/tests/test_multi_machine_feed_session.py -k "test_follow_hook" -v
     ```

---

## 6. Công Thức Đối Soát Hiện Trường Live O(1) Cho Coordinator
Để kiểm tra nhanh trạng thái thực tế xem cơ chế warm-up và kế thừa ca có hoạt động hay không trên các đợt chạy live hôm nay mà không quét đĩa:
```python
import json
from pathlib import Path

live_dir = Path("D:/Taadaa/runtime/kibe/live/2026-09-05")
for r in sorted(live_dir.glob("row-1-*")):
    manifest_p = next(r.glob("*/run_manifest.json"), None)
    if not manifest_p:
        continue
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    for s in manifest.get("multi_machine_summary", []):
        m, feed_st, swipes = s.get("machine"), s.get("final_status"), s.get("swipes_completed", 0)
        f_p = manifest_p.parent / f"machines/machine_{m}/{manifest_p.parent.name}/follow_result.json"
        if not f_p.exists() or feed_st == "success":
            continue
        f_data = json.loads(f_p.read_text(encoding="utf-8"))
        print(f"[{r.name}] M{m:02d}: feed={feed_st} swipes={swipes} -> follow={f_data.get('status')} cnt={f_data.get('followed_count')} reason={f_data.get('reason')[:30]}")
```
- **Bằng chứng điển hình (05/09/2026):**
  - `Máy 26` (run `row-1-093208`): Feed fail (`manual-needed`, swipes = 1) nhưng do phiên `row-1-081602` trước đó trong ca đạt `success` $\rightarrow$ Kế thừa trust, Follow Hook chạy thành công `status: OK, followed_count: 7`.
  - `Máy 24` & `Máy 76` (run `row-1-113039`): Feed fail (`manual-needed`) nhưng đã lướt 9 swipes ($\ge 3$) $\rightarrow$ Vượt cổng feed gating thành công, sau đó được lọc an toàn ở gate video / cooldown của riêng nick.

