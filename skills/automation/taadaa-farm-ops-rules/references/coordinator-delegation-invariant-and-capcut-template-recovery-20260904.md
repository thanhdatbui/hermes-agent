# Coordinator Delegation Invariant & Subagent Zero-Interference (2026-09-04)

## 1. Coordinator Role & Zero-Direct-Debug Policy
- **Nguyên tắc bất biến:**
  - Khi nhận Farm Alert `[MÁY N]`, bug report, hoặc task debug/recovery:
    - Coordinator **BẮT BUỘC** gọi `delegate_task` cho worker subagent xử lý từ Turn 1.
    - **CẤM TUYỆT ĐỐI** Coordinator tự ý can thiệp chạy lệnh terminal, inspect ADB, dump UI, hoặc sửa code trực tiếp trên thiết bị/worktree.
  - **Khi User giục hoặc hỏi tiến độ ("Ủa lâu thế à", "xong chưa"):**
    - Coordinator CHỈ báo cáo trạng thái tiến trình của subagent ngắn gọn (đang chạy bước nào, vì sao cần thời gian trên thiết bị thật).
    - **CẤM PANIC:** Tuyệt đối không tự ý gõ lệnh terminal thăm dò hay can thiệp ADB song song vì sẽ gây race condition, chiếm quyền thiết bị và xung đột với subagent đang chạy.

## 2. Recovery & Auto-Dismiss CapCut Template & UIAutomator Helper
- **UIAutomator Helper App:** Khi `com.github.uiautomator` đè foreground, force-stop helper package và re-foreground `SplashActivity`.
- **CapCut Template / Creation Hub:** Tự động nhận diện (`_is_capcut_template_surface`) và dismiss (`_dismiss_capcut_template_surface`) bằng nút đóng/back góc trên hoặc semantic back bounded, fail-closed sau 4 lần thử.
