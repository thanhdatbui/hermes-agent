# OmniRoute Antigravity Concurrency & Review Payload Optimization

## 1. Cấu hình OmniRoute (`port 20129`)
- Combo pool `ag-gemini-pool-3` chứa 13 tài khoản Antigravity (12 Pro + 1 Starter Standby) hoạt động theo cơ chế `priority` spillover.
- **`maxConcurrent`:** Đặt 8 cho các tài khoản Google AI Pro, 3 cho Starter (tổng dung lượng ~100 slots đồng thời).
- **`DEFAULT_TIMEOUT_MS` (Semaphore Queue Timeout):** Đặt 90,000ms (90s) thay vì 30s mặc định trong `open-sse/services/accountSemaphore.ts` để chống văng lỗi `SEMAPHORE_TIMEOUT` khi nhiều tiến trình chạy song song.
- **Persisted Cooldown Gate:** Tài khoản hết quota (429) được OmniRoute tự động skip (0ms) sang tài khoản tiếp theo, không mồi request vô ích.

## 2. Tối ưu Payload Review (Diff-Scoped Anti-Wedging)
- **CẤM:** Nhét toàn bộ file test/mock/fixtures chứa hàng nghìn dòng XML vào prompt review (đẩy context lên 180k tokens làm nghẽn pool và chậm model).
- **BẮT BUỘC:** Chỉ gửi `git diff -U5` của đúng các file thay đổi trong scope + rubric yêu cầu an toàn/fail-closed.
- **Streaming & TTFT:** Dùng `stream: True` và đặt socket timeout 90s thay vì chờ blocking 300s.
