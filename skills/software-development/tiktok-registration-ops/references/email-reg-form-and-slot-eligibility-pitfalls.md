# Pitfalls & Quy tắc: Form Transition, Slot Accounting & Pipeline Alerts (TikTok Reg)

Tài liệu đúc kết từ đợt fix 3 lỗi vận hành trong `D:\Taadaa\Tiktok_Reg`.

---

## 1. Header False-Positive trong `detect_after_continue()` (`social_reg_v1.py`)

### Triệu chứng
Sau khi điền email và ấn nút "Tiếp tục", script lập tức báo `form_still_visible`, bấm phím BACK thoát flow, và sau khi thử hết candidates thì ném ngoại lệ sai:
`RuntimeError: [07] Tat ca N email cua STT ... da co TK TikTok`

### Nguyên nhân gốc rễ
- Header của màn hình TikTok là "Nhập địa chỉ email" (hoặc "Enter email address").
- Nếu `form_hints` chứa từ khóa ngắn như `"nhap dia chi email"`, hàm `detect_after_continue` sẽ match ngay với header khi màn hình đang loading/chuyển tiếp.
- `flat_xml` vẫn còn header dẫn đến việc nhận định nhầm là form chưa gửi hoặc bị kẹt.

### Quy tắc xử lý
1. `form_hints` **tuyệt đối không** chứa text trùng tiêu đề header.
2. Chỉ giữ các hint lỗi validation thực tế xuất hiện dưới ô input:
   - `"nhap dia chi email hop le"`, `"hop le"`, `"khong hop le"`, `"invalid email"`, `"valid email"`.
3. Chỉ coi là `form_still_visible` khi có thông báo lỗi rõ ràng hoặc khi đã hết toàn bộ timeout mà màn hình không chuyển tiếp.
4. Nếu hết candidate email do lỗi form/timeout, phải raise đúng lỗi `RuntimeError(f"[07] Khong the dang ky email cho STT {stt}: form validation error hoac timeout")`, không được gán nhầm là "email đã có tài khoản".

---

## 2. Slot Accounting Bug trong `tiktok_target_eligibility.py`

### Triệu chứng
Máy đã có đủ 8 tài khoản vật lý hoặc 8 dòng trong tracking workbook nhưng scheduler vẫn tiếp tục pick máy vào batch, dẫn tới crash `MACHINE_FULL_8_ACCOUNTS`.

### Nguyên nhân gốc rễ
Trong `load_registered_mailboxes()`:
```python
# LỖI:
if tiktok_id and stt_idx is not None and stt_idx < len(row):
    machine_counts[m] += 1
```
Khi máy có row thứ 8 đã được ghi nhận vào file quản lý nhưng ô `tiktok_id` còn trống (ví dụ tài khoản đang chờ xác thực hoặc reg dở), điều kiện `if tiktok_id` bị False. Do đó `machine_counts[m]` chỉ đếm được 7, khiến `select_pending_targets()` coi máy vẫn còn slot trống và tiếp tục dispatch.

### Quy tắc xử lý
Đếm mọi slot/dòng đã được cấp phát cho máy:
```python
# ĐÚNG:
if stt_idx is not None and stt_idx < len(row):
    machine_counts[m] += 1
```

---

## 3. Pipeline Alert Guard Phase 2a (`run_night_chain_pipeline.py`)

### Triệu chứng
Telegram liên tục nhận cảnh báo đỏ Phase 2a thất bại dù thực tế batch đăng ký đã chạy xong và xử lý hết danh sách target.

### Nguyên nhân gốc rễ
- Pipeline chỉ kiểm tra `exit_code != 0`. Khi 1 target fail (ví dụ captcha, checkpoint, mạng), runner trả mã thoát khác 0.
- Điều này nhầm lẫn giữa **lỗi vận hành farm trên target** (đã được ghi nhận vào `all_results.json` và tổng kết cuối đêm) với **lỗi script/hạ tầng pipeline**.

### Quy tắc xử lý
Đồng bộ guard tương tự Phase 1 (Gmail):
```python
tiktok_reg_details = parse_tiktok_details(tiktok_reg_out)
# Nếu batch đã hoàn tất và ghi nhận kết quả từng máy (total > 0), không bắn alert khẩn cấp
if not (isinstance(tiktok_reg_details, dict) and int(tiktok_reg_details.get("total", 0) or 0) > 0):
    _send_night_chain_alert("Phase 2a (Reg TikTok)", tiktok_reg_code, parse_summary_line(tiktok_reg_out, "TikTok"), str(TIKTOK_REG_REPO_DIR / "social_reg_log.txt"))
```
