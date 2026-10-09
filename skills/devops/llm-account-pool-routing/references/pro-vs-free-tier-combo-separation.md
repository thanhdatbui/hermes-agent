# Pro vs Free Tier Sub-Combo Separation & Deep Nesting Pitfalls

Tài liệu này tổng kết nguyên lý phân tầng tài khoản Pro vs Free trong OmniRoute, kiến trúc phân tầng 2 lớp sạch (Clean 2-Tier Hierarchy) và các cạm bẫy khi cấu hình lồng combo (Combo Nesting).

---

## 1. Bản chất vấn đề (The Pro Starvation Pathology)
- **Hiện tượng**: Pool Antigravity có 111 tài khoản, trong đó có 16 tài khoản Google AI Pro (`g1-pro-tier` / `plan: Pro`) và 87 tài khoản Free / Standard (`free-tier` / `standard-tier`).
- **Nguyên nhân**: Khi gộp chung Pro và Free vào một combo phẳng (`ag-gemini-pool-3`) chạy thuật toán `round-robin`, request sẽ được phân bổ đều cho từng connection. Vì số lượng tài khoản Free áp đảo (~85%), nên 85% traffic tự động rơi vào tài khoản Free trong khi các tài khoản Pro còn đầy 100% quota và rảnh rỗi.
- **Hậu quả**: Tài khoản Free có quota tuần rất thấp (~200 request / 30M tokens) và chu kỳ reset cứng 7 ngày, dễ bị dính 429 sau 10-15 phút dồn tải. Trong khi đó, tài khoản Pro có quota gấp 50-60 lần và chu kỳ hồi nhanh (5h).

---

## 2. Kiến trúc 2 tầng phẳng chuẩn mực (Clean 2-Tier Priority Hierarchy)

Tuyệt đối **KHÔNG lồng 3 lớp combo đệ quy** (`omni-worker` -> `ag-gemini-pool-3` -> `ag-gemini-pro-pool`):
- Mặc dù OmniRoute hỗ trợ `MAX_COMBO_DEPTH = 3` (tối đa 10), nhưng việc lồng 3 lớp trong chế độ `execute` (`nestedComboMode: "execute"`) làm tăng độ trễ và dễ gây timeout luồng duyệt runtime units.

### Cấu trúc 5 Tầng Chuẩn trong `omni-worker`:
```text
omni-worker (Strategy: priority, nestedComboMode: "execute")
├── Tier 1: ag-gemini-pool-3 (Strategy: round-robin, 16 Pro Accounts — ƯU TIÊN 100%)
├── Tier 2: ag-gemini-free-pool (Strategy: round-robin, 87 Free Accounts — Fallback Gemini)
├── Tier 3: chatgpt-web-pool (Strategy: round-robin, 12-16 Accounts ChatGPT Web)
├── Tier 4: omni-free (Strategy: priority, Models Free ngoài: Muse Spark, MiMo, Laguna...)
└── Tier 5: ag-claude (Strategy: round-robin, Claude Sonnet 4.6 — Fallback cuối)
```

- **Tier 1 (`ag-gemini-pool-3`)**: Thu gọn chỉ chứa đúng các tài khoản Google AI Pro (`g1-pro-tier` / `plan: Pro`). Giữ nguyên name `ag-gemini-pool-3` để đảm bảo tương thích 100% với cấu hình client (Hermes `config.yaml`) và test suites.
- **Tier 2 (`ag-gemini-free-pool`)**: Tạo combo riêng chứa toàn bộ các tài khoản Free/Standard active. Đóng vai trò tấm đệm cứu hộ khi dàn Pro chạm trần concurrency hoặc cạn quota.

---

## 3. Cạm bẫy dữ liệu (Data Integrity Pitfalls)

### Pitfall 1: Thiếu `connectionId` trong combo models
- Khi tạo hoặc cập nhật combo qua API hoặc script, mỗi model entry có `kind: "model"` bắt buộc phải có trường `connectionId`.
- Nếu thiếu `connectionId`, router sẽ fallback về credential mặc định hoặc gây lỗi định tuyến tiềm ẩn (latent failure), đồng thời làm trượt các bài audit nghiêm ngặt (như `closeout_gate.py`).

### Pitfall 2: Bỏ quên tài khoản active bên ngoài combo
- Khi kiểm tra tài khoản, luôn đối soát giữa `provider_connections` trong SQLite (`storage.sqlite`) với danh sách `models` của combo.
- Tránh tình trạng tài khoản active trong DB nhưng không có trong bất kỳ combo nào (như đợt rà soát phát hiện 34 tài khoản Free active bị bỏ rơi bên ngoài `ag-gemini-pool-3`).

### Pitfall 3: Kiểm tra định kỳ cờ `is_active`
- Chỉ add những tài khoản có `is_active = 1` vào các combo active.
- Tài khoản dính lỗi auth hoặc bị vô hiệu hóa (`is_active = 0`) cần được loại trừ khỏi danh sách model của combo để tránh lãng phí vòng lặp thử lỗi và tăng latency.
