# TikTok Following Graph & Farm Cluster Reconnaissance

## 1. Trích xuất Following/Followers siêu tốc qua In-Session API (Bypass DOM Scroll)

Khi cần cào danh sách Following (~700 nick) hoặc Followers của một tài khoản trên TikTok Web qua Chrome CDP:
- **Hạn chế của DOM Scroll:** Cuộn container DOM thường bị khựng ở 28-30 users đầu tiên do cơ chế lazy load và ảo hóa của TikTok Web.
- **Giải pháp tối ưu:** Gọi trực tiếp in-session `fetch()` với cookie đã đăng nhập trong context tab (`Runtime.evaluate`).

```javascript
(async () => {
    // secUid lấy từ HTML hydration: document.querySelector('#__UNIVERSAL_DATA_FOR_REHYDRATION__')
    const secUid = 'MS4wLjABAAAA...'; 
    let cursor = 0;
    let hasMore = true;
    const allUsers = [];
    let loops = 0;
    // scene: 21 = Following (Đang follow), 67 = Followers (Người theo dõi)
    const scene = 21; 

    while (hasMore && loops < 35) {
        loops++;
        const url = `/api/user/list/?count=30&minCursor=${cursor}&maxCursor=0&secUid=${encodeURIComponent(secUid)}&scene=${scene}`;
        const res = await fetch(url);
        const data = await res.json();
        if (data.statusCode !== 0) break;
        const list = data.userList || [];
        for (const item of list) {
            if (item.user) allUsers.push({
                id: item.user.id,
                uniqueId: item.user.uniqueId,
                nickname: item.user.nickname,
                secUid: item.user.secUid
            });
        }
        hasMore = data.hasMore && list.length > 0;
        cursor = data.minCursor;
        await new Promise(r => setTimeout(r, 200)); // Rate limit guard
    }
    return allUsers;
})()
```

## 2. Bẫy Trường `relation` (Viewer Relation Trap)

- **CẢNH BÁO QUAN TRỌNG:** Trường `item.user.relation` trong API `/api/user/list/` **KHÔNG PHẢI** là mối quan hệ giữa kênh mục tiêu và user trong danh sách.
- `relation` phản ánh quan hệ giữa **Tài khoản đang đăng nhập trên trình duyệt (Viewer)** và user đó:
  - `0`: Viewer chưa follow user đó.
  - `1`: Viewer đang follow user đó.
  - `2`: Viewer và user đó là bạn bè (mutual follow).
- **CẤM TUYỆT ĐỐI:** Không dùng `relation == 0` để kết luận "kênh mục tiêu không có follow chéo 2 chiều".

## 3. Kỹ thuật Đối Soát Tập Giao (Intersection Gate) Chứng Minh Follow Chéo

Khi các nick vệ tinh trong dàn đối thủ bật cài đặt riêng tư **Ẩn danh sách Following/Followers ("Chỉ mình tôi")**, ta không thể vào nick vệ tinh để kiểm tra chiều ngược lại.
Cách duy nhất để chứng minh quan hệ 2 chiều:
1. Lấy danh sách **Following** của kênh mục tiêu: $F_{out} = \{u_1, u_2, ...\}$
2. Lấy danh sách **Followers** của kênh mục tiêu: $F_{in} = \{v_1, v_2, ...\}$
3. Tính tập giao:
$$\text{Mutual Set} = F_{out} \cap F_{in}$$
- Nếu $\text{Mutual Set}$ xuất hiện hàng chục đến hàng trăm nick trùng khớp, đây là **bằng chứng không thể chối cãi** về việc các nick này follow qua lại 2 chiều với kênh mục tiêu (mạng lưới seeding nội bộ).

## 4. Dấu Hiệu Nhận Diện Cụm Farm / PBN Seeding Đối Thủ

1. **Snowflake ID Timestamp (`uid >> 32`):**
   - So sánh ngày/giờ tạo nick của kênh mục tiêu với các nick trong danh sách following.
   - Nhịp tạo 7–9 phút/nick liên tiếp: Nhịp reg tự động của tool/phone farm đơn luồng.
   - Nhiều nick tạo cùng một giây hoặc cách nhau 1-2 giây: Batch reg đa luồng trên dàn phone farm.
