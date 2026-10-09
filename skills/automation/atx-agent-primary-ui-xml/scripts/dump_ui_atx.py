#!/usr/bin/env python3
"""
Dump live UI XML via atx-agent JSON-RPC endpoint.
Zero external dependencies (uses standard library urllib, json, subprocess).
Avoids EXIT 137 caused by 'adb shell uiautomator dump' conflicting with active uiautomator2 stub.
"""
import sys
import subprocess
import json
import urllib.request
import os
import shutil

def get_adb_bin():
    env_adb = os.environ.get("ADB_PATH")
    if env_adb and os.path.isfile(env_adb):
        return env_adb
    which_adb = shutil.which("adb")
    if which_adb:
        return which_adb
    default_xiaowei = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
    if os.path.isfile(default_xiaowei):
        return default_xiaowei
    return "adb"

def get_adb_host():
    return os.environ.get("ADB_HOST", "127.0.0.1")

def get_uiautomator_pid(serial, adb_bin, host="127.0.0.1"):
    cmd = [adb_bin]
    if host and host not in ("127.0.0.1", "localhost"):
        cmd.extend(["-H", host])
    cmd.extend(["-s", serial, "shell", "ps -A"])
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    for line in res.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 9 and parts[-1] == "com.github.uiautomator":
            return parts[1]
    return None

def ensure_uiautomator_stub(serial, adb_bin, host="127.0.0.1"):
    pid = get_uiautomator_pid(serial, adb_bin, host)
    if pid:
        return pid
    cmd = [adb_bin]
    if host and host not in ("127.0.0.1", "localhost"):
        cmd.extend(["-H", host])
    cmd.extend(["-s", serial, "shell", "/data/local/tmp/atx-agent", "curl", "-X", "POST", "http://127.0.0.1:7912/uiautomator"])
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    import time
    for _ in range(12):
        time.sleep(0.5)
        pid = get_uiautomator_pid(serial, adb_bin, host)
        if pid:
            return pid
    return None

def dump_ui(serial, output_path=None, host=None):
    adb_bin = get_adb_bin()
    if not host:
        host = get_adb_host()
    pid = ensure_uiautomator_stub(serial, adb_bin, host)
    if not pid:
        raise RuntimeError(f"com.github.uiautomator process not found in ps -A on device {serial}")

    cmd_prefix = [adb_bin]
    if host and host not in ("127.0.0.1", "localhost"):
        cmd_prefix.extend(["-H", host])

    # Set up dynamic forward
    subprocess.run(cmd_prefix + ["-s", serial, "forward", "tcp:0", "tcp:7912"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    # Parse dynamic port from forward --list
    list_res = subprocess.run(cmd_prefix + ["-s", serial, "forward", "--list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    local_port = None
    for line in list_res.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == serial and parts[2] == "tcp:7912":
            local_port = parts[1].replace("tcp:", "")
            break

    if not local_port:
        raise RuntimeError(f"Failed to resolve forwarded local port for {serial}")

    try:
        url = f"http://{host}:{local_port}/session/{pid}:com.github.uiautomator/jsonrpc/0"
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "dumpWindowHierarchy",
            "params": [True]
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        xml = data.get("result", "")
        if not xml or "<hierarchy" not in xml:
            raise RuntimeError(f"Invalid XML received from ATX: {data}")

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(xml)
        return xml
    finally:
        subprocess.run([adb_bin, "-s", serial, "forward", "--remove", f"tcp:{local_port}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dump_ui_atx.py <serial> [output_path.xml] [--host <ip>]")
        sys.exit(1)
    serial = sys.argv[1]
    out_file = None
    host = get_adb_host()
    args = sys.argv[2:]
    idx = 0
    while idx < len(args):
        if args[idx] in ("--host", "-H") and idx + 1 < len(args):
            host = args[idx + 1]
            idx += 2
        elif not out_file:
            out_file = args[idx]
            idx += 1
        else:
            idx += 1

    xml = dump_ui(serial, out_file, host=host)
    if not out_file:
        print(xml)
    else:
        print(f"Dumped {len(xml)} bytes to {out_file}")
