import os
import re
import uuid
import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer

DREEVE_UPLOAD_URL = os.environ.get(
    "DREEVE_UPLOAD_URL", "http://app:8080/api/v1/activity/upload"
)

class RelayHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Extract token from ?access_token=... or Authorization header
        query = parse_qs(urlparse(self.path).query)
        token = query.get("access_token", [None])[0]
        auth_header = self.headers.get("Authorization")
        if not auth_header and token:
            auth_header = f"Bearer {token}"

        if not auth_header:
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"error": "Missing access_token or Authorization header"}')
            return

        # 2. Read raw GPX payload from FitoTrack
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0 or content_length > 25 * 1024 * 1024:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid or empty payload"}')
            return
        gpx_bytes = self.rfile.read(content_length)

        # 3. Build a unique filename from Fitotrack-Workout-Type and Fitotrack-Timestamp
        workout_type = self.headers.get("Fitotrack-Workout-Type", "workout")
        timestamp = self.headers.get("Fitotrack-Timestamp", uuid.uuid4().hex[:8])
        raw_filename = self.headers.get(
            "X-FitoTrack-Filename", f"{workout_type}_{timestamp}.gpx"
        )
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', raw_filename)
        if not filename.lower().endswith((".gpx", ".tcx", ".fit")):
            filename += ".gpx"

        # 4. Build multipart/form-data body
        boundary = f"----FitoRelayBoundary{uuid.uuid4().hex}"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: application/gpx+xml\r\n\r\n"
        ).encode("utf-8") + gpx_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        # 5. Forward to Dreeve API (include User-Agent to avoid bot blocks)
        req = urllib.request.Request(
            DREEVE_UPLOAD_URL,
            data=body,
            headers={
                "Authorization": auth_header,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
                "Accept": "application/json",
                "User-Agent": "FitoTrack-Dreeve-Relay/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read()
                print(f"[SUCCESS] Uploaded {filename} -> HTTP {resp.status}", flush=True)
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as e:
            err_body = e.read()
            print(f"[DREEVE HTTP ERROR {e.code}] {err_body.decode('utf-8', errors='replace')}", flush=True)
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(err_body)
        except Exception as e:
            print(f"[UPSTREAM EXCEPTION] URL={DREEVE_UPLOAD_URL} Error={repr(e)}", flush=True)
            self.send_response(502)
            self.end_headers()
            self.wfile.write(f'{{"error": "Upstream error: {str(e)}"}}'.encode("utf-8"))

if __name__ == "__main__":
    print(f"FitoTrack relay listening on :8081 -> {DREEVE_UPLOAD_URL}", flush=True)
    HTTPServer(("0.0.0.0", 8081), RelayHandler).serve_forever()
