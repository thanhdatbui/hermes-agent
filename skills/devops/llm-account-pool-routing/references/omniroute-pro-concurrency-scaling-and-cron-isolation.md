### Pathology 37: Bẫy Cronjob Re-activate Tự Động Phá Vỡ Cách Ly (`is_active = 0`) & Chiến Lược Tăng Tải Concurrency Cap Cho Pool Pro (`max_concurrent: 2 -> 3`) (2026-10-01)

**Triệu chứng:**
- Người vận hành đã chủ động cách ly 23 tài khoản Antigravity Free bị thiếu `project_id` (gây lỗi 422) bằng cách chạy SQL đặt `is_active = 0`.
- Tuy nhiên, chỉ sau khoảng 1 tiếng, khi kiểm tra lại SQLite thì 23 tài khoản này lại đột ngột biến thành `is_active = 1` và tiếp tục bị router gọi trúng khi Tier 1 tràn tải!
- Đồng thời, người dùng băn khoăn: *"Mức `max_concurrent: 2` trên 20 acc Pro có bị thấp quá gây nghẽn không, và có nâng lên 3 được không?"*.

**Cơ chế lỗi cốt lõi (Cron Re-activation Blindness & Concurrency Capacity):**
1. **Bẫy Cron Re-activation Blindness:**
   - Trong script định kỳ `cron_omni_activate_soaked_codex.py` (chạy mỗi 1 tiếng lúc phút 00), tác giả trước đây đã thêm logic "cứu hộ tự động" cho Antigravity:
     ```python
     UPDATE provider_connections 
     SET is_active = 1 
     WHERE provider = 'antigravity' 
       AND is_active = 0 
       AND test_status = 'active'
     ```
   - **Bản chất bẫy:** Khi người dùng hoặc script phát hiện tài khoản bị lỗi `422 Missing Google projectId`, trường `test_status` trong database vẫn có thể đang lưu giá trị `'active'`.
   - Kết quả: Cứ mỗi 60 phút, cron này tự động quét và ép bật `is_active = 1` cho TẤT CẢ các tài khoản Antigravity đang bị tắt, phá vỡ hoàn toàn mọi nỗ lực cách ly acc hỏng của người vận hành!
2. **Khắc phục triệt để trong Cron:**
   - Bắt buộc thêm ràng buộc tính toàn vẹn `project_id`:
     ```sql
     UPDATE provider_connections 
     SET is_active = 1 
     WHERE provider = 'antigravity' 
       AND is_active = 0 
       AND test_status = 'active'
       AND project_id IS NOT NULL 
       AND project_id != ''
     ```
   - Ràng buộc này đảm bảo tài khoản Antigravity chỉ được phép tự động kích hoạt lại khi và chỉ khi đã có Project ID hợp lệ trên Google Cloud Code.

3. **Phân tích & Chiến lược nâng `max_concurrent: 2 -> 3` cho Pool Pro:**
   - **Số liệu thực tế 7 ngày (58.000+ requests):**
     - Mức `max_concurrent: 2` trên 20 acc Pro thực tế đã gánh trọn vẹn **96.2% – 99.8%** tổng lưu lượng hàng ngày (tỷ lệ tràn xuống Free chỉ từ 0.2% đến 4%). Lỗi 429 trên Pro chỉ 1 – 23 lần/ngày (<0.2%).
     - Tình trạng tràn tải chỉ xảy ra cục bộ trong 1-2 phút cao điểm khi nhiều subagent đồng loạt dội requests context nặng (>160k tokens, ngâm 20s–45s).
   - **Đánh giá khi nâng lên `max_concurrent: 3` cho Pro:**
     - **Tăng 50% công suất tức thời:** $20 \text{ acc} \times 3 = \mathbf{60 \text{ luồng song song}}$ (thay vì 40 luồng), đủ sức nuốt trọn hầu hết các đợt cao điểm mà không cần tràn xuống Free.
     - **An toàn hạn ngạch:** Tài khoản Google AI Pro trả phí có hạn mức RPM/TPM cao hơn hẳn tài khoản thường, hoàn toàn đủ sức chịu 3 luồng đồng thời mà không bị Google bóp rate limit.
     - **Thuật toán `least-used` bảo vệ:** Strategy `least-used` trong combo `omni-worker` luôn rải đều request vào tài khoản ít việc nhất, tránh dồn cục 3 request nặng vào cùng 1 tài khoản nếu các tài khoản khác còn slot rảnh.
     - **Tài khoản Thường (Free) BẮT BUỘC giữ nguyên mức 2:** Không nâng Free lên 3 vì tài khoản miễn phí có RPM rất thấp, nếu nạp 3 request song song sẽ bị Google bóp latency hoặc nổ 429 ngay lập tức.
   - **Hiệu lực tức thì:** OmniRoute dùng `TTLCache` in-memory 5 giây cho các bản ghi provider connections (`readCache.ts`). Do đó, việc update `max_concurrent = 3` trực tiếp trong SQLite có hiệu lực runtime trong vòng 5 giây mà **không cần restart tiến trình OmniRoute**.
