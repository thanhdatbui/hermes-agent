# GPM Antigravity OAuth Feeder (Full Pool Automation)

## Mục đích
Tự động quét các profile GPM đã có sẵn session cookie Google (đã login thành công từ ca nuôi/ca tối), kích hoạt và nạp quyền OAuth Antigravity lên server OmniRoute (`:20129`), mở rộng kho quota AI đa model (Claude 4.6, Gemini 3.8 Flash, GPT-OSS).

## Quy tắc an toàn & Ràng buộc
1. **Giới hạn IP (Hard Constraint):** TỐI ĐA 1 account / 1 IP (proxy port) / 1 ngày. Sử dụng file state `gpm_oauth_daily_state.json` theo dõi `used_proxies` theo ngày (`YYYY-MM-DD`).
2. **Concurrency:** Chạy tối đa 5 workers song song (`ThreadPoolExecutor(max_workers=5)`).
3. **Loại trừ rủi ro (Farm Safety):**
   - Bỏ qua 100% tài khoản dính recovery `khoaleemagic` (`SKIPPED_KHOALE`).
   - Bỏ qua tài khoản đang nằm trong `cooldown_7days` hoặc `wrong_password_or_checkpoint` trong `oauth_pipeline_status.json`.
4. **Trình duyệt Stealth Core 142 qua GPM API:**
   - Tuyệt đối KHÔNG launch standalone Chrome bằng subprocess Playwright trực tiếp (sẽ bị Google chặn `"Trình duyệt hoặc ứng dụng này có thể không an toàn"`).
   - BẮT BUỘC khởi chạy qua GPM Local API v3: `GET http://127.0.0.1:19995/api/v3/profiles/start/{id}?win_scale=0.8`.
   - Kết nối Playwright qua CDP `connect_over_cdp(f"http://{remote_debugging_address}")`.
5. **Hậu kiểm sau khi Exchange code thành công:**
   - Gán Proxy 1:1 qua `PUT /api/settings/proxies/assignments` theo cổng proxy tương ứng.
   - Kích hoạt đồng bộ model: `POST /api/providers/{conn_id}/sync-models`.

6. **Silent Watchdog Invariant & reCAPTCHA Logger Leak Prevention (`no_agent: true`):**
   - **Hiện tượng**: Job `gpm-oauth-full-pool-feeder` (chạy định kỳ 08, 12, 16, 20, 23h) chạy dưới chế độ `no_agent: true`. Khi Google kích hoạt reCAPTCHA, hàm `solve_recaptcha_audio` từ `add_oauth_omniroute.py` in các dòng log debug (`Clicking reCAPTCHA checkbox...`, `Error solving reCAPTCHA audio: Locator.count: Frame was detached`) ra console. Hermes scheduler tưởng tiến trình có nội dung trả về nên chuyển tiếp toàn bộ log thô lên Telegram ("Cronjob Response").
   - **Nguyên nhân gốc**: Module helper `add_oauth_omniroute.py` khai báo `logging.basicConfig()` ở module-level mà không cách ly handler, kết hợp với các worker Playwright văng lỗi khi Google ngắt kết nối iframe reCAPTCHA (`Frame was detached`).
   - **Kỷ luật xử lý**:
     * Mute toàn bộ logger con trước khi gọi: `logging.getLogger("add_oauth_omniroute").handlers = [logging.NullHandler()]` với `propagate = False`.
     * Bọc các lời gọi tự động giải captcha và Playwright trong luồng redirect câm hoặc ghi ra log file riêng.
     * Áp dụng quy tắc Silent Watchdog bất biến: Nếu `success_count == 0`, script BẮT BUỘC thoát êm (`return 0`) với stdout rỗng 100% (0 bytes). Chỉ `print()` báo cáo tóm tắt khi có ít nhất 1 tài khoản được nạp thành công (`success_count > 0`).

7. **Pool Capacity Gate & Anti-Hammering Discipline:**
   - Khi Antigravity Pool trên OmniRoute (`:20129`) đã có số lượng tài khoản dồi dào (> 100 acc LIVE), việc cố nạp thêm khi dải proxy đang dính reCAPTCHA hàng loạt là không cần thiết và tiềm ẩn rủi ro làm xấu trust score của proxy.
   - Ưu tiên tạm dừng (`pause`) feeder hoặc đặt ngưỡng kiểm tra: nếu `len(active_antigravity) >= 100`, feeder tự động bỏ qua ca chạy và giữ im lặng tuyệt đối.
