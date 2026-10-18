import json
import queue
import signal
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 20135
GPM_API = "http://127.0.0.1:19995/api/v3"
GPM_PROFILE_ID = "4344af68-9954-4bf5-9a57-2b6853cf0d74"
GEMINI_URL = "https://gemini.google.com/app"
MODEL_NAME = "gemini-4-argon"
MODEL_LABEL = "4 Argon"
RESPONSE_APPEAR_TIMEOUT_S = 20
STOP_TIMEOUT_S = 180
REQUEST_TIMEOUT_S = 240

INPUT_SELECTOR = 'div[contenteditable="true"], rich-textarea p, rich-textarea div, div.ql-editor'
SEND_SELECTOR = 'button[aria-label*="Gửi"], button[aria-label*="Send"], button.send-button, [data-test-id="send-button"]'
STOP_SELECTOR = 'button[aria-label*="Ngưng"], button[aria-label*="Stop"], [data-test-id="stop-button"], div[role="button"]:has-text("Ngưng")'
MODEL_MENU_SELECTOR = 'button:has-text("Gemini"), [data-test-id="model-switcher-button"], [data-test-id="bard-mode-menu-button"]'
RESPONSE_SELECTOR = "message-content, model-response, .model-response-text, .markdown"


def gpm_get(path):
    with urllib.request.urlopen(f"{GPM_API}{path}", timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not (payload.get("status") == "success" or payload.get("success") is True):
        raise RuntimeError(f"GPM {path} failed: {payload}")
    return payload["data"]


def gpm_start(profile_id=GPM_PROFILE_ID):
    data = gpm_get(f"/profiles/start/{profile_id}")
    return data.get("remote_debugging_address")


def gpm_close(profile_id=GPM_PROFILE_ID):
    try:
        with urllib.request.urlopen(f"{GPM_API}/profiles/stop/{profile_id}", timeout=10):
            pass
    except Exception as exc:
        print(f"GPM close failed: {exc}", flush=True)


class GeminiSession:
    def __init__(self, profile_id=GPM_PROFILE_ID):
        self.profile_id = profile_id
        self._playwright = None
        self._browser = None
        self._page = None

    def start(self):
        from playwright.sync_api import sync_playwright

        address = gpm_start(self.profile_id)
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.connect_over_cdp(f"http://{address}")
        context = self._browser.contexts[0]
        self._page = context.pages[0] if context.pages else context.new_page()
        self._page.goto(GEMINI_URL, wait_until="domcontentloaded")
        self._page.wait_for_selector(INPUT_SELECTOR, timeout=60000)
        self._select_model()
        self._page.set_viewport_size({"width": 1280, "height": 900})

    def _select_model(self):
        page = self._page
        try:
            switcher = page.locator(MODEL_MENU_SELECTOR).first
            if MODEL_LABEL not in switcher.inner_text().strip():
                switcher.click(timeout=5000)
                page.wait_for_timeout(1000)
                page.locator(f'[role="menuitem"]:has-text("{MODEL_LABEL}"), button:has-text("{MODEL_LABEL}")').first.click(timeout=5000)
                page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Model select skipped or already selected: {e}", flush=True)

    def ask(self, prompt):
        page = self._page
        input_el = page.locator(INPUT_SELECTOR).first
        input_el.click()
        input_el.fill(prompt)
        page.wait_for_timeout(500)

        send_btn = page.locator(SEND_SELECTOR).first
        if send_btn.is_visible():
            send_btn.click()
        else:
            input_el.press("Enter")

        page.wait_for_timeout(3000)
        t_start = time.monotonic()
        deadline = t_start + STOP_TIMEOUT_S

        while time.monotonic() < deadline:
            page.wait_for_timeout(3000)
            has_stop = page.locator("button:has-text('Ngưng'), button[aria-label*='Ngưng'], button[aria-label*='Stop'], [data-test-id='stop-button']").count() > 0
            if has_stop:
                continue

            page.wait_for_timeout(2000)
            try:
                page.locator(".model-response-text, [data-test-id='conversation-turn']").last.scroll_into_view_if_needed()
            except Exception:
                pass
            page.wait_for_timeout(1000)

            containers = page.locator(".model-response-text, message-content, [data-test-id='conversation-turn']").all()
            for container in reversed(containers):
                text = container.inner_text().strip()
                if text and prompt not in text and "Gemini là một AI" not in text and "Lưu ý" not in text:
                    lines = [line.strip() for line in text.split("\n") if line.strip()]
                    deduped = []
                    for line in lines:
                        if not deduped or line != deduped[-1]:
                            deduped.append(line)
                    res_text = "\n".join(deduped)
                    return res_text
        return "No response from Argon"

    def close(self):
        try:
            if self._browser is not None:
                self._browser.close()
            if self._playwright is not None:
                self._playwright.stop()
        finally:
            gpm_close(self.profile_id)


class Worker(threading.Thread):
    def __init__(self, profile_id=GPM_PROFILE_ID):
        super().__init__(daemon=True)
        self.jobs = queue.Queue()
        self.ready = threading.Event()
        self.init_error = None
        self._session = GeminiSession(profile_id)

    def run(self):
        try:
            self._session.start()
            print("Gemini Argon session ready", flush=True)
        except Exception as exc:
            self.init_error = exc
            print(f"Gemini Argon session init failed: {exc}", flush=True)
        finally:
            self.ready.set()

        while True:
            job = self.jobs.get()
            if job is None:
                break
            prompt, reply = job
            try:
                if self.init_error is not None:
                    raise RuntimeError(f"session init failed: {self.init_error}")
                reply.put(("ok", self._session.ask(prompt)))
            except Exception as exc:
                reply.put(("error", exc))

        self._session.close()

    def submit(self, prompt):
        if not self.ready.wait(timeout=REQUEST_TIMEOUT_S):
            raise TimeoutError("session not ready")
        reply = queue.Queue(maxsize=1)
        self.jobs.put((prompt, reply))
        status, value = reply.get(timeout=REQUEST_TIMEOUT_S)
        if status == "error":
            raise value
        return value

    def stop(self):
        self.jobs.put(None)
        self.join(timeout=60)


def last_user_text(messages):
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        if isinstance(content, list):
            content = "\n".join(
                part.get("text", "") for part in content if part.get("type") == "text"
            )
        return str(content).strip()
    return ""


class Handler(BaseHTTPRequestHandler):
    worker = None

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": {"message": "not found"}})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            prompt = last_user_text(body.get("messages", []))
            if not prompt:
                self._send_json(400, {"error": {"message": "no user message"}})
                return
            answer = self.worker.submit(prompt)
        except Exception as exc:
            self._send_json(500, {"error": {"message": str(exc)}})
            return

        self._send_json(
            200,
            {
                "id": f"chatcmpl-argon-{uuid.uuid4().hex}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": MODEL_NAME,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": answer},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    def _send_json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}", flush=True)


def run_server(port=PORT, profile_id=GPM_PROFILE_ID):
    worker = Worker(profile_id)
    worker.start()
    Handler.worker = worker

    server = ThreadingHTTPServer((HOST, port), Handler)

    def request_shutdown(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    print(f"Listening on http://{HOST}:{port}/v1/chat/completions", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        worker.stop()
        print("Gemini Argon server stopped", flush=True)


if __name__ == "__main__":
    run_server()