2. **Chỉ số nhân bản (Carbon Copy Metrics):**
   - Các nick vệ tinh có chỉ số following, followers, video tương đương nhau (ví dụ: cùng 710–730 following, ~540 followers, ~40 video).
   - 100% nick vệ tinh đều bật chế độ ẩn danh sách Following.
3. **Format Username:**
   - Họ tiếng Việt + chuỗi ký tự ngẫu nhiên 6 ký tự + số đuôi (ví dụ: `truonsmcd31`, `tonnuqrpw8l`, `nguyelkcppf`).

## 5. Bản Chất Phân Bổ View, Trần Follow Nội Bộ & Nhịp Đăng Dàn Vệ Tinh (Case Study 6 Tháng)

Đối soát thực tế toàn bộ video của 5 nick vệ tinh tiêu biểu vs kênh chính:
1. **200-View Limbo ở dàn vệ tinh là BÌNH THƯỜNG:**
   - 100% nick vệ tinh đều có view trung bình chỉ từ **140 đến 250 view** (min 2 view, max < 900 view).
   - Không có "thuật toán ma thuật" giúp toàn bộ dàn nick đều triệu view. Phone farm vận hành theo **trò chơi xác suất**: 90–95% nick vệ tinh kẹt 200 view đóng vai trò chân rết seeding mồi, chỉ 1–2 nick cắn đề xuất (988K, 591K) kéo doanh thu.
2. **Trần Follower Nội Bộ (Internal Seeding Pool Ceiling):**
   - Tại sao nuôi 7 tháng, đăng 40 video mà tất cả các nick vệ tinh đều kẹt cứng ở mức **540 – 555 Follower**, không chạm nổi 1.000 Follower?
   - **Bản chất:** Con số ~540 Follower chính là **tổng quy mô cụm tài khoản trong farm của đối thủ**! Khi các máy trong farm chạy flow follow chéo cho nhau, mỗi nick sẽ nhận được tối đa ~540 follow từ toàn bộ dàn máy nội bộ.
   - Khi video của dàn vệ tinh kẹt ở 200-view limbo (không được FYP đẩy cho người ngoài), và acc không chạy kéo follow ngoài hiệu quả, **tốc độ tăng trưởng follower sẽ đâm đầu vào tường (đứng im vĩnh viễn ở mức trần nội bộ ~540)**. Muốn vượt mốc 1.000 follow (để gắn bio/livestream), bắt buộc phải có video cắn đề xuất thật hoặc mở rộng quy mô dàn máy nội bộ.
3. **Thao Tác Bấm Tay Bán Tự Động vs Cron Tự Động Hóa:**
   - Đối thủ có script nhưng **không cấu hình cron tự động**, mà vận hành bằng cách người ngồi bấm tay kích hoạt script theo đợt.
   - **Hệ quả dữ liệu:** Giải mã tại sao các đợt up video luôn tập trung vào 3 khung giờ (10h, 16h, 21h - giờ người ngồi máy rảnh tay) và khoảng cách giữa các video dài 70h – 128h (3 – 5 ngày mới up 1 clip).
   - **Đánh giá:** Khoảng cách thưa này vô tình tạo ra nhịp thở an toàn (tránh cờ bot cluster), nhưng khiến năng suất cực thấp và kẹt tăng trưởng. Farm Taadaa chạy **cron tự động hóa 100% kết hợp ngày dưỡng sinh `is_organic` (nhịp ~3.3 ngày)** đạt được cả 2 ưu điểm: an toàn thuật toán tương đương nhưng năng suất cao gấp bội và giải phóng hoàn toàn sức người.
4. **Công thức Content & Khung giờ:**
   - Thời lượng 19s – 45s, 100% visual/gái xinh reup Douyin.
   - Caption tối giản: chỉ nhồi 4–5 hashtag trending (`#xuhuong #trending #viral #foryou #tiktokvietnam`).
   - Khung giờ đăng cố định toàn dàn: 10:00, 16:00, 21:00.
