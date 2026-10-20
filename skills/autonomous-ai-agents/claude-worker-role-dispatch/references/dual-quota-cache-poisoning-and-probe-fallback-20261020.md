# Dual Quota Cache Disconnect and Probe Timeout Cache-Poisoning Bug (20/10/2026)

## 1. Su Co Hien Truong va Cau Hoi Cua Operator

Operator da chan chinh:
> *"Tai sao cu loi cache quota hoai the t da ep phai cap nhat quota moi r ma? Fix di"*

### Trieu chung:
1. Operator / Agent da chu dong chay: `python D:/Taadaa/tools/refresh_claude_quota_file.py`.
   Lenh thanh cong va in: `Refreshed plan-usage-history.json with live quota: 5h 21.0% / weekly 6.0%`.
2. Tuy nhien, ngay sau do khi goi `claude_worker.py --role planner ...`, lenh bi chan dung voi ma loi `exit 21`:
   - Quota 5 gio: N/A% (nguong 85%)
   - Quota tuan: N/A% (nguong 90%)
   - Ly do: Timeout khi truy van /usage tu Claude CLI
3. Nghich ly: Quota thuc te an toan (21% / 6%), da ep refresh, nhung lenh van bi chan vi "Quota N/A".

---

## 2. Phan Tich Goc Re: Hai Tang Cache Bi Lech Pha

He thong kiem soat Quota ton tai 2 tang luu tru cache doc lap:

### Tang 1: Cache Lich Su (plan-usage-history.json)
- Vi tri: Thu muc Claude Roaming (`plan-usage-history.json`).
- Nguoi dung: `claude_worker.py`, `haiku_worker.py`, `refresh_claude_quota_file.py`.
- Co che: Luu mang `samples` chua lich su do (`fh`: 5h usage, `sd`: weekly usage, `t`: timestamp ms).
- TTL Stale: `MAX_QUOTA_STALE_HOURS = 2.0` (2 gio).

### Tang 2: Cache Vang Lai cua Quota Guard Wrapper (claude_quota_cache.json)
- Vi tri: Thu muc runtime cache cua Claude Quota Guard (`claude_quota_cache.json`).
- Nguoi dung: `claude_quota_guard.py` (Pre-Tool Execution Guard chan o wrapper `claude.exe`).
- Co che: Luu snapshot JSON lan probe gan nhat (`decision`, `used_5h`, `used_weekly`, `ts`).
- TTL Stale: `CACHE_TTL_SECONDS = 45.0` (chi 45 giay!).

---

## 3. Co Che Sinh Loi Ngo Doc Cache (Cache Poisoning)

1. `refresh_claude_quota_file.py` chi ghi vao Tang 1, KHONG ghi vao Tang 2.
2. Khi `claude_worker.py` bat binary Claude, wrapper `claude_quota_guard.py` kiem tra Tang 2.
3. Do TTL chi co 45s, cache het han. Guard phai probe live: `claude.exe -p /usage --output-format json` (timeout 20s).
4. Khi mang lag hoac CLI khoi dong cham, probe nem `TimeoutExpired`.
5. Code cu cua Guard nhan `u_5h is None`, lap tuc ghi de `BLOCK_PROBE_FAILED` vao file cache 45s.
6. Hau qua: Cac tien trinh tiep theo trong 45s doc trug cache bi ngo doc nay, lap tuc fail `exit 21` voi Quota `N/A%`, khong probe lai du quota thuc te chi moi 21%.

---

## 4. Giai Phap Kien Truc Triet De

1. **Fallback sang Tang 1 khi Probe Live Timeout:**
   Truoc khi phan quyet `BLOCK_PROBE_FAILED`, Guard doc mau hop le gan nhat trong `plan-usage-history.json` (< 2 gio). Neu co, dung ngay de ra quyet dinh `ALLOW` / `BLOCK`.
2. **Triet Tieu Ngo Doc Cache (Never Cache Transient Failures):**
   Neu quyet dinh la `BLOCK_PROBE_FAILED`, TUYET DOI CAM ghi vao file cache. Lan goi sau se probe lai ngay.
3. **Nang TTL Cache Hop Ly:**
   Nang `CACHE_TTL_SECONDS` tu 45s len 180s (3 phut) de giam thieu probe don dap gay nghen.
