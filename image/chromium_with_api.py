#!/usr/bin/env python3
"""
Chromium launcher with DOM API server.

Launches Chromium with remote debugging enabled and provides an HTTP API
on port 8122 that returns JSON layout trees of DOM for all open tabs.
"""

import http.server
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error

# CDP WebSocket communication
try:
    import websocket
except ImportError:
    print("Installing websocket-client...", file=sys.stderr)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client"])
    import websocket

CDP_PORT = 9222
API_PORT = 8122
CHROMIUM_CMD = [
    "chromium",
    "--disable-seccomp-filter-sandbox",
    "--test-type",
    f"--remote-debugging-port={CDP_PORT}",
    "--remote-allow-origins=*",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-sync",
    "--disable-translate",
    "--metrics-recording-only",
]

chromium_process = None


def get_cdp_targets():
    """Get list of debuggable targets from CDP."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json", timeout=5) as resp:
            return json.load(resp)
    except (urllib.error.URLError, OSError) as e:
        return {"error": str(e)}


class CDPSession:
    """Manages a CDP WebSocket session for multiple commands."""

    def __init__(self, ws_url, timeout=10):
        self.ws = websocket.create_connection(ws_url, timeout=timeout)
        self.msg_id = 0

    def send(self, method, params=None):
        """Send a CDP command and return the result."""
        self.msg_id += 1
        request = {"id": self.msg_id, "method": method}
        if params:
            request["params"] = params
        self.ws.send(json.dumps(request))

        while True:
            response = json.loads(self.ws.recv())
            if response.get("id") == self.msg_id:
                if "error" in response:
                    return {"error": response["error"]}
                return response.get("result")

    def close(self):
        """Close the WebSocket connection."""
        self.ws.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def cdp_send(ws_url, method, params=None, timeout=10):
    """Send a single CDP command (opens new connection)."""
    with CDPSession(ws_url, timeout) as session:
        return session.send(method, params)


def get_viewport(session):
    """Get viewport metrics for a tab."""
    try:
        metrics = session.send("Page.getLayoutMetrics")
        if not metrics:
            return None

        # Extract useful viewport info
        viewport = {}

        # CSS viewport (what's visible)
        if "cssVisualViewport" in metrics:
            vv = metrics["cssVisualViewport"]
            viewport["visualViewport"] = {
                "x": vv.get("pageX", 0),
                "y": vv.get("pageY", 0),
                "width": vv.get("clientWidth", 0),
                "height": vv.get("clientHeight", 0),
                "scale": vv.get("scale", 1),
            }

        # Layout viewport
        if "cssLayoutViewport" in metrics:
            lv = metrics["cssLayoutViewport"]
            viewport["layoutViewport"] = {
                "x": lv.get("pageX", 0),
                "y": lv.get("pageY", 0),
                "width": lv.get("clientWidth", 0),
                "height": lv.get("clientHeight", 0),
            }

        # Content size (full scrollable area)
        if "cssContentSize" in metrics:
            cs = metrics["cssContentSize"]
            viewport["contentSize"] = {
                "width": cs.get("width", 0),
                "height": cs.get("height", 0),
            }

        return viewport
    except Exception:
        return None


def get_node_bounds(session, backend_node_ids):
    """Get bounding boxes for nodes using DOM.getBoxModel."""
    bounds_map = {}

    for backend_id in backend_node_ids:
        try:
            result = session.send("DOM.getBoxModel", {"backendNodeId": backend_id})
            if result and "model" in result:
                model = result["model"]
                # content box is the innermost box
                content = model.get("content", [])
                if len(content) >= 8:
                    # content is [x1,y1, x2,y2, x3,y3, x4,y4] for quad
                    x = min(content[0], content[2], content[4], content[6])
                    y = min(content[1], content[3], content[5], content[7])
                    x2 = max(content[0], content[2], content[4], content[6])
                    y2 = max(content[1], content[3], content[5], content[7])
                    bounds_map[backend_id] = {
                        "x": x,
                        "y": y,
                        "width": x2 - x,
                        "height": y2 - y,
                    }
                # Also include border box for full element bounds
                border = model.get("border", [])
                if len(border) >= 8:
                    x = min(border[0], border[2], border[4], border[6])
                    y = min(border[1], border[3], border[5], border[7])
                    x2 = max(border[0], border[2], border[4], border[6])
                    y2 = max(border[1], border[3], border[5], border[7])
                    if backend_id in bounds_map:
                        bounds_map[backend_id]["borderBox"] = {
                            "x": x,
                            "y": y,
                            "width": x2 - x,
                            "height": y2 - y,
                        }
        except Exception:
            # Node may not have a box (e.g., display:none)
            pass

    return bounds_map


def get_layout_tree(ws_url):
    """Get layout/accessibility tree with coordinates for a single tab."""
    try:
        with CDPSession(ws_url, timeout=30) as session:
            # Enable required domains
            session.send("DOM.enable")
            session.send("Accessibility.enable")
            session.send("Page.enable")

            # Get viewport info
            viewport = get_viewport(session)

            # Get full accessibility tree
            ax_tree = session.send("Accessibility.getFullAXTree")

            if ax_tree and "nodes" in ax_tree:
                nodes = ax_tree["nodes"]

                # Collect all backendDOMNodeIds to fetch bounds
                backend_ids = []
                for node in nodes:
                    if "backendDOMNodeId" in node:
                        backend_ids.append(node["backendDOMNodeId"])

                # Fetch bounds for all nodes
                if backend_ids:
                    bounds_map = get_node_bounds(session, backend_ids)

                    # Attach bounds to nodes
                    for node in nodes:
                        backend_id = node.get("backendDOMNodeId")
                        if backend_id and backend_id in bounds_map:
                            node["bounds"] = bounds_map[backend_id]

                result = {"nodes": nodes}
                if viewport:
                    result["viewport"] = viewport
                return result

            # Fallback to DOM if accessibility tree not available
            doc = session.send("DOM.getDocument", {"depth": -1, "pierce": True})
            result = doc or {"error": "Failed to get tree"}
            if viewport:
                result["viewport"] = viewport
            return result

    except Exception as e:
        return {"error": str(e)}


def get_all_tabs_layout():
    """Get layout trees for all open tabs."""
    targets = get_cdp_targets()

    if isinstance(targets, dict) and "error" in targets:
        return {"error": targets["error"], "tabs": []}

    results = []
    for target in targets:
        if target.get("type") != "page":
            continue

        tab_info = {
            "id": target.get("id"),
            "url": target.get("url"),
            "title": target.get("title"),
        }

        ws_url = target.get("webSocketDebuggerUrl")
        if ws_url:
            tab_info["layout"] = get_layout_tree(ws_url)
        else:
            tab_info["layout"] = {"error": "No WebSocket URL available"}

        results.append(tab_info)

    return {"tabs": results}


class APIHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the DOM API."""

    def log_message(self, format, *args):
        """Log to stderr with timestamp."""
        print(f"[API] {args[0]}", file=sys.stderr)

    def send_json(self, data, status=200):
        """Send JSON response."""
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/" or self.path == "/layout":
            # Return layout tree of all tabs
            result = get_all_tabs_layout()
            self.send_json(result)

        elif self.path == "/targets" or self.path == "/tabs":
            # Return list of CDP targets
            targets = get_cdp_targets()
            self.send_json(targets)

        elif self.path == "/health":
            # Health check
            self.send_json({"status": "ok", "chromium_pid": chromium_process.pid if chromium_process else None})

        else:
            self.send_json({"error": "Not found", "endpoints": ["/", "/layout", "/targets", "/tabs", "/health"]}, 404)


