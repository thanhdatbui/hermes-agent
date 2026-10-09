# SWITCHER_OPEN_FAILED & Process Duration Triage in TikTok Add 2FA

## 1. Cơ chế phát sinh lỗi `SWITCHER_OPEN_FAILED`

### Nguồn gốc ngoại lệ trong `automation-core`
Trong `automation_core/tiktok/account_switcher.py`, hàm `open_switcher`:
```python
        except Exception as exc:
            last = exc
            if attempt + 1 < max_attempts and isinstance(exc, AccountSwitcherError):
                try:
                    recover_navigation_failure(adapter, exc)
                except AccountSwitcherError:
                    pass
    if isinstance(last, AccountSwitcherError):
        raise last
    raise AccountSwitcherError("SWITCHER_OPEN_FAILED", "switcher could not be opened") from last
```

### Tại sao xảy ra trên máy thật?
1. **Bẫy Header 1 tài khoản duy nhất (Single-Account Profile Header Trap - Phát hiện 07/09/2026 trên Máy 1)**:
   - Khi thiết bị chỉ mới đăng nhập **độc nhất 1 tài khoản** (ví dụ `@tranngan767`), giao diện trang Profile của TikTok **KHÔNG HỀ CÓ** nút mũi tên xổ xuống (dropdown arrow) ở đỉnh màn hình.
   - Thanh header trên cùng chỉ gồm: Nút "Thêm người" bên trái `[24,96][132,204]` và "Menu hồ sơ ☰" bên phải `[948,96][1056,204]`.
   - Node username (ví dụ `@tranngan767` bounds `[400,594][679,639]`) dù có thuộc tính `clickable="true"`, nhưng khi tap vào thì TikTok **KHÔNG HỀ mở bất kỳ Bottom Sheet nào** (do hệ thống TikTok nhận biết chỉ có 1 nick nên không hỗ trợ chuyển nhanh tại header).
   - `find_switcher_anchor` tìm trúng node này, tap vào nhưng `is_switcher_open` luôn trả về False $\rightarrow$ Thử 3 lần đều hỏng và văng `SWITCHER_OPEN_FAILED`.
   - **Đường mở Switcher bắt buộc khi máy chỉ có 1 nick**:
     * Profile $\rightarrow$ Menu hồ sơ ☰ `[948,96][1056,204]` $\rightarrow$ Cài đặt và quyền riêng tư (`Settings and privacy`).
     * Cuộn xuống đáy cùng $\rightarrow$ Chọn **"Chuyển đổi tài khoản"** (`Switch account`) hoặc **"Thêm tài khoản"** (`Add account`).
     * Khi đã đăng nhập từ 2 nick trở lên, TikTok mới kích hoạt tính năng dropdown switcher tại header Profile.
2. **Tài khoản mục tiêu chưa có trên máy**:
   - Runner 2FA đọc danh sách từ workbook (ví dụ dòng 5: `ginnyhanstei80`), giả định tài khoản đã được đăng nhập từ trước.
   - Nếu nick chưa từng đăng nhập vào TikTok trên thiết bị, hoặc tài khoản bị logout/văng sau đợt dọn dẹp, script vào Profile không thấy tên nick khớp, cố gắng mở Account Switcher để tìm.
3. **Kẹt UI không mở được Bottom Sheet**:
   - Khi ở màn hình Profile của TikTok, script gọi `prepare_switcher_anchor` (swipe nhẹ từ 1248 lên 806) để đưa sticky header `id/pcq` hoặc `id/pmi` lên giữa màn hình.
   - Sau đó tap vào tên để bung sheet "Chuyển đổi tài khoản".
   - Nếu sau khi tap, `is_switcher_open(opened)` không xác nhận được marker sheet (do TikTok không nhận tap, UI bị đơ, hoặc popup đè), `open_switcher` ném `SWITCHER_NOT_CONFIRMED`.
   - Trong `account_preflight.py`, nếu `opened_here` là False hoặc ngoại lệ không phải `AccountSwitcherError`, lỗi được bọc thành mã terminal `SWITCHER_OPEN_FAILED`.

---

## 2. Phân định Thời gian Thực thi (Process Runtime vs User Perception)

### Hiện tượng: User thắc mắc "Treo 4 tiếng xong báo fail"
- **Thực tế kỹ thuật**:
  - Tiến trình runner `python_runner/run_batch_live_2fa.py` có cơ chế bounded attempts nghiêm ngặt:
    ```python
    for attempt in range(1, 4):
        # mỗi attempt chạy subprocess run_capture_phase_b.py
        if same_reason_retries >= 2 or attempt == 3:
            return replace(base, status="failed", reason=reason, attempts=attempt)
    ```
  - Thời gian chạy thực tế của 1 target failed qua 3 attempts chỉ kéo dài **~7 đến 10 phút** (khoảng 400–600s), sau đó process tự thoát (`exit code 4`).
- **Nguyên nhân gây hiểu lầm "treo 4 tiếng"**:
  - Do chuỗi batch được kích hoạt từ ca sáng (ví dụ ~08:11) qua các subagent điều tra, chờ đợi hàng đợi thiết bị hoặc delay trong cơ chế thông báo nền của nền tảng tin nhắn (Telegram), kết quả thoát của process con chỉ được bàn giao về chat vào giữa trưa (~12:46).
- **Quy tắc phản hồi khi user nghi ngờ treo**:
  - Trích xuất ngay timestamp thực tế bắt đầu và kết thúc từ `state.db` hoặc process log.
  - Báo cáo rõ ràng: *"Tiến trình thực tế chỉ chạy mất X phút Y giây với 3 lượt retry rồi thoát an toàn, không bị deadlock loop."*

---

## 3. Quy trình Xử lý Hiện trường khi gặp `SWITCHER_OPEN_FAILED`

1. **Bước 1 — Kiểm tra màn hình hiện tại (O(1))**:
   - Chụp ảnh màn hình: `adb -s <serial> exec-out screencap -p > D:/Taadaa/reports/mN_current.png`.
   - Đọc nhanh `mCurrentFocus`: `adb -s <serial> shell dumpsys window windows | grep -i mCurrentFocus`.
   - Xác định TikTok đang ở Feed, Profile, hay bị văng ra Launcher.

2. **Bước 2 — Kiểm tra danh sách tài khoản trong Switcher**:
   - Nếu TikTok đang mở, tap nút Hồ sơ (bounds `[864,1794][1080,1920]`).
   - Mở switcher thủ công bằng cách tap header hoặc gọi hàm kiểm tra inventory.
   - Đối chiếu xem nick mục tiêu (cột C của dòng Excel tương ứng) đã có mặt trong danh sách chuyển đổi tài khoản hay chưa:
     * **Chưa có nick**: Bàn giao luồng Login (`tiktok-log-in`) để nạp nick vào máy trước.
     * **Đã có nick nhưng không mở được**: Kiểm tra xem máy có bị vướng popup hệ thống / widget che khuất, hoặc kiểm tra tọa độ swipe của `prepare_switcher_anchor`.
