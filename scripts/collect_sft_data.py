#!/usr/bin/env python3
"""
Collect SFT training data from desktopd + Chromium.

Usage:
    python scripts/collect_sft_data.py --output ./data_format/sft_examples/20260202 --count 10
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Add parent dir to path for data_format imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from image.layout_to_ui_tree import convert_layout_to_ui_tree

# API endpoints
DESKTOPD_URL = os.environ.get("DESKTOPD_URL", "http://localhost:8080")
CDP_PORT = 9222

# Container settings
CONTAINER_NAME = "osworld"
CONTAINER_RUNTIME = None  # Auto-detect


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


def container_exec(cmd: str, user: str = "user") -> subprocess.CompletedProcess:
    """Execute command inside container."""
    runtime = detect_runtime()
    full_cmd = [
        runtime, "exec",
        "-u", user,
        "-e", "XDG_RUNTIME_DIR=/tmp/xdg",
        "-e", "WAYLAND_DISPLAY=wayland-1",
        CONTAINER_NAME,
        "sh", "-c", cmd
    ]
    return subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)


def get_screenshot(output_path: str) -> bool:
    """Capture screenshot via desktopd API."""
    try:
        with urllib.request.urlopen(f"{DESKTOPD_URL}/api/v1/screenshot", timeout=10) as resp:
            with open(output_path, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as e:
        print(f"Error getting screenshot: {e}", file=sys.stderr)
        return False


DOM_API_URL = os.environ.get("DOM_API_URL", "http://localhost:8122")


def get_cdp_layout() -> dict:
    """Get layout tree via chromium_with_api.py HTTP API."""
    try:
        with urllib.request.urlopen(f"{DOM_API_URL}/layout", timeout=30) as resp:
            return json.load(resp)
    except Exception as e:
        print(f"Layout API error: {e}", file=sys.stderr)
        return {"tabs": []}


def navigate_to_url(url: str) -> bool:
    """Navigate Chromium to a URL via CDP (using container's websocket)."""
    runtime = detect_runtime()
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
    # Run via subprocess with script as argument
    full_cmd = [
        runtime, "exec",
        "-u", "user",
        "-e", "XDG_RUNTIME_DIR=/tmp/xdg",
        "-e", "WAYLAND_DISPLAY=wayland-1",
        CONTAINER_NAME,
        "python3", "-c", nav_script
    ]
    result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"Nav error: {result.stderr}", file=sys.stderr)
    return result.returncode == 0


