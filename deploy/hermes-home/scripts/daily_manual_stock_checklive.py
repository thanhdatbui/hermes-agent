"""
Cron 07:00 Check Live kho UP TAY — TẤT CẢ SP có hàng
- SP 40 TikTok: khommo247 API (cookies Camoufox) + fallback VPS direct
- SP 57 IG: clonefbig CDP (browser Hermes port 9222, chia batch 400)
- SP khác (38/39/60/61): báo số lượng stock + die tích lũy (kể cả 0)
Báo cáo Telegram: số lượng từng SP, live/die mới dọn, so sánh với hôm qua.
"""
import sys, os, time, json, subprocess, urllib.request, urllib.parse, random, datetime, socket, glob

# ============ CONFIG ============
PROFILE_DIR = os.path.expandvars(r"%LOCALAPPDATA%\hermes\scripts\khommo_profile")
COOKIE_FILE = os.path.join(PROFILE_DIR, "khommo_cookies.txt")
COOKIE_TTL = 6 * 3600
SSH_KEY = os.path.expanduser("~/.ssh/doravo_deploy")
VPS = "root@152.42.187.200"
PASS_PROXY = "TaadaaMobi#2026!"
PROXY_BASE = "test.taadaa.click"
CAMOUFOX_PY = os.path.expandvars(r"%LOCALAPPDATA%\hermes\scripts\khommo_get_cookies.py")
CAMOUFOX_PYTHON = r"D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe"
IG_CDP_PY = os.path.expandvars(r"%LOCALAPPDATA%\hermes\scripts\ig_check_cdp.py")
IG_ITEMS_FILE = os.path.expandvars(r"%LOCALAPPDATA%\hermes\scripts\clonefbig_items.json")
IG_RESULT_FILE = os.path.expandvars(r"%LOCALAPPDATA%\hermes\scripts\clonefbig_result.json")
STATE_FILE = os.path.expandvars(r"%LOCALAPPDATA%\hermes\scripts\checklive_state.json")

# SP up tay: id -> (tên, loại_check)
SP_MAP = {
    40: ("TikTok Random Live", "tiktok"),
    57: ("IG 2FA On Aged 1-30d", "ig"),
    38: ("TikTok US Like New", "none"),
    39: ("IG New Reg Has Avatar", "none"),
    60: ("X Search Top 2025", "none"),
    61: ("Gmail Log ALL có Mail khôi phục", "none"),
}

def log(msg):
    print(msg, flush=True)

def now_str():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

