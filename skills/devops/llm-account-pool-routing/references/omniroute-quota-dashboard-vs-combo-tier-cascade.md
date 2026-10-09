# OmniRoute: Dashboard Quota vs Combo Tier Cascade & Cleanup Runbook

## 1. Bẫy Chẩn Đoán: Dashboard Quota ("Token Expired Hết") vs Pool Thực Tế
- **Hiện tượng:** Người dùng vào `/dashboard/quota` thấy danh sách hiện một loạt badge đỏ `Token expired` hoặc `401`, lầm tưởng toàn bộ pool tài khoản LLM (ví dụ Google Antigravity / Gemini Pro) đã cạn kiệt quota hoặc chết sạch.
- **Bản chất kỹ thuật:**
  - Trang `/dashboard/quota` liệt kê **toàn bộ tài khoản tồn tại trong database** của provider đó (bao gồm các tài khoản Free, Standard, hoặc tài khoản cũ từ nhiều tháng trước).
  - Các tài khoản thực sự phục vụ trong Combo sản xuất (như `ag-gemini-pool-3` với 22 acc Pro) là một tập con riêng biệt được gán bằng `connectionId`.
  - Kiểm tra thực tế trong SQLite (`storage.sqlite`):
    ```sql
    -- Kiểm tra trạng thái tài khoản trong pool cụ thể
    SELECT p.email, p.is_active, p.test_status, q.remaining_percentage
    FROM provider_connections p
    LEFT JOIN quota_snapshots q ON p.id = q.connection_id
    WHERE p.id IN (<list_connection_ids_from_combo>)
    ```
- **Quy tắc chẩn đoán:** Tuyệt đối không kết luận pool chết dựa vào tổng quan dashboard. Phải tra cứu theo đúng danh sách `connectionId` của combo đang chạy.

---

## 2. Bệnh Học Concurrency Cap & Trượt Tầng (Spillover Cascade)
- **Cơ chế lỗi:**
  - Combo chính (`omni-worker`) cấu hình `strategy: priority` kèm `failoverBeforeRetry: true` và `queueTimeoutMs: 1000ms`.
  - Khi nhiều worker/subagent gửi request lớn đồng thời (context 100k-200k tokens), một số acc Pro chạm concurrency cap (2/2).
  - Sau 1000ms chờ semaphore, request không kịp phục vụ sẽ bị tính là nghẽn và lập tức kích hoạt failover trượt xuống các Tier tiếp theo:
    - **Tier 1:** `ag-gemini-pool-3` (22 acc Pro 3.8 Flash).
    - **Tier 1b:** `ag-gemini-pool-3-37` (22 acc Pro 3.7 Flash) — thực chất dùng chung 22 tài khoản và chung bucket quota Google với Tier 1, không tạo thêm dung lượng độc lập.
    - **Tier 2:** `ag-gemini-free-pool` (87 acc Free) — khi nhận request `gemini-3.8-flash-tiered`, các acc Free không có quyền sẽ lập tức ném lỗi 429 / 403 Upstream.
    - **Tier 3:** `codex-luna` (Codex Luna High).
- **Hệ quả:** Request văng vào dàn account Free hoặc tài khoản rác ngoài pool, sinh ra log đỏ liên tục dù dàn Pro vẫn còn quota dồi dào.

---

## 3. Thao Tác Chỉnh Sửa & Xóa Combo An Toàn Trong OmniRoute
- **Gỡ bỏ bước (Tier) trong Combo:**
  - Có thể thực hiện qua UI modal **Edit Combo** (quy trình 4 bước: Basics $\rightarrow$ Steps $\rightarrow$ Strategy $\rightarrow$ Review & Save).
  - Hoặc cập nhật trực tiếp qua API:
    ```bash
    PUT /api/combos/:id
    Content-Type: application/json
    { "models": [ ...danh_sach_steps_moi... ] }
    ```
- **Cạm bẫy Native Confirm Dialog khi bấm Delete trên Web UI:**
  - Khi bấm nút icon thùng rác (Delete) của một Combo trên giao diện web, trình duyệt bắn hộp thoại JavaScript native `window.confirm("Delete this combo?")`.
  - Hộp thoại native này chặn đứng event loop của Playwright/CDP nếu không có handler tự động, gây timeout cho các công cụ browser automation.
  - **Khắc phục an toàn:** Gọi API `DELETE /api/combos/:id` trong context console trình duyệt hoặc qua HTTP request trực tiếp:
    ```javascript
    fetch('/api/combos/' + comboId, { method: 'DELETE' }).then(r => r.json());
    ```
    Thao tác này loại bỏ triệt để combo thừa mà không làm treo phiên điều khiển browser.