def run_api_server():
    """Run the HTTP API server."""
    server = http.server.HTTPServer(("0.0.0.0", API_PORT), APIHandler)
    print(f"[API] Listening on port {API_PORT}", file=sys.stderr)
    server.serve_forever()


def wait_for_cdp(timeout=30):
    """Wait for CDP to become available."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            targets = get_cdp_targets()
            if isinstance(targets, list):
                print(f"[CDP] Ready with {len(targets)} targets", file=sys.stderr)
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print(f"\n[Main] Received signal {signum}, shutting down...", file=sys.stderr)
    if chromium_process:
        chromium_process.terminate()
        try:
            chromium_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chromium_process.kill()
    sys.exit(0)


def main():
    global chromium_process

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Parse command line args - pass extras to Chromium
    chromium_args = CHROMIUM_CMD.copy()
    if len(sys.argv) > 1:
        chromium_args.extend(sys.argv[1:])

    # If no URL specified, open a blank page
    has_url = any(arg.startswith("http") or arg.startswith("file:") for arg in sys.argv[1:])
    if not has_url:
        chromium_args.append("about:blank")

    print(f"[Main] Starting Chromium with CDP on port {CDP_PORT}", file=sys.stderr)
    print(f"[Main] Command: {' '.join(chromium_args)}", file=sys.stderr)

    # Start Chromium
    env = os.environ.copy()
    chromium_process = subprocess.Popen(
        chromium_args,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print(f"[Main] Chromium started with PID {chromium_process.pid}", file=sys.stderr)

    # Wait for CDP to be ready
    if not wait_for_cdp():
        print("[Main] ERROR: CDP did not become ready in time", file=sys.stderr)
        chromium_process.terminate()
        sys.exit(1)

    # Start API server in a thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()

    print(f"[Main] API server running on http://0.0.0.0:{API_PORT}", file=sys.stderr)
    print("[Main] Endpoints:", file=sys.stderr)
    print("  GET /        - Layout tree of all tabs", file=sys.stderr)
    print("  GET /layout  - Layout tree of all tabs", file=sys.stderr)
    print("  GET /targets - List CDP targets", file=sys.stderr)
    print("  GET /tabs    - List CDP targets", file=sys.stderr)
    print("  GET /health  - Health check", file=sys.stderr)

    # Wait for Chromium to exit
    try:
        return_code = chromium_process.wait()
        print(f"[Main] Chromium exited with code {return_code}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\n[Main] Interrupted, shutting down...", file=sys.stderr)
        chromium_process.terminate()
        chromium_process.wait(timeout=5)


if __name__ == "__main__":
    main()
