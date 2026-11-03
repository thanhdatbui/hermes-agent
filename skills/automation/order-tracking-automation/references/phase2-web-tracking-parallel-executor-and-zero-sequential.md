# Phase 2 Web Tracking Parallel Executor & Zero-Sequential Discipline (2026-11-03)

## 1. Bẫy Tàn Dư Tuần Tự (The Lingering Sequential Trap)
- **Sự cố:** Dù Phase 1 (bóc app máy S7) đã được chuyển sang đa luồng `ThreadPoolExecutor`, Phase 2 (theo dõi Web API bưu cục qua `track_web_order`) vẫn bị viết sót lại một vòng lặp tuần tự:
  ```python
  # SAI: Vòng lặp tuần tự làm chậm và nghẽn toàn bộ nếu 1 đơn bị lag mạng
  for o in orders_fresh:
      if classify_order_phase(o) == "ACTIVE_WEB_TRACKING":
          res = track_web_order(o, dry_run=dry_run)
  ```
- **Hậu quả:** Khi số lượng đơn có mã bưu cục tăng lên, việc gọi HTTP request tuần tự tới API bưu cục (J&T, GHN, SPX) làm kéo dài thời gian watchdog. Nếu 1 đơn gặp sự cố mạng hoặc phản hồi chậm (2-5s), toàn bộ các đơn phía sau bị trễ theo, vi phạm trực tiếp nguyên tắc vận hành: **Farm cấm cuốn chiếu / tuần tự, bắt buộc làm song song đồng loạt**.

## 2. Giải Pháp Chuẩn Hóa Song Song 100% Cả 2 Pha
1. **Chuyển Phase 2 sang ThreadPoolExecutor độc lập:**
   ```python
   active_web_orders = [o for o in orders_fresh if classify_order_phase(o) == "ACTIVE_WEB_TRACKING"]
   if active_web_orders:
       max_web_workers = len(active_web_orders)
       with ThreadPoolExecutor(max_workers=max_web_workers) as executor:
           futures = [executor.submit(_web_track_worker, order) for order in active_web_orders]
           for future in as_completed(futures):
               results["web_track_results"].append(future.result())
   ```
2. **Cô lập lỗi tại worker `_web_track_worker`:**
   - Mỗi đơn chạy trong một worker riêng biệt có `try...except`.
   - Một đơn lỗi kết nối hoặc parse HTML thất bại chỉ sinh status `WEB_TRACK_ERROR` cho riêng đơn đó, không bao giờ ngắt quãng hay ảnh hưởng đến kết quả tracking của các đơn còn lại.
3. **An toàn dữ liệu đồng thời:**
   - Dữ liệu ghi trực tiếp vào SQLite SSOT `farm_master.db` (bảng `orders`) qua `farm_db.upsert_order`.
   - Khi ghi mirror ra file `orders.json`, sử dụng file lock hoặc đồng bộ hóa thread-safe để tránh race conditions.
