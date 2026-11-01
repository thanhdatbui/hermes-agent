# Marketplace Research: E-Commerce Variant Clickbait & Direct Link Delivery

## 1. Context & User Correction
- Khi User yêu cầu tra cứu sản phẩm trên sàn thương mại điện tử (Shopee, Lazada) để tư vấn cấu hình/mua sắm:
  - **Lỗi 1 (Quên Link):** Agent chỉ báo giá suông hoặc giải thích thông số mà không đính kèm link sản phẩm trực tiếp (`https://shopee.vn/product/<shopid>/<itemid>`), khiến User mất công phải hỏi lại *"Sao hôm qua không gửi link cho tao"*.
  - **Lỗi 2 (Bẫy giá Clickbait Phân Loại):** Bọn shop trên Shopee luôn dùng thủ thuật gom nhiều dòng máy vào cùng 1 link để hạ giá hiển thị tối thiểu bên ngoài tìm kiếm nhằm câu view (Clickbait).

## 2. Các Dạng Bẫy Giá Phân Loại Điển Hình Trên Shopee
1. **Bẫy Barebone / Xác Máy (Không CPU, RAM, Ổ cứng):**
   - Treo giá ngoài: `1.190.000₫ - 5.355.000₫` (ví dụ Dell OptiPlex 3050 Micro).
   - Thực tế: Mức giá rẻ nhất `1.191.960₫` chỉ là phân loại `Barabone(xác máy)` (chỉ có vỏ case + mainboard + nguồn). Khi bấm chọn cấu hình chạy được (`i3 6100T/4GB/128GB` hoặc `i5 7500T/8G/256G`), giá thực tế nhảy lên `2.500.000₫ – 3.800.000₫`.
2. **Bẫy Độn Model Thấp / Cũ (N3160 / J4105 vs N100):**
   - Treo banner và tiêu đề hoành tráng: `ROUTER PC G31F N100 6 LAN FAN`, giá ngoài `2.661.330₫ - 3.699.000₫`.
   - Thực tế: Mức giá `2.661.330₫` chỉ áp dụng cho option CPU đời cũ `J4105 4 LAN`. Khi bấm chọn đúng model `N100 6P + FAN` kẹp `Full (RAM + Mik LV6)`, giá thực tế nhảy vọt lên tận **`5.393.130₫`** (gấp đôi giá hiển thị)!

3. **Bẫy Không RAM / Không Ổ Trên Thin Client & Mini PC Doanh Nghiệp (Dell Wyse 5070, Lenovo M700 Tiny):**
   - Treo giá ngoài `2.000.000₫` nhưng khi bấm chọn cấu hình thực tế:
     - Dell Wyse 5070: Chọn `KHÔNG RAM` + `EMMC 16Gb` thì đúng 2.0tr, nhưng khi chọn chạy được `RAM 8GB + SSD M.2 128GB` giá nhảy lên **`2.980.000₫`** (bản RAM 4GB + EMMC 16GB là `2.350.000₫`).
     - Lenovo ThinkCentre M700 Tiny: Giá min `2.050.000₫` là bản Barebone hoặc NEC i3/i5 8G/128G sau voucher, bản i5-6500 full 8G/256G nhảy lên `3.200.000₫`.
   - **Chiến lược tối ưu khi User cần tầm giá rẻ (~2tr):** Mini PC văn phòng trên Shopee luôn bị đội giá cao hơn 30-40% do phí sàn; nếu muốn mua quanh 1.8tr - 2.2tr thì nên lấy danh sách tên model chính xác (HP 400 G3 Mini, Dell 3050 Micro, Lenovo M700 Tiny, Dell Wyse 5070) để tìm trên các hội nhóm Facebook (Chợ Mini PC / Soft Router x86 VN) săn hàng thợ thanh lý.

## 3. Quy Tắc Bắt Buộc Khi Báo Giá Sàn TMĐT
1. **Always Extract Direct Item Link:** Mọi câu trả lời báo giá phần cứng trên sàn BẮT BUỘC phải đính kèm URL chính xác của từng shop để User click kiểm tra ngay.
2. **Check Deep Variant Modal:** Tuyệt đối không lấy dải giá min hiển thị ngoài trang search. BẮT BUỘC phải mở modal phân loại (Variant sheet), click vào đúng option hoàn chỉnh (Full CPU + RAM + SSD + License nếu có) để lấy giá thanh toán thực tế của cấu hình chạy được.
3. **Phân Tách Rõ Ràng Khi Báo Cáo:**
   - Giá xác máy (Barebone) nếu User tự có linh kiện.
   - Giá hoàn chỉnh (Full Option) để cắm điện là chạy.
   - Cảnh báo rõ cho User biết nếu sản phẩm có sự chênh lệch lớn giữa giá ngoài và giá thật bên trong.