def send_click(x: int, y: int) -> bool:
    """Send click via desktopd tablet API."""
    data = json.dumps({"events": [{"type": "click", "x": x, "y": y, "button": "left"}]}).encode()
    req = urllib.request.Request(
        f"{DESKTOPD_URL}/api/v1/tablet_event",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 204
    except Exception as e:
        print(f"Click error: {e}", file=sys.stderr)
        return False


def send_keyboard(text: str) -> bool:
    """Send text input via desktopd keyboard API."""
    events = []
    for char in text:
        events.append({"keysym": char, "state": "down"})
        events.append({"keysym": char, "state": "up"})

    data = json.dumps({"events": events}).encode()
    req = urllib.request.Request(
        f"{DESKTOPD_URL}/api/v1/keyboard_event",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 204
    except Exception as e:
        print(f"Keyboard error: {e}", file=sys.stderr)
        return False


def collect_step(output_dir: Path, step_index: int, action: dict) -> bool:
    """Collect one step: screenshot, ui_tree, action."""
    step_dir = output_dir / "steps" / f"{step_index:03d}"
    step_dir.mkdir(parents=True, exist_ok=True)

    # Screenshot
    screenshot_path = step_dir / "screenshot.png"
    if not get_screenshot(str(screenshot_path)):
        return False

    # UI tree
    layout = get_cdp_layout()
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


def collect_trajectory(output_dir: Path, task: dict, actions: list) -> bool:
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
        print(f"  Step {i}: {action['action_type']}", file=sys.stderr)

        if not collect_step(traj_dir, i, action):
            print(f"  Failed to collect step {i}", file=sys.stderr)
            return False

        # Execute action
        if action["action_type"] == "click":
            params = action["parameters"]
            send_click(params["x"], params["y"])
        elif action["action_type"] == "type":
            send_keyboard(action["parameters"]["text"])
        elif action["action_type"] == "wait":
            time.sleep(action["parameters"].get("seconds", 1))

        time.sleep(0.5)  # Wait for UI to update

    # Final screenshot
    final_path = traj_dir / "final_screenshot.png"
    get_screenshot(str(final_path))

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


# Sample tasks for data collection
SAMPLE_TASKS = [
    {
        "task": {
            "task_id": "example_com_view",
            "instruction": "View the example.com homepage",
            "application": "chromium",
            "difficulty": "easy",
            "expected_steps": 1
        },
        "url": "https://www.example.com",
        "actions": [
            {"action_type": "wait", "parameters": {"seconds": 2}, "reasoning": "Wait for page to load"}
        ]
    },
    {
        "task": {
            "task_id": "google_search_page",
            "instruction": "Navigate to Google search page",
            "application": "chromium",
            "difficulty": "easy",
            "expected_steps": 1
        },
        "url": "https://www.google.com",
        "actions": [
            {"action_type": "wait", "parameters": {"seconds": 2}, "reasoning": "Wait for Google to load"}
        ]
    },
    {
        "task": {
            "task_id": "wikipedia_main",
            "instruction": "Visit Wikipedia main page",
            "application": "chromium",
            "difficulty": "easy",
            "expected_steps": 1
        },
        "url": "https://www.wikipedia.org",
        "actions": [
            {"action_type": "wait", "parameters": {"seconds": 2}, "reasoning": "Wait for Wikipedia to load"}
        ]
    },
    {
        "task": {
            "task_id": "github_homepage",
            "instruction": "Navigate to GitHub homepage",
            "application": "chromium",
            "difficulty": "easy",
            "expected_steps": 1
        },
        "url": "https://github.com",
        "actions": [
            {"action_type": "wait", "parameters": {"seconds": 2}, "reasoning": "Wait for GitHub to load"}
        ]
    },
    {
        "task": {
            "task_id": "duckduckgo_search",
            "instruction": "Open DuckDuckGo search engine",
            "application": "chromium",
            "difficulty": "easy",
            "expected_steps": 1
        },
        "url": "https://duckduckgo.com",
        "actions": [
            {"action_type": "wait", "parameters": {"seconds": 2}, "reasoning": "Wait for DuckDuckGo to load"}
        ]
    },
    {
        "task": {
            "task_id": "python_docs",
            "instruction": "Visit Python documentation",
            "application": "chromium",
            "difficulty": "easy",
            "expected_steps": 1
        },
        "url": "https://docs.python.org",
        "actions": [
            {"action_type": "wait", "parameters": {"seconds": 2}, "reasoning": "Wait for Python docs to load"}
        ]
    },
    {
        "task": {
            "task_id": "httpbin_get",
            "instruction": "Open httpbin.org for testing",
            "application": "chromium",
            "difficulty": "easy",
            "expected_steps": 1
        },
        "url": "https://httpbin.org",
        "actions": [
            {"action_type": "wait", "parameters": {"seconds": 2}, "reasoning": "Wait for httpbin to load"}
        ]
    },
    {
        "task": {
            "task_id": "jsonplaceholder_api",
            "instruction": "View JSONPlaceholder API page",
            "application": "chromium",
            "difficulty": "easy",
            "expected_steps": 1
        },
        "url": "https://jsonplaceholder.typicode.com",
        "actions": [
            {"action_type": "wait", "parameters": {"seconds": 2}, "reasoning": "Wait for API page to load"}
        ]
    },
    {
        "task": {
            "task_id": "hn_frontpage",
            "instruction": "Browse Hacker News front page",
            "application": "chromium",
            "difficulty": "easy",
            "expected_steps": 1
        },
        "url": "https://news.ycombinator.com",
        "actions": [
            {"action_type": "wait", "parameters": {"seconds": 2}, "reasoning": "Wait for HN to load"}
        ]
    },
    {
        "task": {
            "task_id": "mdn_web_docs",
            "instruction": "Open MDN Web Docs",
            "application": "chromium",
            "difficulty": "easy",
            "expected_steps": 1
        },
        "url": "https://developer.mozilla.org",
        "actions": [
            {"action_type": "wait", "parameters": {"seconds": 2}, "reasoning": "Wait for MDN to load"}
        ]
    },
]


def main():
    parser = argparse.ArgumentParser(description="Collect SFT training data")
    parser.add_argument("--output", "-o", required=True, help="Output directory")
    parser.add_argument("--count", "-n", type=int, default=10, help="Number of samples to collect")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Collecting {args.count} samples to {output_dir}", file=sys.stderr)
    print(f"Using container runtime: {detect_runtime()}", file=sys.stderr)

    collected = 0
    for i, sample in enumerate(SAMPLE_TASKS[:args.count]):
        task = sample["task"]
        url = sample["url"]
        actions = sample["actions"]

        print(f"\n[{i+1}/{args.count}] {task['task_id']}: {task['instruction']}", file=sys.stderr)

        # Navigate to URL
        print(f"  Navigating to {url}...", file=sys.stderr)
        if not navigate_to_url(url):
            print(f"  Failed to navigate", file=sys.stderr)
            continue
        time.sleep(3)  # Wait for page load

        # Collect trajectory
        if collect_trajectory(output_dir, task, actions):
            collected += 1
            print(f"  Success!", file=sys.stderr)
        else:
            print(f"  Failed!", file=sys.stderr)

    print(f"\nCollected {collected}/{args.count} samples", file=sys.stderr)

    # Create index
    index = {
        "version": "1.0",
        "total_trajectories": collected,
        "successful": collected,
        "failed": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
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
