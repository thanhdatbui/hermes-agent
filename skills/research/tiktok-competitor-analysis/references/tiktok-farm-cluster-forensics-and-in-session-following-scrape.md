# TikTok Farm Cluster Forensics & In-Session Following Scraping

## 1. Kỹ thuật cào Following/Follower qua In-Session Fetch API (Bypass WAF & DOM Trap)

Khi cào danh sách Following (hoặc Follower) của tài khoản TikTok trên Web:
- Khách chưa đăng nhập: Bị modal "Đăng nhập vào TikTok" chặn hoàn toàn.
- Tài khoản đã đăng nhập nhưng cuộn DOM (`scrollTop`, `mouseWheel`, `scrollIntoView`): Thường xuyên bị kẹt cứng ở mốc 28–30 user do cơ chế virtualized list hoặc event listener chặn cuộn tự động.

### Giải pháp tối ưu: In-Session Fetch API
Chạy trực tiếp trong console hoặc qua Chrome CDP WebSocket `Runtime.evaluate` trên tab TikTok đã có session:

```javascript
(async () => {
    // 1. Trích xuất secUid từ HTML hydration hoặc DOM
    const hydration = JSON.parse(document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__')?.innerText || '{}');
    const secUid = hydration?.['__DEFAULT_SCOPE__']?.['webapp.user-detail']?.['userInfo']?.['user']?.['secUid'] 
                   || document.body.innerHTML.match(/"secUid":"([^"]+)"/)?.[1];
    
    // 2. scene: 21 = Following (Đang follow), 67 = Followers (Người theo dõi)
    let cursor = 0;
    let hasMore = true;
    const allUsers = [];

    while (hasMore) {
        const url = `/api/user/list/?count=30&minCursor=${cursor}&maxCursor=0&secUid=${encodeURIComponent(secUid)}&scene=21`;
        const res = await (await fetch(url)).json();
        if (res.statusCode !== 0) break;
        
        const list = res.userList || [];
        for (const item of list) {
            const u = item.user;
            if (u) {
                allUsers.push({
                    id: u.id,
                    uniqueId: u.uniqueId,
                    nickname: u.nickname,
                    avatar: u.avatarLarger,
                    signature: u.signature,
                    relation: u.relation, // 1: 1 chiều (following), 2: 2 chiều (mutual / bạn bè)
                    secUid: u.secUid
                });
            }
        }
        hasMore = res.hasMore && list.length > 0;
        cursor = res.minCursor;
        await new Promise(r => setTimeout(r, 250)); // giãn cách nhẹ
    }
    return allUsers;
})()
```

---

## 2. Dấu vết Forensics nhận diện cụm nick Phone Farm trong danh sách Following

Nhiều người lầm tưởng: *"Nick trong farm phải follow chéo nhau (`relation == 2`) mới biết là cùng farm"*.
**Thực tế ngược lại hoàn toàn**: Phone farm chuyên nghiệp **cấm** follow chéo 2 chiều để tránh tạo đồ thị liên kết cụm (graph cluster) khiến AI TikTok quét trảm hàng loạt.

Thay vào đó, các dấu vết kỹ thuật chứng minh cụm tài khoản phone farm bao gồm:

### A. Nhịp đăng ký tài khoản (Snowflake Creation Cadence)
Giải mã timestamp ngày giờ khởi tạo từ TikTok UID (64-bit integer):
```python
import datetime

def get_creation_datetime(uid: int) -> datetime.datetime:
    ts = uid >> 32
    return datetime.datetime.fromtimestamp(ts)
```
- **Nhịp reg đơn luồng**: Cứ cách đều đặn **7 – 9 phút** có 1 tài khoản mới được tạo ra liên tiếp trong cùng ngày (thời gian chạy 1 kịch bản reg mail + reg TikTok tự động trên máy farm).
- **Cụm reg đa luồng**: Nhiều tài khoản có timestamp tạo ra **cùng một giây** hoặc cách nhau 1–2 giây (nhiều máy trong dàn farm bấm hoàn tất flow reg cùng lúc).

### B. Chỉ số nhân bản & Cấu hình rập khuôn (Clone Metrics)
- **Tỷ lệ following/follower**: Quanh quẩn cùng một mức (ví dụ: ~710–730 following, ~540 follower).
- **Kho video**: Số lượng clip đăng tương đương nhau (ví dụ: ~36–46 video).
- **Quyền riêng tư**: Tất cả các nick trong cụm đều bật chế độ "Ẩn danh sách Following (Chỉ mình tôi)".
- **Pattern username**: Họ tiếng Việt ghép với chuỗi ngẫu nhiên 6 ký tự + 1-2 số đuôi (ví dụ: `nguyelkcppf`, `tonnuqrpw8l`, `truonsmcd31`, `lethibehl9s`).

### C. Mục đích của việc tài khoản chính đi follow dàn nick farm vệ tinh
1. **Phân phối danh sách UID mục tiêu**: Thay vì cào UID lạ ngoài mạng, tool farm dùng chính danh sách nick vừa reg trong hệ thống để làm mục tiêu seeding.
2. **Mồi quan hệ ban đầu (Seed Graph)**: Tạo lịch sử hoạt động và mạng lưới quan hệ ban đầu cho tài khoản.
3. **Seeding view & like đợt đầu**: Dàn nick vệ tinh này chính là nguồn người xem và tương tác đầu tiên đẩy video của tài khoản chính cắn đề xuất đợt đầu.
