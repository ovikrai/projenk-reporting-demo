"""Local portfolio server with a real Python reporting endpoint."""
import argparse
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from reporting.__main__ import run

ROOT = Path(__file__).resolve().parent
RUN_LOCK = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def reply(self, status, value):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/config":
            self.reply(200, {"local_pipeline": True})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path != "/api/run":
            return self.reply(404, {"error": "Unknown endpoint"})
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + self.headers.get("Host", ""):
            return self.reply(403, {"error": "Cross-origin runs are not permitted"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024:
                raise ValueError("Invalid request size")
            month = json.loads(self.rfile.read(length))["month"]
            if month not in ("2026-07", "2026-08", "2026-09"):
                raise ValueError("Choose a demo reporting month")
            with RUN_LOCK:
                result = run(ROOT / "data/synthetic_orders.csv", ROOT / "docs/reports" / month, month)
            self.reply(200, result)
        except (ValueError, KeyError, OSError, TypeError) as error:
            self.reply(400, {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description="Serve the Projenk portfolio locally")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not (ROOT / "docs/data/manifest.json").exists():
        from scripts.build_site import build
        build()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(ROOT / "docs")))
    print(f"Projenk: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
