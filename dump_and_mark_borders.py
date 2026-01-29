#!/usr/bin/env python3
"""
Screenshot utility that captures the Chromium window and marks HTML node boundaries.

Uses desktopd API for screenshots and window geometry, and the Chromium DOM API
for layout information including element bounding boxes.

Usage:
    python dump_and_mark_borders.py [output.png]
    python dump_and_mark_borders.py --help

Environment variables:
    DESKTOPD_URL    - desktopd API base URL (default: http://localhost:8080)
    DOM_API_URL     - Chromium DOM API URL (default: http://localhost:8122)
"""

import argparse
import io
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow", file=sys.stderr)
    sys.exit(1)


DESKTOPD_URL = "http://localhost:8080"
DOM_API_URL = "http://localhost:8122"


def get_env(name, default):
    """Get environment variable with default."""
    import os
    return os.environ.get(name, default)


def fetch_json(url, timeout=10):
    """Fetch JSON from a URL."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.URLError as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from {url}: {e}", file=sys.stderr)
        return None


def fetch_screenshot(desktopd_url):
    """Fetch screenshot from desktopd API."""
    url = f"{desktopd_url}/api/v1/screenshot"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return Image.open(io.BytesIO(resp.read()))
    except urllib.error.URLError as e:
        print(f"Error fetching screenshot: {e}", file=sys.stderr)
        return None


def find_chromium_window(tree):
    """Find Chromium window geometry in the Sway tree."""
    def search_node(node):
        # Check if this node is a Chromium window
        app_id = (node.get("app_id") or "").lower()
        name = (node.get("name") or "").lower()
        window_props = node.get("window_properties") or {}
        window_class = (window_props.get("class") or "").lower()

        is_chromium = (
            "chromium" in app_id or
            "chromium" in name or
            "chromium" in window_class or
            "chrome" in app_id or
            "chrome" in name
        )

        if is_chromium and node.get("type") == "con":
            rect = node.get("rect", {})
            if rect.get("width", 0) > 0 and rect.get("height", 0) > 0:
                return rect

        # Recursively search children
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            result = search_node(child)
            if result:
                return result

        return None

    return search_node(tree)


def get_layout_info(dom_api_url):
    """Fetch layout information from the Chromium DOM API."""
    url = f"{dom_api_url}/layout"
    return fetch_json(url, timeout=30)


def draw_node_borders(draw, nodes, viewport, window_rect, chrome_ui_offset=0):
    """Draw red borders around all nodes with bounds."""
    scroll_x = viewport.get("visualViewport", {}).get("x", 0)
    scroll_y = viewport.get("visualViewport", {}).get("y", 0)

    # Window position offset
    win_x = window_rect.get("x", 0)
    win_y = window_rect.get("y", 0)

    drawn_count = 0

    for node in nodes:
        bounds = node.get("bounds")
        if not bounds:
            continue

        # Skip nodes with zero size
        if bounds.get("width", 0) <= 0 or bounds.get("height", 0) <= 0:
            continue

        # Convert document coordinates to screen coordinates
        # Document coords -> viewport coords -> window coords -> screen coords
        x = bounds["x"] - scroll_x + win_x
        y = bounds["y"] - scroll_y + win_y + chrome_ui_offset
        width = bounds["width"]
        height = bounds["height"]

        # Draw rectangle (x1, y1, x2, y2)
        x1, y1 = x, y
        x2, y2 = x + width, y + height

        # Draw red border
        draw.rectangle([x1, y1, x2, y2], outline="red", width=1)
        drawn_count += 1

    return drawn_count


def estimate_chrome_ui_height(window_rect, viewport):
    """Estimate the height of Chrome UI (tabs, address bar, bookmarks)."""
    window_height = window_rect.get("height", 0)
    viewport_height = viewport.get("visualViewport", {}).get("height", 0)

    if viewport_height > 0 and window_height > viewport_height:
        # The difference is roughly the Chrome UI height
        return window_height - viewport_height

    # Default estimate for Chrome UI (tabs + address bar + bookmarks bar)
    return 90


def main():
    parser = argparse.ArgumentParser(
        description="Capture Chromium window screenshot with HTML node borders marked in red."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Output file path (default: chromium_borders_TIMESTAMP.png)"
    )
    parser.add_argument(
        "--desktopd-url",
        default=get_env("DESKTOPD_URL", DESKTOPD_URL),
        help=f"desktopd API URL (default: {DESKTOPD_URL})"
    )
    parser.add_argument(
        "--dom-api-url",
        default=get_env("DOM_API_URL", DOM_API_URL),
        help=f"Chromium DOM API URL (default: {DOM_API_URL})"
    )
    parser.add_argument(
        "--full-screen",
        action="store_true",
        help="Don't clip to Chromium window, use full screenshot"
    )
    parser.add_argument(
        "--no-borders",
        action="store_true",
        help="Don't draw borders, just save the screenshot"
    )
    parser.add_argument(
        "--chrome-ui-height",
        type=int,
        default=None,
        help="Override Chrome UI height in pixels (tabs, address bar, etc.)"
    )

    args = parser.parse_args()

    # Generate default output filename
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"chromium_borders_{timestamp}.png"

    print(f"Fetching screenshot from {args.desktopd_url}...", file=sys.stderr)
    screenshot = fetch_screenshot(args.desktopd_url)
    if screenshot is None:
        print("Failed to fetch screenshot", file=sys.stderr)
        return 1

    print(f"Screenshot size: {screenshot.width}x{screenshot.height}", file=sys.stderr)

    # Get window tree to find Chromium window
    print(f"Fetching window tree from {args.desktopd_url}...", file=sys.stderr)
    tree = fetch_json(f"{args.desktopd_url}/api/v1/tree")
    if tree is None:
        print("Failed to fetch window tree", file=sys.stderr)
        return 1

    # Find Chromium window
    window_rect = find_chromium_window(tree)
    if window_rect is None:
        print("Warning: Chromium window not found in tree, using full screen", file=sys.stderr)
        window_rect = {"x": 0, "y": 0, "width": screenshot.width, "height": screenshot.height}
    else:
        print(f"Chromium window: x={window_rect['x']}, y={window_rect['y']}, "
              f"w={window_rect['width']}, h={window_rect['height']}", file=sys.stderr)

    # Clip to Chromium window unless --full-screen
    if not args.full_screen:
        x, y = window_rect["x"], window_rect["y"]
        w, h = window_rect["width"], window_rect["height"]

        # Ensure we don't go out of bounds
        x2 = min(x + w, screenshot.width)
        y2 = min(y + h, screenshot.height)
        x = max(0, x)
        y = max(0, y)

        screenshot = screenshot.crop((x, y, x2, y2))
        print(f"Clipped to: {screenshot.width}x{screenshot.height}", file=sys.stderr)

        # Adjust window_rect for the clipped image
        window_rect = {"x": 0, "y": 0, "width": screenshot.width, "height": screenshot.height}

    # Get layout information and draw borders
    if not args.no_borders:
        print(f"Fetching layout from {args.dom_api_url}...", file=sys.stderr)
        layout_info = get_layout_info(args.dom_api_url)

        if layout_info is None:
            print("Failed to fetch layout info, saving screenshot without borders", file=sys.stderr)
        elif "error" in layout_info:
            print(f"Layout API error: {layout_info['error']}", file=sys.stderr)
            print("Saving screenshot without borders", file=sys.stderr)
        else:
            # Process each tab
            tabs = layout_info.get("tabs", [])
            if not tabs:
                print("No tabs found in layout response", file=sys.stderr)
            else:
                # Use first tab (or could iterate over all)
                tab = tabs[0]
                print(f"Processing tab: {tab.get('title', 'Unknown')}", file=sys.stderr)

                layout = tab.get("layout", {})
                nodes = layout.get("nodes", [])
                viewport = layout.get("viewport", {})

                if not nodes:
                    print("No nodes with bounds found", file=sys.stderr)
                else:
                    # Estimate Chrome UI height
                    chrome_ui_height = args.chrome_ui_height
                    if chrome_ui_height is None:
                        chrome_ui_height = estimate_chrome_ui_height(window_rect, viewport)
                    print(f"Chrome UI height offset: {chrome_ui_height}px", file=sys.stderr)

                    # Draw borders on the screenshot
                    draw = ImageDraw.Draw(screenshot)
                    drawn = draw_node_borders(draw, nodes, viewport, window_rect, chrome_ui_height)
                    print(f"Drew borders for {drawn} nodes", file=sys.stderr)

    # Save the result
    screenshot.save(args.output)
    print(f"Saved to: {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