# ---------- SSH/DB ----------
def vps_query(sql: str) -> str:
    wrapper = ('export MYSQL_PWD="$(awk -F= \'/^DB_PASSWORD=/{print $2}\' /root/.shopclone7_db_credentials)"\n'
               'DB_USER="$(awk -F= \'/^DB_USER=/{print $2}\' /root/.shopclone7_db_credentials)"\n'
               'DB_NAME="$(awk -F= \'/^DB_NAME=/{print $2}\' /root/.shopclone7_db_credentials)"\n'
               'DB_HOST="$(awk -F= \'/^DB_HOST=/{print $2}\' /root/.shopclone7_db_credentials)"\n'
               'mysql -h"$DB_HOST" -u"$DB_USER" "$DB_NAME" -N')
    proc = subprocess.Popen(["ssh", "-i", SSH_KEY, "-o", "BatchMode=yes", VPS, wrapper],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate(input=sql.encode("utf-8"), timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"VPS SQL error: {err.decode()[:200]}")
    return out.decode("utf-8", errors="ignore").strip()

def get_all_up_stock():
    sql = ("SELECT p.id, p.name, "
           "(SELECT COUNT(*) FROM product_stock ps WHERE ps.product_code=p.code) AS stock, "
           "(SELECT COUNT(*) FROM product_die pd WHERE pd.product_code=p.code) AS die_total, "
           "(SELECT COALESCE(SUM(po.amount), 0) FROM product_order po WHERE po.product_id=p.id AND po.create_gettime >= DATE_SUB(CURDATE(), INTERVAL 1 DAY) AND po.create_gettime < CURDATE()) AS sold_yesterday, "
           "(SELECT COALESCE(SUM(po.amount), 0) FROM product_order po WHERE po.product_id=p.id AND po.create_gettime >= DATE_FORMAT(NOW(), '%Y-%m-01 00:00:00')) AS sold_month, "
           "(SELECT COALESCE(SUM(po.amount), 0) FROM product_order po WHERE po.product_id=p.id) AS sold_total "
           "FROM products p WHERE p.supplier_id=0 ORDER BY p.id;")
    out = vps_query(sql)
    result = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 7:
            sid = int(parts[0])
            result[sid] = {
                "name": parts[1],
                "stock": int(parts[2]),
                "die_total": int(parts[3]),
                "sold_yesterday": int(parts[4]),
                "sold_month": int(parts[5]),
                "sold_total": int(parts[6]),
                "items": []
            }
    for sid, (name, ctype) in SP_MAP.items():
        if ctype == "none":
            continue
        sql2 = f"SELECT ps.id, ps.uid, ps.product_code, ps.account FROM product_stock ps JOIN products p ON ps.product_code=p.code WHERE p.id={sid};"
        out2 = vps_query(sql2)
        items = []
        for line in out2.splitlines():
            parts = line.split("\t")
            if len(parts) >= 4:
                items.append({"id": parts[0].strip(), "uid": parts[1].strip(), "product_code": parts[2].strip(), "account": parts[3].strip()})
        result[sid]["items"] = items
    return result

def move_die(items, product_code):
    if not items:
        return 0
    deleted = 0
    chunk_size = 200
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i+chunk_size]
        ids = ",".join(str(x["id"]) for x in chunk)
        sql = ["START TRANSACTION;"]
        for item in chunk:
            acc = item['account'].replace("'", "''").replace("\\", "\\\\")
            uid = item['uid'].replace("'", "''")
            code = item['product_code'].replace("'", "''")
            sql.append(f"INSERT INTO product_die (product_code, seller, uid, account, create_gettime, type) VALUES ('{code}', 0, '{uid}', '{acc}', NOW(), 'checklive_daily');")
        sql.append(f"DELETE FROM product_stock WHERE id IN ({ids});")
        sql.append("COMMIT;")
        vps_query("\n".join(sql))
        deleted += len(chunk)
    return deleted

# ---------- TikTok check ----------
def get_cookies():
    if os.path.exists(COOKIE_FILE):
        age = time.time() - os.path.getmtime(COOKIE_FILE)
        if age < COOKIE_TTL:
            with open(COOKIE_FILE) as f:
                ck = f.read().strip()
            if "KHOMMO247SESSID_V2" in ck:
                return ck
    log("[TikTok] Lấy cookies mới bằng Camoufox...")
    r = subprocess.run([CAMOUFOX_PYTHON, CAMOUFOX_PY], capture_output=True, text=True, timeout=420)
    if r.returncode != 0 or "KHOMMO247SESSID_V2" not in r.stdout:
        raise RuntimeError(f"Không lấy được cookies khommo247: {r.stderr[-200:]}")
    return r.stdout.strip().splitlines()[-1]

def check_tiktok_api(username, cookies, proxy):
    enc_pass = urllib.parse.quote(PASS_PROXY, safe="")
    proxy_url = f"http://{proxy['username']}:{enc_pass}@{PROXY_BASE}:{proxy['port']}"
    req = urllib.request.Request(
        "https://khommo247.com/api/tiktok_check.php",
        data=json.dumps({"username": username}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Cookie": cookies,
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://khommo247.com/cong-cu/check-tiktok",
        },
        method="POST",
    )
    proxy_handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    opener = urllib.request.build_opener(proxy_handler)
    with opener.open(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))

def get_proxy_list():
    proxies = []
    for port in range(5101, 5124):
        try:
            socket.create_connection((PROXY_BASE, port), timeout=2).close()
            proxies.append({"port": port, "username": f"mobi{port-5101+1}"})
        except Exception:
            pass
    if not proxies:
        proxies = [{"port": p, "username": f"mobi{p-5101+1}"} for p in range(5101, 5124)]
    return proxies

