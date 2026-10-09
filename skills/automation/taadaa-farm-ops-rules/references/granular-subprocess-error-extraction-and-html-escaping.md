# Granular Subprocess Error Extraction & Telegram HTML Alert Safety

## 1. Bối cảnh & Vấn đề (Anti-Pattern)
- **Chuỗi lỗi generic vô nghĩa:** Khi các consumer tiến trình con (như `run_post.py` của TikTok upload, `follow_engine.py`, `social_reg_v1.py`) kết thúc với mã lỗi khác 0 (`proc.returncode != 0`), các script điều phối caller thường gán cứng fallback generic:
  `reason = "upload_subprocess_nonzero"` hoặc `reason = "task_failed"`.
  Điều này làm vứt bỏ toàn bộ ngữ cảnh chẩn đoán phong phú trong `report.json` (`error`, `reason`, `last_state`, `status`), `stderr` (Traceback/Exception), và `stdout` (State markers).
  Hậu quả: Người vận hành nhận Farm Alert trên Telegram mà không biết lỗi thực tế là gì (lệch tài khoản, timeout ADB, kẹt template, không tìm thấy nút, v.v.), dẫn đến bức xúc và mất thời gian điều tra lại từ đầu.
- **Lỗi vỡ cú pháp HTML Telegram (`can't parse entities`):** Khi chèn các biến động (`error_reason`, `account`, `serial`, `status_text`) trực tiếp vào template HTML Telegram, nếu chuỗi lỗi có chứa các ký tự `<...>` (như `[REDACTED: contains 'token']`, `<redacted>`, `<module>`, `<stdin>`), Telegram Bot API từ chối gửi tin nhắn (HTTP 400), làm mất hoàn toàn cảnh báo sự cố.

---

## 2. Giải pháp chuẩn hoá (Case Fix: Case 85 & Case 106)

### A. Hàm bóc tách lỗi đa tầng (`_extract_upload_subprocess_error`)
Áp dụng cho mọi tiến trình caller gọi subprocess trong Taadaa farm:
```python
def _extract_upload_subprocess_error(
    rep_data: dict[str, Any] | None,
    stderr: str,
    stdout: str,
    returncode: int,
) -> str:
    """Trích xuất lỗi chi tiết, trung thực từ report.json, stderr hoặc stdout."""
    extracted_error = ""

    # Tầng 1: Đọc từ report.json (nếu có file report hợp lệ)
    if isinstance(rep_data, dict):
        err = rep_data.get("error") or rep_data.get("reason")
        last_st = rep_data.get("last_state")
        rep_st = rep_data.get("status")

        clean_err = " ".join(str(err).split()) if err is not None else ""
        if clean_err:
            if last_st and str(last_st).strip() not in clean_err:
                extracted_error = f"[{str(last_st).strip()}] {clean_err}"
            else:
                extracted_error = clean_err
        elif last_st:
            extracted_error = f"failed_at_state_{str(last_st).strip()}"
        elif rep_st and str(rep_st).strip().upper() != "SUCCESS":
            extracted_error = f"upload_status_{str(rep_st).strip()}"

    # Tầng 2: Đọc từ stderr (lấy dòng exception cuối cùng)
    if not extracted_error and stderr and stderr.strip():
        lines = [line.strip() for line in stderr.splitlines() if line.strip()]
        if lines:
            extracted_error = lines[-1]

    # Tầng 3: Đọc từ stdout (quét dòng [ERROR]/[CRITICAL] hoặc >>> State:)
    if not extracted_error and stdout and stdout.strip():
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        for line in reversed(lines):
            line_lower = line.lower()
            if "[error]" in line_lower or "[critical]" in line_lower:
                extracted_error = line
                break
        if not extracted_error:
            for line in reversed(lines):
                if ">>> state:" in line.lower() or ">>> state" in line.lower():
                    extracted_error = line
                    break

    # Tầng 4: Fallback mã thoát an toàn
    if not extracted_error:
        extracted_error = f"upload_exit_code_{returncode}"

    # Giới hạn độ dài tối đa 250 ký tự cho thông báo súc tích
    if len(extracted_error) > 250:
        extracted_error = extracted_error[:247] + "..."

    return extracted_error
```

### B. Bảo vệ cú pháp HTML Telegram (`automation_core/alerts.py`)
Luôn import `html` và escape tất cả các biến động trước khi nhúng vào template HTML:
```python
import html

safe_account = html.escape(str(account or ""))
safe_serial = html.escape(str(serial or "N/A"))
safe_error_reason = html.escape(str(error_reason or ""))
safe_status_text = html.escape(str(status_text or ""))

summary_caption = (
    f"🚨 <b>[FARM ALERT: MÁY {machine}] DỪNG PHIÊN</b>\n"
    f"• Quy trình: <b>{meta_name}</b>\n"
    f"• Máy: {machine} | Serial: {safe_serial} | Nick: {safe_account}\n"
    f"• Triệu chứng: {safe_error_reason}\n"
    f"• Hiện trường: {safe_status_text}"
)
```
Tương tự cho `send_farm_script_alert` với `safe_error_reason`.
