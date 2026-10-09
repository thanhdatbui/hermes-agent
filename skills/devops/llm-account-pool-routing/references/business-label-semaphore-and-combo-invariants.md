# Bệnh lý Router: Nhãn Business Fake, Bẫy Semaphore 30s & Invariants Vận Hành Pool

## 1. Bản chất Nhãn "Business" vs "Restricted" trên Antigravity
- **Hiện tượng**: Dashboard hiển thị nhãn `Business` màu xanh đẹp đẽ (do đọc trường `plan: "Business"` trả về lúc OAuth ban đầu).
- **Thực tế**: Trong JSON `provider_specific_data`, trường `subscriptionTier` thực chất là `Antigravity (Restricted)`.
- **Bẫy Probe 1+1 (False Live)**:
  - Khi probe đơn lẻ với câu ngắn `1+1` hoặc câu vừa ~1.000 tokens: Google API vẫn trả về `HTTP 200 OK`.
  - Nhưng khi đưa vào Combo chạy tải thực tế với concurrency >= 2: Google lập tức nghẽn hoặc vọt latency, chiếm trọn 2/2 slots `maxConcurrent: 2`.
  - Các request tiếp theo dồn vào sẽ bị giam chân đúng 30 giây rồi nổ bão lỗi `429 Semaphore timeout after 30000ms`.
  - **Quy tắc bất biến**: Tuyệt đối CẤM tin vào kết quả probe 1 request đơn lẻ để nạp lại nhóm account Business/Restricted vào các combo chạy dồn tải của Farm.

## 2. Bẫy Công Tắc `isActive = false` Mù Trong Combo
- **Lỗ hổng kiến trúc**: Trong mã nguồn dispatch của OmniRoute (`comboStructure.ts` / `combo.ts`), router duyệt trực tiếp danh sách mảng `models` được cấu hình bên trong combo.
- **Hậu quả**: Khi user hoặc script bấm tắt công tắc account trên UI (`isActive = false`), router **HOÀN TOÀN KHÔNG KIỂM TRA** cờ này khi dispatch combo! Router vẫn âm thầm tống request vào account đã bị tắt.
- **Kỷ luật vận hành**: Muốn cách ly hoặc loại bỏ triệt để một account lỗi khỏi combo, **BẮT BUỘC PHẢI GỠ HẲN CONNECTION ID RA KHỎI MẢNG `models` CỦA COMBO ĐÓ** (thông qua API `PUT /api/combos/:id` hoặc cập nhật trường `data` trong SQLite).

## 3. Kiến Trúc Atomic Spillover (0ms Fail-Fast) vs Bẫy Cooldown Cascade
- **Phản biện Sol Reviewer**:
  - Lỗi Semaphore Timeout nội bộ chỉ chứng minh account đang quá tải (`overloaded`), KHÔNG chứng minh account bị chết (`unhealthy`).
  - Nếu áp dụng Auto-Cooldown (`markBlocked`) cứng khi dính Semaphore Timeout: khi có một đợt burst tải, toàn bộ pool sẽ bị block dây chuyền dẫn đến `Healthy Pool Size = 0` (Cooldown Cascade).
- **Giải pháp chuẩn (Affinity-First, Availability-Second)**:
  - Mở rộng `tryAcquireAccountSemaphore` ngay trước dispatch cho tất cả 19 combo strategies (bao gồm `cache-optimized` và `p2c`), không ưu tiên riêng cho `priority`.
  - Nếu account được ghim hoặc chọn đang bận full slot `maxConcurrent`: lập tức nhả `null` trong 0ms để tiến trình tiếp tục vòng lặp sang candidate tiếp theo trong pool.
  - Non-priority strategies tuyệt đối không được return early dừng luồng, mà phải tiếp tục spillover sang anh em cùng pool để đảm bảo availability.
