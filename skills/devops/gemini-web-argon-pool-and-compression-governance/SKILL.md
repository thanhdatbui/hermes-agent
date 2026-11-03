---
name: gemini-web-argon-pool-and-compression-governance
description: "Vận hành Pool Gemini-Web (Argon 1M), tự động bóc cookie GPM CDP khi 401, và tối ưu nén context cơ học Hermes."
---
# Gemini-Web (Argon Pool) & Compression Governance

Sử dụng quy chuẩn này khi vận hành pool tài khoản `gemini-web` (Argon 1M context) trên OmniRoute (`:20129`), xử lý lỗi xác thực 401 qua GPMLogin, hoặc cấu hình nén ngữ cảnh Hermes.

## 1. Bản Chất Sự Cố Pool Gemini-Web (401 Unauthorized) & Đối Soát Combo (15 vs 20 Accs)
* **Vị trí CSDL OmniRoute chuẩn:** Lưu tại `C:\Users\Kibe\.omniroute\storage.sqlite` (KHÔNG phải `AppData\Roaming\OmniRoute`).
* **Đồng bộ 2 Combo `gemini-web` và `gemini-web-argon-pool` (20 Accs Pro):**
  - Cả 2 combo hiện tại đã được đồng bộ đầy đủ **20 accounts Pro** (chạy chung danh sách 20 tài khoản xoay tua qua MobiProxy 4G, strategy `cache-optimized`).
  - `gate_b_planner.py` gọi vào `gemini-web`, còn `gemini_web_worker.py` và `consult_advisor.py` gọi vào `gemini-web-argon-pool`.
  - Cả Planner và Advisor đã được gài cứng `"reasoning_effort": "high"` để kích hoạt suy nghĩ sâu. Ngược lại, luồng Nén Context (Hermes Context Compression) giữ nguyên không reasoning để tránh timeout 503.
* Model `gemini-web` (Argon Pool) sử dụng Cookie Session:
  - `__Secure-1PSID`
  - `__Secure-1PSIDTS`
  - `__Secure-1PSIDCC`
* Khi Google hết hạn phiên hoặc đổi security token, OmniRoute ghi nhận:
  `[401]: Gemini Web session is not authenticated; refresh the __Secure-1PSID cookies.`
* **Nguyên nhân bỏ sót:**
  - Watchdog `cron_chatgpt_web_pool_watchdog.py` ban đầu chỉ quét `chatgpt-web`, `antigravity` và `codex`.
  - Thiếu nhánh cho `gemini-web` khiến tài khoản bị 401 nằm chết âm thầm dù profile GPM và tài khoản Google vẫn sống 100%.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
