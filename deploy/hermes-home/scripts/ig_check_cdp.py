"""Check IG qua clonefbig bằng Chrome CDP (port 9222, profile Hermes IP nhà) - chia batch 500."""
import sys, time, json

def main() -> int:
    from playwright.sync_api import sync_playwright

    # Đọc items từ argv: file JSON tạm
    import os
    ITEMS_FILE = os.path.expandvars(r"%LOCALAPPDATA%\hermes\scripts\clonefbig_items.json")
    OUT_FILE = os.path.expandvars(r"%LOCALAPPDATA%\hermes\scripts\clonefbig_result.json")

    items = json.load(open(ITEMS_FILE))
    usernames = [x["uid"] for x in items]
    print(f"Check {len(usernames)} IG usernames", flush=True)

    live_set, die_set = set(), set()
    batch_size = 400
    results = {}
    for idx in range(0, len(usernames), batch_size):
        chunk = usernames[idx:idx+batch_size]
        print(f"Batch {idx//batch_size+1}: {len(chunk)} usernames", flush=True)
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            except Exception as e:
                print(f"ERR CDP connect: {str(e)[:80]}", flush=True)
                raise
            page = browser.new_page()
            try:
                page.goto("https://clonefbig.com/checklive", wait_until="domcontentloaded", timeout=60000)
                # chờ CF clear
                for i in range(30):
                    low = page.title().lower()
                    if "just a moment" not in low and "chờ một chút" not in low:
                        break
                    page.wait_for_timeout(2000)
                page.wait_for_timeout(5000)

                # bấm nút Check nếu có để trigger CF token mới
                ta = page.query_selector("#inputArea")
                if not ta:
                    raise RuntimeError("Không tìm thấy inputArea")
                page.fill("#inputArea", "\n".join(chunk))
                page.wait_for_timeout(500)
                try:
                    page.evaluate("startCheck()")
                except Exception:
                    # nút check bằng click thường
                    btn = page.query_selector('button:has-text("Check")')
                    if btn:
                        btn.click()
                    else:
                        page.evaluate("document.querySelector('#btnCheck')?.click()")

                # chờ kết quả: tick live/die count tiến dần
                total = len(chunk)
                for i in range(120):  # tối đa 2 phút
                    page.wait_for_timeout(1000)
                    try:
                        live_cnt = int((page.input_value("#liveOutput") or "").count("\n") + 1 if page.input_value("#liveOutput").strip() else 0)
                    except Exception:
                        live_cnt = 0
                    try:
                        die_cnt = int((page.input_value("#dieOutput") or "").count("\n") + 1 if page.input_value("#dieOutput").strip() else 0)
                    except Exception:
                        die_cnt = 0
                    # đọc textarea
                    lv = (page.input_value("#liveOutput") or "").strip()
                    dv = (page.input_value("#dieOutput") or "").strip()
                    lset = {x.strip().lower() for x in lv.splitlines() if x.strip()}
                    dset = {x.strip().lower() for x in dv.splitlines() if x.strip()}
                    done_cnt = len(lset) + len(dset)
                    if done_cnt >= total:
                        break
                    if i > 30 and done_cnt > 0 and done_cnt == (len(lset)+len(dset)) and i % 10 == 0:
                        # không tiến triển 10s
                        pass
                live_set |= lset
                die_set |= dset
                print(f"  Batch xong: live={len(lset)} die={len(dset)}", flush=True)
            except Exception as e:
                print(f"  Batch ERR: {str(e)[:100]}", flush=True)
            finally:
                try:
                    page.close()
                except Exception:
                    pass

    # Mapping kết quả
    live_items = [x for x in items if x["uid"].lower() in live_set]
    die_items = [x for x in items if x["uid"].lower() in die_set]
    unresolved = [x for x in items if x["uid"].lower() not in live_set and x["uid"].lower() not in die_set]
    out = {
        "live": [x["uid"] for x in live_items],
        "die": [x["uid"] for x in die_items],
        "unresolved": [x["uid"] for x in unresolved],
        "live_count": len(live_items),
        "die_count": len(die_items),
        "unresolved_count": len(unresolved),
    }
    with open(OUT_FILE, "w") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"RESULT: live={len(live_items)} die={len(die_items)} unresolved={len(unresolved)}", flush=True)
    print("OUT_FILE:", OUT_FILE, flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())