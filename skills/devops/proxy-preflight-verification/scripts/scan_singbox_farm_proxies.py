#!/usr/bin/env python3
"""
Scan Sing-box Farm Proxy Cluster (Ports 20001..20080) on 192.168.110.2
Concurrent probe with dual endpoint verification and classification:
- OK: HTTP 200 with valid public IPv4
- 502: Bad Gateway (upstream 4G dongle/modem down)
- RESET: Connection reset (WinError 10054 / remote disconnected)
- REFUSED: Connection refused (WinError 10061 / port closed / container down)
- TIMEOUT: Connect/read timeout
"""

import argparse
import concurrent.futures
import json
import re
import sys
import time
import requests

IP_REGEX = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")

def probe_one_endpoint(proxy_url, target_url, timeout):
    try:
        r = requests.get(
            target_url,
            proxies={"http": proxy_url, "https": proxy_url},
            timeout=timeout,
            headers={"User-Agent": "curl/7.88.1"}
        )
        ip = r.text.strip()
        if r.status_code == 200 and IP_REGEX.match(ip):
            return {"status": "OK", "ip": ip, "code": 200, "error": None}
        elif r.status_code == 502:
            return {"status": "502", "ip": None, "code": 502, "error": "502 Bad Gateway"}
        else:
            return {"status": f"HTTP_{r.status_code}", "ip": None, "code": r.status_code, "error": f"HTTP {r.status_code}: {ip[:50]}"}
    except requests.exceptions.ProxyError as e:
        err_str = str(e)
        if "502" in err_str or "Bad Gateway" in err_str:
            return {"status": "502", "ip": None, "code": 502, "error": "502 Bad Gateway"}
        elif "10061" in err_str or "refused" in err_str.lower():
            return {"status": "REFUSED", "ip": None, "code": None, "error": "Connection Refused (port closed/container down)"}
        elif "10054" in err_str or "reset" in err_str.lower() or "remotedisconnected" in err_str.lower():
            return {"status": "RESET", "ip": None, "code": None, "error": "Connection Reset (upstream disconnected)"}
        elif "timed out" in err_str.lower() or "timeout" in err_str.lower():
            return {"status": "TIMEOUT", "ip": None, "code": None, "error": "Proxy Connect Timeout"}
        else:
            return {"status": "PROXY_ERROR", "ip": None, "code": None, "error": err_str[:100]}
    except requests.exceptions.Timeout as e:
        return {"status": "TIMEOUT", "ip": None, "code": None, "error": "Request Timeout"}
    except requests.exceptions.ConnectionError as e:
        err_str = str(e)
        if "10061" in err_str or "refused" in err_str.lower():
            return {"status": "REFUSED", "ip": None, "code": None, "error": "Connection Refused"}
        elif "10054" in err_str or "reset" in err_str.lower():
            return {"status": "RESET", "ip": None, "code": None, "error": "Connection Reset"}
        return {"status": "CONN_ERROR", "ip": None, "code": None, "error": err_str[:100]}
    except Exception as e:
        return {"status": "ERROR", "ip": None, "code": None, "error": f"{type(e).__name__}: {str(e)[:100]}"}

def probe_machine(machine_id, host, base_port, timeout):
    port = base_port + machine_id
    proxy_url = f"http://{host}:{port}"
    start_t = time.time()
    
    res = probe_one_endpoint(proxy_url, "http://api.ipify.org", timeout)
    if res["status"] != "OK":
        res2 = probe_one_endpoint(proxy_url, "http://icanhazip.com", timeout)
        if res2["status"] == "OK":
            res = res2
        elif res["status"] in ("TIMEOUT", "PROXY_ERROR") and res2["status"] in ("502", "REFUSED", "RESET"):
            res = res2

    elapsed = round(time.time() - start_t, 2)
    res["machine_id"] = machine_id
    res["port"] = port
    res["elapsed"] = elapsed
    return res

def run_scan(host="192.168.110.2", start_port=20001, end_port=20080, workers=30, timeout_val=3.0, json_output=None):
    base_port = 20000
    start_m = start_port - base_port
    end_m = end_port - base_port
    timeout_tuple = (timeout_val, timeout_val)

    print(f"[*] Starting proxy scan: {start_port}..{end_port} (Machines {start_m}..{end_m}) on {host}")
    print(f"[*] Concurrency: {workers} workers, Timeout: {timeout_val}s")
    start_time = time.time()

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_m = {executor.submit(probe_machine, m, host, base_port, timeout_tuple): m for m in range(start_m, end_m + 1)}
        for future in concurrent.futures.as_completed(future_to_m):
            m = future_to_m[future]
            try:
                results[m] = future.result()
            except Exception as e:
                results[m] = {
                    "machine_id": m,
                    "port": base_port + m,
                    "status": "EXCEPTION",
                    "ip": None,
                    "code": None,
                    "error": str(e),
                    "elapsed": 0
                }

    total_time = round(time.time() - start_time, 2)
    total_scanned = end_m - start_m + 1

    ok_list = []
    error_list = []
    category_counts = {}

    for m in range(start_m, end_m + 1):
        r = results.get(m)
        status = r["status"]
        category_counts[status] = category_counts.get(status, 0) + 1
        if status == "OK":
            ok_list.append(r)
        else:
            error_list.append(r)

    print(f"[*] Scan completed in {total_time}s\n")
    print("=" * 60)
    print(f"SUMMARY REPORT: {len(ok_list)}/{total_scanned} LIVE, {len(error_list)}/{total_scanned} FAILED")
    print("=" * 60)
    print("Breakdown by status:")
    for cat, cnt in sorted(category_counts.items()):
        print(f"  - {cat}: {cnt}")
    print("-" * 60)

    if error_list:
        print("\nDETAILED LIST OF FAILED PROXIES:")
        for r in error_list:
            print(f"  - Cổng {r['port']} [Máy {r['machine_id']:02d}]: {r['status']} | {r['error']} ({r['elapsed']}s)")
    else:
        print(f"\nAll {total_scanned} proxies are live and healthy!")

    print("\n" + "=" * 60)

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "host": host,
        "total": total_scanned,
        "live_count": len(ok_list),
        "fail_count": len(error_list),
        "breakdown": category_counts,
        "failed_details": error_list,
        "live_details": ok_list,
        "all_results": [results[m] for m in range(start_m, end_m + 1)]
    }

    if json_output:
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[*] Saved report to {json_output}")

    return report

def main():
    parser = argparse.ArgumentParser(description="Scan Sing-box Farm Proxy Ports")
    parser.add_argument("--host", default="192.168.110.2", help="Proxy cluster host IP (default: 192.168.110.2)")
    parser.add_argument("--start-port", type=int, default=20001, help="Start port (default: 20001)")
    parser.add_argument("--end-port", type=int, default=20080, help="End port (default: 20080)")
    parser.add_argument("--workers", type=int, default=30, help="Concurrent workers (default: 30)")
    parser.add_argument("--timeout", type=float, default=3.0, help="Socket connect/read timeout in seconds (default: 3.0)")
    parser.add_argument("--output", default=None, help="Save JSON report to file")
    args = parser.parse_args()

    run_scan(
        host=args.host,
        start_port=args.start_port,
        end_port=args.end_port,
        workers=args.workers,
        timeout_val=args.timeout,
        json_output=args.output
    )

if __name__ == "__main__":
    main()