def check_tiktok(items):
    if not items:
        return {"live": [], "die": [], "fail": [], "deleted": 0}
    cookies = get_cookies()
    proxies = get_proxy_list()
    log(f"[TikTok] Check {len(items)} acc qua khommo247 (proxy UP: {len(proxies)})...")
    live, die, fail = [], [], []
    for idx, item in enumerate(items):
        username = item["uid"]
        status = "fail"
        for attempt in range(3):
            proxy = random.choice(proxies)
            try:
                data = check_tiktok_api(username, cookies, proxy)
                if data.get("success"):
                    status = data.get("status", "fail")
                    break
            except Exception:
                pass
            time.sleep(0.8)
        if status == "live":
            live.append(item)
        elif status == "die":
            die.append(item)
        else:
            fail.append(item)
        if (idx + 1) % 25 == 0 or idx + 1 == len(items):
            log(f"  {idx+1}/{len(items)}: live={len(live)} die={len(die)} fail={len(fail)}")
    deleted = move_die(die, items[0]["product_code"] if items else "")
    log(f"[TikTok] XONG: live={len(live)} die={len(die)} (dọn {deleted}) fail={len(fail)}")
    return {"live": live, "die": die, "fail": fail, "deleted": deleted}

# ---------- IG check qua clonefbig CDP ----------
def check_ig(items):
    if not items:
        return {"live": [], "die": [], "fail": [], "deleted": 0}
    log(f"[IG] Check {len(items)} acc qua clonefbig (CDP browser Hermes)...")
    # Ghi items ra file cho ig_check_cdp.py
    with open(IG_ITEMS_FILE, "w") as f:
        json.dump(items, f, ensure_ascii=False)
    # Xóa file kết quả cũ
    if os.path.exists(IG_RESULT_FILE):
        os.remove(IG_RESULT_FILE)
    r = subprocess.run([CAMOUFOX_PYTHON, IG_CDP_PY], capture_output=True, text=True, timeout=900)
    print(r.stdout[-500:], flush=True)
    if r.returncode != 0 or not os.path.exists(IG_RESULT_FILE):
        log(f"[IG] CDP script lỗi: {r.stderr[-200:]}")
        return {"live": [], "die": [], "fail": items, "deleted": 0}
    res = json.load(open(IG_RESULT_FILE))
    live_uids = set(res.get("live", []))
    die_uids = set(res.get("die", []))
    live = [x for x in items if x["uid"].lower() in live_uids]
    die = [x for x in items if x["uid"].lower() in die_uids]
    fail = [x for x in items if x["uid"].lower() not in live_uids and x["uid"].lower() not in die_uids]
    deleted = move_die(die, items[0]["product_code"] if items else "")
    log(f"[IG] XONG: live={len(live)} die={len(die)} (dọn {deleted}) fail={len(fail)}")
    return {"live": live, "die": die, "fail": fail, "deleted": deleted}

# ---------- Ensure CDP browser ----------
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP_URL = "http://127.0.0.1:9222/json/version"

def cdp_alive():
    try:
        with urllib.request.urlopen(CDP_URL, timeout=5) as r:
            return r.status == 200
    except Exception:
        return False

