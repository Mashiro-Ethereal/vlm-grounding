#!/usr/bin/env python3
"""
Concurrent SFT data collection from multiple containers.

Usage:
    # First, start multiple containers:
    for i in {0..4}; do
        podman run -d --name osworld-$i -p $((8080+i*10)):8080 -p $((8122+i*10)):8122 localhost/osworld-desktopd:latest
    done

    # Then run collection:
    python scripts/collect_sft_data_concurrent.py --output ./dataset/sft_100 --count 100 --workers 5
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

# Add parent dir to path for data_format imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from image.layout_to_ui_tree import convert_layout_to_ui_tree

# Container settings
CONTAINER_RUNTIME = None  # Auto-detect

# Thread-safe print lock
print_lock = Lock()


def safe_print(msg):
    """Thread-safe print."""
    with print_lock:
        print(msg, file=sys.stderr)


def detect_runtime():
    """Auto-detect docker or podman."""
    global CONTAINER_RUNTIME
    if CONTAINER_RUNTIME:
        return CONTAINER_RUNTIME

    for cmd in ["podman", "docker"]:
        try:
            result = subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                CONTAINER_RUNTIME = cmd
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    raise RuntimeError("Neither docker nor podman found")


class ContainerWorker:
    """Worker that manages a single container instance."""

    def __init__(self, worker_id: int, base_port: int = 8080):
        self.worker_id = worker_id
        self.container_name = f"osworld-{worker_id}"
        self.desktopd_port = base_port + worker_id * 10
        self.dom_api_port = base_port + 42 + worker_id * 10  # 8122, 8132, etc.
        self.desktopd_url = f"http://localhost:{self.desktopd_port}"
        self.dom_api_url = f"http://localhost:{self.dom_api_port}"
        self.runtime = detect_runtime()

    def is_ready(self) -> bool:
        """Check if container is ready."""
        try:
            with urllib.request.urlopen(f"{self.desktopd_url}/api/v1/screenshot", timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_screenshot(self, output_path: str) -> bool:
        """Capture screenshot via desktopd API."""
        try:
            with urllib.request.urlopen(f"{self.desktopd_url}/api/v1/screenshot", timeout=10) as resp:
                with open(output_path, "wb") as f:
                    f.write(resp.read())
            return True
        except Exception as e:
            safe_print(f"[Worker {self.worker_id}] Screenshot error: {e}")
            return False

    def get_cdp_layout(self) -> dict:
        """Get layout tree via chromium_with_api.py HTTP API."""
        try:
            with urllib.request.urlopen(f"{self.dom_api_url}/layout", timeout=30) as resp:
                return json.load(resp)
        except Exception as e:
            safe_print(f"[Worker {self.worker_id}] Layout API error: {e}")
            return {"tabs": []}

    def navigate_to_url(self, url: str) -> bool:
        """Navigate Chromium to a URL via CDP."""
        nav_script = f'''
import json
import urllib.request
import websocket

with urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=5) as resp:
    targets = json.load(resp)

for t in targets:
    if t.get("type") == "page":
        ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=10)
        ws.send(json.dumps({{"id": 1, "method": "Page.navigate", "params": {{"url": "{url}"}}}}))
        ws.recv()
        ws.close()
        break
'''
        full_cmd = [
            self.runtime, "exec",
            "-u", "user",
            "-e", "XDG_RUNTIME_DIR=/tmp/xdg",
            "-e", "WAYLAND_DISPLAY=wayland-1",
            self.container_name,
            "python3", "-c", nav_script
        ]
        try:
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                safe_print(f"[Worker {self.worker_id}] Nav error: {result.stderr}")
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            safe_print(f"[Worker {self.worker_id}] Navigation timeout")
            return False

    def send_click(self, x: int, y: int) -> bool:
        """Send click via desktopd tablet API."""
        data = json.dumps({"events": [{"type": "click", "x": x, "y": y, "button": "left"}]}).encode()
        req = urllib.request.Request(
            f"{self.desktopd_url}/api/v1/tablet_event",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 204
        except Exception as e:
            safe_print(f"[Worker {self.worker_id}] Click error: {e}")
            return False

    def send_keyboard(self, text: str) -> bool:
        """Send text input via desktopd keyboard API."""
        events = []
        for char in text:
            events.append({"keysym": char, "state": "down"})
            events.append({"keysym": char, "state": "up"})

        data = json.dumps({"events": events}).encode()
        req = urllib.request.Request(
            f"{self.desktopd_url}/api/v1/keyboard_event",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 204
        except Exception as e:
            safe_print(f"[Worker {self.worker_id}] Keyboard error: {e}")
            return False

    def collect_step(self, output_dir: Path, step_index: int, action: dict) -> bool:
        """Collect one step: screenshot, ui_tree, action."""
        step_dir = output_dir / "steps" / f"{step_index:03d}"
        step_dir.mkdir(parents=True, exist_ok=True)

        # Screenshot
        screenshot_path = step_dir / "screenshot.png"
        if not self.get_screenshot(str(screenshot_path)):
            return False

        # UI tree
        layout = self.get_cdp_layout()
        ui_tree = convert_layout_to_ui_tree(layout)
        ui_tree_path = step_dir / "ui_tree.json"
        with open(ui_tree_path, "w") as f:
            json.dump(ui_tree, f, indent=2)

        # Action
        action["step_index"] = step_index
        action_path = step_dir / "action.json"
        with open(action_path, "w") as f:
            json.dump(action, f, indent=2)

        return True

    def collect_trajectory(self, output_dir: Path, task: dict, actions: list) -> bool:
        """Collect a complete trajectory."""
        traj_id = task["task_id"]
        traj_dir = output_dir / "trajectories" / traj_id
        traj_dir.mkdir(parents=True, exist_ok=True)

        # Save task
        task_path = traj_dir / "task.json"
        with open(task_path, "w") as f:
            json.dump(task, f, indent=2)

        # Collect steps
        start_time = time.time()
        for i, action in enumerate(actions):
            if not self.collect_step(traj_dir, i, action):
                safe_print(f"[Worker {self.worker_id}] Failed to collect step {i}")
                return False

            # Execute action
            if action["action_type"] == "click":
                params = action["parameters"]
                self.send_click(params["x"], params["y"])
            elif action["action_type"] == "type":
                self.send_keyboard(action["parameters"]["text"])
            elif action["action_type"] == "wait":
                time.sleep(action["parameters"].get("seconds", 1))

            time.sleep(0.5)  # Wait for UI to update

        # Final screenshot
        final_path = traj_dir / "final_screenshot.png"
        self.get_screenshot(str(final_path))

        # Result
        elapsed = int((time.time() - start_time) * 1000)
        result = {
            "trajectory_id": traj_id,
            "success": True,
            "total_steps": len(actions),
            "completion_time_ms": elapsed,
            "error_message": None,
            "model_info": {"name": "human", "version": "1.0"}
        }
        result_path = traj_dir / "result.json"
        with open(result_path, "w") as f:
            json.dump(result, f, indent=2)

        return True


# 100 general website tasks for data collection
SAMPLE_TASKS = [
    # News & Media
    {"task_id": "bbc_news", "url": "https://www.bbc.com", "instruction": "Visit BBC News homepage"},
    {"task_id": "cnn_news", "url": "https://www.cnn.com", "instruction": "Navigate to CNN homepage"},
    {"task_id": "reuters", "url": "https://www.reuters.com", "instruction": "Open Reuters news site"},
    {"task_id": "ap_news", "url": "https://apnews.com", "instruction": "Visit Associated Press news"},
    {"task_id": "npr", "url": "https://www.npr.org", "instruction": "Open NPR homepage"},
    {"task_id": "theguardian", "url": "https://www.theguardian.com", "instruction": "Visit The Guardian"},
    {"task_id": "nytimes", "url": "https://www.nytimes.com", "instruction": "Navigate to NY Times"},
    {"task_id": "washingtonpost", "url": "https://www.washingtonpost.com", "instruction": "Open Washington Post"},
    {"task_id": "aljazeera", "url": "https://www.aljazeera.com", "instruction": "Visit Al Jazeera news"},
    {"task_id": "bloomberg", "url": "https://www.bloomberg.com", "instruction": "Open Bloomberg homepage"},

    # Search Engines
    {"task_id": "google", "url": "https://www.google.com", "instruction": "Open Google search"},
    {"task_id": "duckduckgo", "url": "https://duckduckgo.com", "instruction": "Visit DuckDuckGo search"},
    {"task_id": "bing", "url": "https://www.bing.com", "instruction": "Navigate to Bing search"},
    {"task_id": "yahoo", "url": "https://www.yahoo.com", "instruction": "Open Yahoo homepage"},
    {"task_id": "ecosia", "url": "https://www.ecosia.org", "instruction": "Visit Ecosia search engine"},
    {"task_id": "startpage", "url": "https://www.startpage.com", "instruction": "Open Startpage search"},
    {"task_id": "brave_search", "url": "https://search.brave.com", "instruction": "Visit Brave Search"},
    {"task_id": "qwant", "url": "https://www.qwant.com", "instruction": "Open Qwant search engine"},

    # Reference & Knowledge
    {"task_id": "wikipedia", "url": "https://www.wikipedia.org", "instruction": "Visit Wikipedia main page"},
    {"task_id": "wiktionary", "url": "https://www.wiktionary.org", "instruction": "Open Wiktionary dictionary"},
    {"task_id": "wikimedia", "url": "https://www.wikimedia.org", "instruction": "Visit Wikimedia Foundation"},
    {"task_id": "britannica", "url": "https://www.britannica.com", "instruction": "Open Encyclopedia Britannica"},
    {"task_id": "archive_org", "url": "https://archive.org", "instruction": "Visit Internet Archive"},
    {"task_id": "wolfram", "url": "https://www.wolframalpha.com", "instruction": "Open Wolfram Alpha"},

    # Tech & Developer
    {"task_id": "github", "url": "https://github.com", "instruction": "Navigate to GitHub homepage"},
    {"task_id": "gitlab", "url": "https://gitlab.com", "instruction": "Visit GitLab homepage"},
    {"task_id": "stackoverflow", "url": "https://stackoverflow.com", "instruction": "Open Stack Overflow"},
    {"task_id": "mdn", "url": "https://developer.mozilla.org", "instruction": "Visit MDN Web Docs"},
    {"task_id": "python_docs", "url": "https://docs.python.org", "instruction": "Open Python documentation"},
    {"task_id": "nodejs_docs", "url": "https://nodejs.org", "instruction": "Visit Node.js homepage"},
    {"task_id": "rust_lang", "url": "https://www.rust-lang.org", "instruction": "Open Rust language site"},
    {"task_id": "golang", "url": "https://go.dev", "instruction": "Visit Go programming language"},
    {"task_id": "typescript", "url": "https://www.typescriptlang.org", "instruction": "Open TypeScript homepage"},
    {"task_id": "reactjs", "url": "https://react.dev", "instruction": "Visit React documentation"},
    {"task_id": "vuejs", "url": "https://vuejs.org", "instruction": "Open Vue.js homepage"},
    {"task_id": "angular", "url": "https://angular.io", "instruction": "Visit Angular framework site"},
    {"task_id": "nextjs", "url": "https://nextjs.org", "instruction": "Open Next.js documentation"},
    {"task_id": "docker_hub", "url": "https://hub.docker.com", "instruction": "Visit Docker Hub"},
    {"task_id": "kubernetes", "url": "https://kubernetes.io", "instruction": "Open Kubernetes documentation"},
    {"task_id": "npmjs", "url": "https://www.npmjs.com", "instruction": "Visit npm registry"},
    {"task_id": "pypi", "url": "https://pypi.org", "instruction": "Open PyPI package index"},
    {"task_id": "crates_io", "url": "https://crates.io", "instruction": "Visit Rust crates registry"},
    {"task_id": "rubygems", "url": "https://rubygems.org", "instruction": "Open RubyGems registry"},
    {"task_id": "maven", "url": "https://mvnrepository.com", "instruction": "Visit Maven repository"},
    {"task_id": "nuget", "url": "https://www.nuget.org", "instruction": "Open NuGet gallery"},

    # Tech News & Community
    {"task_id": "hackernews", "url": "https://news.ycombinator.com", "instruction": "Browse Hacker News"},
    {"task_id": "reddit", "url": "https://www.reddit.com", "instruction": "Visit Reddit homepage"},
    {"task_id": "slashdot", "url": "https://slashdot.org", "instruction": "Open Slashdot news"},
    {"task_id": "techcrunch", "url": "https://techcrunch.com", "instruction": "Visit TechCrunch"},
    {"task_id": "arstechnica", "url": "https://arstechnica.com", "instruction": "Open Ars Technica"},
    {"task_id": "wired", "url": "https://www.wired.com", "instruction": "Visit Wired magazine"},
    {"task_id": "theverge", "url": "https://www.theverge.com", "instruction": "Open The Verge"},
    {"task_id": "engadget", "url": "https://www.engadget.com", "instruction": "Visit Engadget"},
    {"task_id": "devto", "url": "https://dev.to", "instruction": "Open DEV Community"},
    {"task_id": "hashnode", "url": "https://hashnode.com", "instruction": "Visit Hashnode blog platform"},
    {"task_id": "medium", "url": "https://medium.com", "instruction": "Open Medium homepage"},

    # Education & Learning
    {"task_id": "coursera", "url": "https://www.coursera.org", "instruction": "Visit Coursera platform"},
    {"task_id": "edx", "url": "https://www.edx.org", "instruction": "Open edX learning platform"},
    {"task_id": "khanacademy", "url": "https://www.khanacademy.org", "instruction": "Visit Khan Academy"},
    {"task_id": "udemy", "url": "https://www.udemy.com", "instruction": "Open Udemy marketplace"},
    {"task_id": "codecademy", "url": "https://www.codecademy.com", "instruction": "Visit Codecademy"},
    {"task_id": "freecodecamp", "url": "https://www.freecodecamp.org", "instruction": "Open freeCodeCamp"},
    {"task_id": "w3schools", "url": "https://www.w3schools.com", "instruction": "Visit W3Schools tutorials"},
    {"task_id": "mit_ocw", "url": "https://ocw.mit.edu", "instruction": "Open MIT OpenCourseWare"},
    {"task_id": "skillshare", "url": "https://www.skillshare.com", "instruction": "Visit Skillshare"},

    # Productivity & Tools
    {"task_id": "notion", "url": "https://www.notion.so", "instruction": "Open Notion homepage"},
    {"task_id": "trello", "url": "https://trello.com", "instruction": "Visit Trello boards"},
    {"task_id": "asana", "url": "https://asana.com", "instruction": "Open Asana project management"},
    {"task_id": "slack", "url": "https://slack.com", "instruction": "Visit Slack homepage"},
    {"task_id": "discord", "url": "https://discord.com", "instruction": "Open Discord platform"},
    {"task_id": "zoom", "url": "https://zoom.us", "instruction": "Visit Zoom homepage"},
    {"task_id": "dropbox", "url": "https://www.dropbox.com", "instruction": "Open Dropbox homepage"},
    {"task_id": "evernote", "url": "https://evernote.com", "instruction": "Visit Evernote"},
    {"task_id": "todoist", "url": "https://todoist.com", "instruction": "Open Todoist app"},
    {"task_id": "calendly", "url": "https://calendly.com", "instruction": "Visit Calendly scheduling"},

    # APIs & Dev Tools
    {"task_id": "httpbin", "url": "https://httpbin.org", "instruction": "Open httpbin.org for testing"},
    {"task_id": "jsonplaceholder", "url": "https://jsonplaceholder.typicode.com", "instruction": "Visit JSONPlaceholder API"},
    {"task_id": "reqres", "url": "https://reqres.in", "instruction": "Open ReqRes test API"},
    {"task_id": "postman", "url": "https://www.postman.com", "instruction": "Visit Postman API platform"},
    {"task_id": "swagger", "url": "https://swagger.io", "instruction": "Open Swagger API tools"},
    {"task_id": "rapidapi", "url": "https://rapidapi.com", "instruction": "Visit RapidAPI hub"},
    {"task_id": "apidoc", "url": "https://apidocjs.com", "instruction": "Open apiDoc documentation"},

    # Design & Creative
    {"task_id": "figma", "url": "https://www.figma.com", "instruction": "Visit Figma design tool"},
    {"task_id": "dribbble", "url": "https://dribbble.com", "instruction": "Open Dribbble design showcase"},
    {"task_id": "behance", "url": "https://www.behance.net", "instruction": "Visit Behance portfolio"},
    {"task_id": "canva", "url": "https://www.canva.com", "instruction": "Open Canva design platform"},
    {"task_id": "unsplash", "url": "https://unsplash.com", "instruction": "Visit Unsplash photos"},
    {"task_id": "pexels", "url": "https://www.pexels.com", "instruction": "Open Pexels stock photos"},
    {"task_id": "fontawesome", "url": "https://fontawesome.com", "instruction": "Visit Font Awesome icons"},
    {"task_id": "coolors", "url": "https://coolors.co", "instruction": "Open Coolors palette generator"},

    # Example & Test Sites
    {"task_id": "example_com", "url": "https://www.example.com", "instruction": "View example.com homepage"},
    {"task_id": "example_org", "url": "https://www.example.org", "instruction": "Open example.org"},
    {"task_id": "iana_domains", "url": "https://www.iana.org/domains/reserved", "instruction": "Visit IANA reserved domains"},

    # Utilities
    {"task_id": "speedtest", "url": "https://www.speedtest.net", "instruction": "Open Speedtest by Ookla"},
    {"task_id": "whatismyip", "url": "https://www.whatismyip.com", "instruction": "Check IP address"},
    {"task_id": "timeanddate", "url": "https://www.timeanddate.com", "instruction": "Visit Time and Date"},
    {"task_id": "weather_com", "url": "https://weather.com", "instruction": "Open Weather.com"},
    {"task_id": "xe_currency", "url": "https://www.xe.com", "instruction": "Visit XE currency converter"},
    {"task_id": "imdb", "url": "https://www.imdb.com", "instruction": "Visit IMDB movie database"},
    {"task_id": "amazon", "url": "https://www.amazon.com", "instruction": "Open Amazon homepage"},
]


def process_task(worker: ContainerWorker, task_data: dict, output_dir: Path, task_num: int, total: int) -> bool:
    """Process a single task with a worker."""
    task_id = task_data["task_id"]
    url = task_data["url"]
    instruction = task_data["instruction"]

    task = {
        "task_id": task_id,
        "instruction": instruction,
        "application": "chromium",
        "difficulty": "easy",
        "expected_steps": 1
    }

    actions = [
        {"action_type": "wait", "parameters": {"seconds": 2}, "reasoning": "Wait for page to fully load"}
    ]

    safe_print(f"[{task_num}/{total}] Worker {worker.worker_id}: {task_id} - {instruction}")

    # Navigate to URL
    if not worker.navigate_to_url(url):
        safe_print(f"[Worker {worker.worker_id}] Failed to navigate to {url}")
        return False

    time.sleep(3)  # Wait for page load

    # Collect trajectory
    if worker.collect_trajectory(output_dir, task, actions):
        safe_print(f"[Worker {worker.worker_id}] Success: {task_id}")
        return True
    else:
        safe_print(f"[Worker {worker.worker_id}] Failed: {task_id}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Concurrent SFT data collection")
    parser.add_argument("--output", "-o", required=True, help="Output directory")
    parser.add_argument("--count", "-n", type=int, default=100, help="Number of samples to collect")
    parser.add_argument("--workers", "-w", type=int, default=5, help="Number of concurrent workers")
    parser.add_argument("--base-port", type=int, default=8080, help="Base port for containers")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Collecting {args.count} samples to {output_dir}", file=sys.stderr)
    print(f"Using {args.workers} concurrent workers", file=sys.stderr)
    print(f"Container runtime: {detect_runtime()}", file=sys.stderr)

    # Create workers
    workers = [ContainerWorker(i, args.base_port) for i in range(args.workers)]

    # Check which workers are ready
    ready_workers = []
    for w in workers:
        if w.is_ready():
            ready_workers.append(w)
            print(f"Worker {w.worker_id} ready at {w.desktopd_url}", file=sys.stderr)
        else:
            print(f"Worker {w.worker_id} NOT ready at {w.desktopd_url}", file=sys.stderr)

    if not ready_workers:
        print("No workers ready! Start containers first.", file=sys.stderr)
        print("\nTo start containers:", file=sys.stderr)
        print(f"  for i in {{0..{args.workers-1}}}; do", file=sys.stderr)
        print(f"    {detect_runtime()} run -d --name osworld-$i \\", file=sys.stderr)
        print(f"      -p $((8080+i*10)):8080 -p $((8122+i*10)):8122 \\", file=sys.stderr)
        print("      localhost/osworld-desktopd:latest", file=sys.stderr)
        print("  done", file=sys.stderr)
        return 1

    print(f"\n{len(ready_workers)} workers ready, starting collection...\n", file=sys.stderr)

    # Get tasks to process
    tasks_to_process = SAMPLE_TASKS[:args.count]
    total_tasks = len(tasks_to_process)

    collected = 0
    failed = 0

    # Process tasks concurrently
    with ThreadPoolExecutor(max_workers=len(ready_workers)) as executor:
        # Create a mapping of futures to task info
        future_to_task = {}

        for i, task_data in enumerate(tasks_to_process):
            # Round-robin assignment to workers
            worker = ready_workers[i % len(ready_workers)]
            future = executor.submit(process_task, worker, task_data, output_dir, i + 1, total_tasks)
            future_to_task[future] = task_data

        # Collect results as they complete
        for future in as_completed(future_to_task):
            task_data = future_to_task[future]
            try:
                success = future.result()
                if success:
                    collected += 1
                else:
                    failed += 1
            except Exception as e:
                safe_print(f"Task {task_data['task_id']} raised exception: {e}")
                failed += 1

    print(f"\n{'='*50}", file=sys.stderr)
    print(f"Collection complete: {collected} success, {failed} failed", file=sys.stderr)

    # Create index
    index = {
        "version": "1.0",
        "total_trajectories": collected,
        "successful": collected,
        "failed": failed,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "workers_used": len(ready_workers),
        "trajectories": []
    }

    traj_dir = output_dir / "trajectories"
    if traj_dir.exists():
        for traj_path in sorted(traj_dir.iterdir()):
            task_file = traj_path / "task.json"
            result_file = traj_path / "result.json"
            if task_file.exists() and result_file.exists():
                with open(task_file) as f:
                    task = json.load(f)
                with open(result_file) as f:
                    result = json.load(f)
                index["trajectories"].append({
                    "id": traj_path.name,
                    "task_id": task["task_id"],
                    "success": result["success"],
                    "steps": result["total_steps"],
                    "application": task.get("application")
                })

    index_path = output_dir / "index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"Index written to {index_path}", file=sys.stderr)
    return 0 if collected > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
