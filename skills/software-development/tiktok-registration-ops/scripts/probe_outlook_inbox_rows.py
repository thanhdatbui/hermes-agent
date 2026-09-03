import json, socket, base64, os, urllib.request, subprocess, sys

# Probe CDP inbox Outlook: liệt kê mail TikTok với time token (dùng để quyết định
# nhánh numeric OTP (mail có code 6 số) vs magic-link (mail verify-link).
# Usage: python probe_outlook_inbox_rows.py [serial]

def cdp_eval(ws_url, expression, timeout=15):
    hostport, path = ws_url.split('ws://', 1)[1].split('/', 1)
    host, port = hostport.split(':')
    sock = socket.create_connection((host, int(port)), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode('ascii')
    sock.sendall((f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
                  f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                  f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
    resp = b''
    while b'\r\n\r\n' not in resp:
        c = sock.recv(4096)
        if not c:
            break
        resp += c
    data = json.dumps({"id": 1, "method": "Runtime.evaluate",
                       "params": {"expression": expression, "returnByValue": True,
                                  "awaitPromise": True}}).encode()
    mask = os.urandom(4)
    h = bytearray([0x81])
    n = len(data)
    if n < 126:
        h.append(0x80 | n)
    elif n < 65536:
        h.append(0x80 | 126); h.extend(n.to_bytes(2, 'big'))
    else:
        h.append(0x80 | 127); h.extend(n.to_bytes(8, 'big'))
    h.extend(mask)
    sock.sendall(bytes(h) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))
    buf = b''
    sock.settimeout(timeout)
    try:
        while True:
            c = sock.recv(65536)
            if not c:
                break
            buf += c
            idx = buf.find(b'{"id":1')
            if idx >= 0:
                depth = 0
                for j in range(idx, len(buf)):
                    if buf[j:j + 1] == b'{':
                        depth += 1
                    elif buf[j:j + 1] == b'}':
                        depth -= 1
                        if depth == 0:
                            try:
                                msg = json.loads(buf[idx:j + 1].decode())
                                if msg.get('id') == 1:
                                    sock.close()
                                    return msg.get('result', {}).get('result', {}).get('value')
                            except Exception:
                                pass
                            break
    except socket.timeout:
        pass
    sock.close()
    return None

adb = r'C:\Program Files (x86)\xiaowei\tools\adb.exe'
serial = sys.argv[1] if len(sys.argv) > 1 else 'ce0217126cd4bc640c'
subprocess.run([adb, '-s', serial, 'forward', 'tcp:9224', 'localabstract:chrome_devtools_remote'],
               capture_output=True)
tabs = json.load(urllib.request.urlopen("http://127.0.0.1:9224/json", timeout=5))
inbox = None
for t in tabs:
    u = str(t.get('url', ''))
    if 'outlook.live.com/mail' in u:
        inbox = t
        break
print('TAB:', inbox.get('url') if inbox else None, '| total tabs:', len(tabs))
if inbox:
    ws = str(inbox['webSocketDebuggerUrl']).replace('127.0.0.1:9222', '127.0.0.1:9224') \
        .replace('localhost:9222', '127.0.0.1:9224')
    # Quét rộng div/span/[role] — selector hẹp [role=listitem] trả [] trên Outlook mới
    expr = """
    (() => {
      const out = [];
      const all = document.querySelectorAll('div,span,[role="listitem"],[role="option"]');
      for (const el of all) {
        const t = (el.innerText || '').trim().replace(/\\s+/g,' ');
        if (/tiktok/i.test(t) && t.length < 400) {
          const m = t.match(/(\\d{1,2}:\\d{2} (SA|CH))|(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2})/);
          out.push((m ? '[' + m[0] + '] ' : '[?] ') + t.slice(0, 200));
        }
      }
      return JSON.stringify([...new Set(out)].slice(0, 14));
    })()
    """
    res = cdp_eval(ws, expr)
    print('ROWS:')
    print(res)
subprocess.run([adb, '-s', serial, 'forward', '--remove', 'tcp:9224'], capture_output=True)
