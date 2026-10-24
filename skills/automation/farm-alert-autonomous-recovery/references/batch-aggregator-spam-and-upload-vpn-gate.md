# Kỷ Luật Fix Alert Spam & False Challenge trong Batch Aggregator (2026-10-01)

## 1. Bối cảnh & Hiện tượng (Root Cause Analysis)
Khi nhiều máy trong fleet gặp sự cố mạng (ví dụ endpoint proxy `ifconfig.me` bị timeout hoặc mạng VPN rớt), `batch_aggregator.py` phát sinh 2 vấn đề nghiêm trọng:
1. **False Positive Challenge Alert**:
   - `CHALLENGE_KEYWORDS` chứa từ khóa `"verification"`.
   - Lỗi do proxy/curl văng ra là `egress IP verification failed`.
   - Bộ gom lỗi khớp substring `"verification"` nên phân loại nhầm các lỗi proxy/mạng thành `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`.
2. **Alert Spam (Multiline HTTP Raw Dump)**:
   - Thư viện `curl` / `goreq` khi timeout in ra toàn bộ request header gồm nhiều dòng trống:
     ```text
     GET /ip HTTP/1.1
     Host: ifconfig.me
     (nhiều dòng trống)
     context deadline exceeded
     ```
   - Tin nhắn Telegram nhồi nguyên đoạn raw dump nhiều dòng này vào, làm loãng kênh chat và gây bức xúc cho người vận hành.

## 2. Giải pháp kỹ thuật chuẩn hóa (Standard Fix Pattern)
Trong `automation-core/src/automation_core/batch_aggregator.py`:

### a. Exclude Proxy/VPN khỏi Challenge Failures
- Cập nhật `CHALLENGE_EXCLUSIONS`:
  ```python
  CHALLENGE_EXCLUSIONS: tuple[str, ...] = (
      "ip verification",
      "verification failed",
      "egress",
      "proxy",
      "vpn",
      "proxy-vpn",
      # ...
  )
  ```
- Kiểm tra cả `error_message` và `error_type` để loại trừ dứt điểm:
  ```python
  if not any(ex in (m.error_message or "").lower() for ex in CHALLENGE_EXCLUSIONS) \
     and not any(ex in (m.error_type or "").lower() for ex in CHALLENGE_EXCLUSIONS):
  ```

### b. Gọt sạch multiline raw dump thành inline string
- Định nghĩa helper `_format_inline_error(text: str, max_len: int = 160) -> str`:
  ```python
  def _format_inline_error(text: str, max_len: int = 160) -> str:
      if not text:
          return ""
      collapsed = " ".join(text.split())
      if len(collapsed) > max_len:
          return collapsed[: max_len - 3] + "..."
      return collapsed
  ```
- Mọi trường `af.error_message`, `cf.error_message` khi format ra Telegram alert bắt buộc bọc qua `_format_inline_error`.

## 3. Quy tắc Preflight VPN cho Upload Workflow (`Tiktok-video`)
- **Triết lý vận hành của User:** *Kể cả khi lướt feed thất bại thì máy vẫn được phép tiếp tục upload video, chỉ khi nào PROXY BỊ LỖI thì mới được chặn không cho chạy.*
- CẤM chặn upload chỉ vì feed session fail hoặc kết thúc với `manual-needed`.
- Cần đặt chốt chặn `require_android_vpn` ngay đầu hàm `run_real()` / `run_post()` trước khi khởi tạo `StateMachine`:
  - Phân loại rõ: `ConsumerPreflightError` vs các lỗi setup hệ thống khác.
  - Proxy sống: Cho phép upload bình thường.
  - Proxy chết / timeout: Fail-closed ngay lập tức (exit code 2), lưu report `FAILED` với `error_type="PREFLIGHT_VPN_BLOCKED"`, tuyệt đối không mở app hay nhảy vào Account Switcher.