def ensure_cdp_browser():
    """Đảm bảo Chrome Hermes (CDP 9222) đang chạy — nếu không thì tự mở."""
    if cdp_alive():
        log("[CDP] Chrome Hermes đang chạy (có sẵn)")
        return
    log("[CDP] Chrome Hermes chưa chạy -> tự khởi động...")
    profile_dir = os.path.expandvars(r"%LOCALAPPDATA%\hermes\browser_profile")
    try:
        subprocess.Popen([
            CHROME_EXE,
            f"--user-data-dir={profile_dir}",
            "--remote-debugging-port=9222",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Chờ CDP lên (tối đa 30s)
        for i in range(15):
            time.sleep(2)
            if cdp_alive():
                log(f"[CDP] Chrome đã lên sau {(i+1)*2}s")
                return
        raise RuntimeError("CDP không lên sau 30s")
    except Exception as e:
        raise RuntimeError(f"Không mở được Chrome CDP: {str(e)[:100]}")

# ---------- State / báo cáo ----------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            return json.load(open(STATE_FILE))
        except Exception:
            return {}
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False)

# ---------- Gửi báo cáo qua bot doravo (đọc token từ DB shop) ----------
def send_telegram_bot(text: str):
    """Gửi report qua bot doravo_stock_alert_bot (settings.telegram_token + telegram_chat_id)."""
    try:
        tk = vps_query("SELECT value FROM settings WHERE name='telegram_token';").strip()
        cid = vps_query("SELECT value FROM settings WHERE name='telegram_chat_id';").strip()
        if not tk or not cid:
            log("⚠️ Không đọc được telegram_token/chat_id từ DB")
            return
        data = urllib.parse.urlencode({"chat_id": cid, "text": text}).encode("utf-8")
        req = urllib.request.Request(f"https://api.telegram.org/bot{tk}/sendMessage", data=data)
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = json.loads(r.read().decode())
        if resp.get("ok"):
            log(f"[Bot] Đã gửi báo cáo qua bot doravo (msg_id={resp['result']['message_id']})")
        else:
            log(f"⚠️ Bot trả lỗi: {resp.get('description')}")
    except Exception as e:
        log(f"⚠️ Lỗi gửi bot: {str(e)[:100]}")

def main():
    start = time.time()
    log(f"===== CHECK LIVE KHO UP TAY - {now_str()} =====")
    try:
        all_stock = get_all_up_stock()
    except Exception as e:
        log(f"❌ LỖI đọc kho: {e}")
        return 1

    state = load_state()
    report_lines = []

    # Đảm bảo Chrome CDP sẵn sàng (cần cho check IG)
    try:
        ensure_cdp_browser()
    except Exception as e:
        log(f"⚠️ {e} — IG sẽ fail nếu không có CDP")

    for sid, (name, ctype) in SP_MAP.items():
        if sid not in all_stock:
            continue
        info = all_stock[sid]
        log(f"\n--- SP {sid}: {name} (stock={info['stock']}) ---")
        res = {"live": [], "die": [], "fail": [], "deleted": 0}
        if ctype == "tiktok" and info["items"]:
            res = check_tiktok(info["items"])
        elif ctype == "ig" and info["items"]:
            res = check_ig(info["items"])
        prev = state.get(str(sid), {})
        prev_stock = prev.get("stock", info["stock"])
        delta = info["stock"] - prev_stock
        live_n = len(res.get("live", []))
        die_n = len(res.get("die", []))
        fail_n = len(res.get("fail", []))
        deleted = res.get("deleted", 0)
        lines = [f"SP {sid} {name}:"]
        
        # Nếu tồn kho = 0 và hôm qua cũng = 0 (hết hàng sẵn) -> chỉ báo tồn 0 & doanh số nếu có, không báo check live
        if info['stock'] == 0 and prev_stock == 0:
            lines.append(f"  Tồn kho: 0 (hết hàng)")
            if info.get('sold_yesterday', 0) > 0 or info.get('sold_month', 0) > 0 or info.get('sold_total', 0) > 0:
                lines.append(f"  Đã bán: hôm qua {info.get('sold_yesterday', 0)} | tháng này {info.get('sold_month', 0)} | tổng {info.get('sold_total', 0)}")
            lines.append(f"  Tổng die tích lũy: {info['die_total']}")
        else:
            lines.append(f"  Tồn kho: {info['stock']} (hôm qua {prev_stock} → {'+' if delta>=0 else ''}{delta})")
            # Nếu có giảm tồn hoặc có đơn bán
            if delta < 0 or info.get('sold_yesterday', 0) > 0 or info.get('sold_month', 0) > 0 or info.get('sold_total', 0) > 0:
                lines.append(f"  Đã bán: hôm qua {info.get('sold_yesterday', 0)} | tháng này {info.get('sold_month', 0)} | tổng {info.get('sold_total', 0)}")
            
            # Chỉ check live khi có hàng tồn trong kho
            if info['stock'] > 0:
                lines.append(f"  Check live: live={live_n} die={die_n} (đã dọn {deleted}) fail={fail_n}")
            lines.append(f"  Tổng die tích lũy: {info['die_total']}")
        
        report_lines.append("\n".join(lines))
        state[str(sid)] = {"stock": info["stock"], "time": now_str(),
                           "live": live_n, "die": die_n, "fail": fail_n, "deleted": deleted}

    save_state(state)
    elapsed = int(time.time() - start)

    # Gộp báo cáo thành 1 tin gửi qua bot doravo
    msg = ["📊 BÁO CÁO CHECK LIVE KHO UP TAY", f"⏰ {now_str()} | Thời gian chạy: {elapsed}s", ""]
    for lines in report_lines:
        msg.append(lines)
        msg.append("")
    changed = []
    for sid in SP_MAP:
        skey = str(sid)
        if skey in state:
            s = state[skey]
            changed.append(f"SP{sid}: {s.get('stock', 0)} (die hôm nay {s.get('die', 0)})")
    msg.append("Tổng quan: " + ", ".join(changed))
    full = "\n".join(msg)

    log("\n" + "=" * 45)
    log(full)
    log("=" * 45)
    send_telegram_bot(full)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())